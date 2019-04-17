import argparse
import os
import io
import datetime
import logging
import subprocess
import time
import sys
import yaml
import boto3

from kubeflow.testing import util
from benchmark.test import deploy_utils

def parse_arguments():
  # create the top-level parser
  parser = argparse.ArgumentParser(description="Submit benchmark test.")
  parser.add_argument("--cluster_name", default="benchmark", type=str, help="EKS cluster name.")
  parser.add_argument("--region", default="benchmark", type=str, help="EKS cluster region.")
  parser.add_argument("--cluster_config", default="", type=str, help="EKS cluster configuration.")

  args = parser.parse_args()
  return args

def get_eks_network_info(cluster_name, az):
  # Find EKS VPC Information
  client = boto3.client('eks')
  response = client.describe_cluster(
    name=cluster_name
  )

  vpc_id = response['cluster']['resourcesVpcConfig']['vpcId']
  subnet_ids = response['cluster']['resourcesVpcConfig']['subnetIds']

  def _uppercase_availability_zone(availability_zone):
    return availability_zone.replace('-', '').upper()

  # Filter subnetId user specified in single availability zone
  client = boto3.client('ec2')
  subnet_name = "eksctl-{}-cluster/SubnetPublic{}".format(cluster_name, _uppercase_availability_zone(az))

  response = client.describe_subnets(
    Filters=[
        {
            'Name': 'availability-zone',
            'Values': [
                az,
            ]
        },
        {
            'Name': 'tag:Name',
            'Values': [subnet_name]
        }
    ],
    SubnetIds=subnet_ids
    )['Subnets']
  if not response:
    raise Exception("can not find subnet " + subnet_name)
  subnet_id = response[0]['SubnetId']

  # find security_group_id
  security_groups = client.describe_security_groups(
    Filters=[
        {
            'Name': 'vpc-id',
            'Values': [
                vpc_id,
            ]
        },
      ],
    )['SecurityGroups']

  for security_group in security_groups:
    if security_group['GroupName'].find('ClusterSharedNodeSecurityGroup') != -1:
      security_group_id = security_group['GroupId']
      break

  return vpc_id, subnet_id, security_group_id


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO,
                      format=('%(asctime)s %(name)-12s %(levelname)-8s %(message)s'),
                      datefmt='%Y-%m-%dT%H:%M:%S',
                      )
  logging.getLogger().setLevel(logging.INFO)

  args = parse_arguments()
  logging.info(args)

  benchmark_dir = str(os.environ['BENCHMARK_DIR'])

  if not os.path.exists(benchmark_dir):
    try:
      os.makedirs(benchmark_dir)
    except OSError:
      pass

  logs_dir = os.path.join(benchmark_dir, "logs")
  if not os.path.exists(logs_dir):
    try:
      os.makedirs(logs_dir)
    except OSError:
      pass

  cluster_manifest_path = os.path.join(benchmark_dir, "eksctl-cluster-config.yaml")
  deploy_utils.download_s3_file(args.cluster_config, cluster_manifest_path)
  logging.info("Download EKS cluster config: %s", args.cluster_config)

  # Customization here to change cluster spec
  with open(cluster_manifest_path, "r") as stream:
    cluster_spec = yaml.load(stream)

  cluster_spec['metadata']['name'] = args.cluster_name
  cluster_spec['metadata']['region'] = args.region
  # TODO this is not good, let's use more elegant config to replace it.
  single_availability_zone = cluster_spec['nodeGroups'][0]['availabilityZones'][0]

  with open(cluster_manifest_path, "w") as stream:
    yaml.dump(cluster_spec, stream, default_flow_style=False, allow_unicode=True)

  # Create target kubeconfig file in shared folder.
  kubeconfig_file_path = os.path.join(benchmark_dir, "kubeconfig")
  if not os.path.exists(kubeconfig_file_path):
    open(kubeconfig_file_path, 'a').close()

  # Create cluster using cluster_config file
  create_cluster_log = util.run(["eksctl", "create", "cluster", "--config-file=" + cluster_manifest_path, "--kubeconfig=" + kubeconfig_file_path])
  logging.info("Successfully create cluster")

  # Collect logs
  log_file = os.path.join(logs_dir, "start_cluster.log")
  with open(log_file, "w") as text_file:
    text_file.write(create_cluster_log)

  # Create config file for storage
  vpc_id, subnet_id, security_group_id = get_eks_network_info(args.cluster_name, single_availability_zone)
  storage_spec = {}
  storage_spec['vpc'] = vpc_id
  storage_spec['subnet'] = subnet_id
  storage_spec['security-group'] = security_group_id

  storage_file_path = os.path.join(benchmark_dir, "storage-config.yaml")
  #if not os.path.exists(storage_file_path):
  with open(storage_file_path, 'w') as stream:
    yaml.dump(storage_spec, stream, default_flow_style=False, allow_unicode=True)

  sys.exit(0)

import argparse
import logging
import yaml
import datetime
import time
import urllib
import os
import boto3

from kubernetes import client as k8s_client
from kubernetes.client import rest
from benchmark.test import deploy_utils
from kubeflow.testing import util


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "--namespace", default='default', type=str, help=("The namespace to use."))
  parser.add_argument(
    "--base_dir",
    default=None,
    type=str,
    help=("The source directory of all repositories."))

  parser.add_argument(
    "--storage_backend",
    default="fsx",
    type=str,
    help=("Dataset storage backend"))

  parser.add_argument(
    "--experiment_id",
    default=None,
    type=str,
    help=("Tag value for cluster key"))

  parser.add_argument(
    "--s3_import_path",
    default=None,
    type=str,
    help=("Tag value for cluster key"))

  args, _ = parser.parse_known_args()
  return args

def get_cluster_network_info(cluster_manifest_path):
  with open(cluster_manifest_path, "r") as stream:
    cluster_spec = yaml.load(stream)

  worker_nodes = cluster_spec['cluster-state']['worker-nodes']
  for instance_id, worker_node in worker_nodes.items():
    vpc_id = worker_node['vpc-id']
    subnet_id = worker_node['subnet-id']
    security_group_id = worker_node['security-groups'][0]['group-id']

  return vpc_id, subnet_id, security_group_id

def install_efs(experiment_id, subnet_id, security_group_id):
  """Install Elastic File System"""

  client = boto3.client('efs')
  fs = client.create_file_system(
    CreationToken=experiment_id,
    PerformanceMode='maxIO',
    Encrypted=False,
    ThroughputMode='bursting',
    Tags=[
      {
        'Key': 'experiment_id',
        'Value': experiment_id
      },
    ]
  )

  fs_desc = client.describe_file_systems(FileSystemId=fs['FileSystemId'])
  while fs_desc['FileSystems'][0]['LifeCycleState'] != 'available':
    time.sleep(5)
    fs_desc = client.describe_file_systems(FileSystemId=fs['FileSystemId'])
    print("EFS state: {0}".format(fs_desc['FileSystems'][0]['LifeCycleState']))

  response = client.create_mount_target(
    FileSystemId=fs['FileSystemId'],
    SubnetId=subnet_id,
    SecurityGroups=[
        security_group_id,
    ]
  )

  mount_desc = client.describe_mount_targets(MountTargetId=response['MountTargetId'])
  while mount_desc['MountTargets'][0]['LifeCycleState'] != 'available':
    time.sleep(5)
    mount_desc = client.describe_mount_targets(MountTargetId=response['MountTargetId'])
    print("EFS state: {0}".format(mount_desc['MountTargets'][0]['LifeCycleState']))

  add_config_entry("external_file_system_id", fs['FileSystemId'])
  add_config_entry("mount_target_id", response['MountTargetId'])

  return fs['FileSystemId']


def install_fsx(experiment_id, subnet_id, security_group_id, s3_import_path=None):
  """Install FSx for Lustre"""
  client = boto3.client('fsx')

  fs = client.create_file_system(
    ClientRequestToken=experiment_id,
    FileSystemType='LUSTRE',
    StorageCapacity=3600,
    SubnetIds=[
        subnet_id,
    ],
    SecurityGroupIds=[
        security_group_id,
    ],
    Tags=[
      {
        'Key': 'experiment_id',
        'Value': experiment_id
      },
    ],
    LustreConfiguration= {
      'ImportPath': s3_import_path
    }
  )

  fs_desc = client.describe_file_systems(FileSystemIds=[fs['FileSystem']['FileSystemId']])
  while fs_desc['FileSystems'][0]['Lifecycle'] != 'AVAILABLE':
    time.sleep(5)
    fs_desc = client.describe_file_systems(FileSystemIds=[fs['FileSystem']['FileSystemId']])
    print("FSX state: {0}".format(fs_desc['FileSystems'][0]['Lifecycle']))

  # record file system id to delete in the future.
  add_config_entry("external_file_system_id", fs['FileSystem']['FileSystemId'])

  return fs['FileSystem']['FileSystemId']

def add_config_entry(key, value):
  benchmark_dir = str(os.environ['BENCHMARK_DIR'])
  cluster_manifest_path = os.path.join(benchmark_dir, "aws-k8s-tester-eks.yaml")

  with open(file_path, "r") as stream:
    cluster_spec = yaml.load(stream)

  with open(file_path, "w") as stream:
    cluster_spec[key] = value
    yaml.dump(cluster_spec, stream, default_flow_style=False, allow_unicode=True)


def install_addon():
  """Install Benchmark Addons."""
  logging.basicConfig(level=logging.INFO,
                      format=('%(asctime)s %(name)-12s %(levelname)-8s %(message)s'),
                      datefmt='%Y-%m-%dT%H:%M:%S',
                      )
  logging.getLogger().setLevel(logging.INFO)

  args = parse_args()
  namespace = args.namespace
  base_dir = args.base_dir
  storage_backend = args.storage_backend
  experiment_id = args.experiment_id
  s3_import_path = args.s3_import_path

  # read network information from file
  benchmark_dir = str(os.environ['BENCHMARK_DIR'])
  cluster_manifest_path = os.path.join(benchmark_dir, "aws-k8s-tester-eks.yaml")
  vpc_id, subnet_id, security_group_id = get_cluster_network_info(cluster_manifest_path)

  # Install storage
  if storage_backend == 'fsx':
    # We want to make sure 988 is open for FSx
    ec2 = boto3.resource('ec2')
    security_group = ec2.SecurityGroup(security_group_id)
    security_group.authorize_ingress(IpProtocol="tcp",CidrIp="0.0.0.0/0",FromPort=988,ToPort=988)

    fs_id = install_fsx(experiment_id, subnet_id, security_group_id, s3_import_path)
  else if storage_backend == 'efs':
    fs_id = install_efs(experiment_id, subnet_id, security_group_id)

if __name__ == "__main__":
  install_addon()
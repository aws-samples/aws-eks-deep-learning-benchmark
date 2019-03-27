import argparse
import os
import io
import datetime
import logging
import subprocess
import time
import sys
import yaml

from kubeflow.testing import util
from benchmark.test import deploy_utils

def parse_arguments():
  # create the top-level parser
  parser = argparse.ArgumentParser(description="Submit benchmark test.")

  parser.add_argument(
    "--region",
    default="us-west-2",
    type=str,
    help="AWS Region.")

  parser.add_argument(
    "--az",
    default="us-west-2a",
    type=str,
    help="AWS Availability Azones, use comma to separate if this is an array.")

  parser.add_argument(
    "--placement_group",
    dest="placement_group",
    action="store_true",
    help=("Use plaecement_group to reduce network cost."))

  parser.add_argument(
    "--no-placement_group", dest="placement_group", action="store_false")

  parser.add_argument(
    "--cluster_version",
    default="1.11",
    type=str,
    help="The zone to create the AWS cluster.")

  parser.add_argument(
    "--ami",
    default="ami-095922d81242d0528",
    type=str,
    help="Amazon EKS-Optimized AMI with GPU Support.")

  parser.add_argument(
    "--instance_type",
    default="p3.16xlarge",
    type=str,
    help="AWS EC2 Instance Types")

  parser.add_argument(
    "--node_count",
    default="",
    type=str,
    help="Number of instacnes in worker group ASG.")

  # Parse the args
  args = parser.parse_args()
  return args

if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO,
                      format=('%(asctime)s %(name)-12s %(levelname)-8s %(message)s'),
                      datefmt='%Y-%m-%dT%H:%M:%S',
                      )
  logging.getLogger().setLevel(logging.INFO)

  args = parse_arguments()
  logging.info(args)

  benchmark_dir = str(os.environ['BENCHMARK_DIR'])
  cluster_manifest_path = os.path.join(benchmark_dir, "aws-k8s-tester-eks.yaml")

  if not os.path.exists(benchmark_dir):
    try: 
      os.makedirs(benchmark_dir)
    except OSError:
      pass

  logs_dir = os.path.join(benchmark_dir, "output", "logs")
  if not os.path.exists(logs_dir):
    try: 
      os.makedirs(logs_dir)
    except OSError:
      pass

  # Generate cluster manifest
  config_log = util.run(["aws-k8s-tester", "eks", "create", "config", "--path", cluster_manifest_path])
  logging.info("Generate EKS cluster manifest: %s", cluster_manifest_path)

  # Customization here to change cluster spec
  with open(cluster_manifest_path, "r") as stream: 
    cluster_spec = yaml.load(stream)
  
  # TODO: fix on aws-k8s-tester side? 
  kubeconfig_file_path = os.path.join(benchmark_dir, "kubeconfig")
  if not os.path.exists(kubeconfig_file_path):
    open(kubeconfig_file_path, 'a').close()

  # we already package `aws-iam-authenticator` in path.
  cluster_spec['aws-iam-authenticator-path'] = "/usr/local/bin/aws-iam-authenticator"
  cluster_spec['enable-worker-node-ssh'] = False
  cluster_spec['kubeconfig-path'] = kubeconfig_file_path
  cluster_spec["aws-region"] = args.region
  cluster_spec['worker-node-instance-type'] = args.instance_type
  cluster_spec['worker-node-ami'] = args.ami
  cluster_spec['node-count'] = args.node_count

  with open(cluster_manifest_path, "w") as stream: 
    yaml.dump(cluster_spec, stream, default_flow_style=False, allow_unicode=True)

  deploy_utils.ensure_aws_credentials()

  # Create cluster based on modified manifest
  create_cluster_log = util.run(["aws-k8s-tester", "eks", "create", "cluster", "--path", cluster_manifest_path])
  #create_cluster_log = util.run(["aws-k8s-tester", "eks", "create", "cluster", "-h"])
  logging.info("Successfully create cluster")

  # Collect logs
  log_file = os.path.join(logs_dir, "start_cluster.log")
  with open(log_file, "w") as text_file:
    text_file.write(config_log)
    text_file.write(create_cluster_log)
 
  sys.exit(0)

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

def uninstall_efs(experiment_id, fs_id, mount_target_id):
  """Install Elastic File System"""

  client = boto3.client('efs')
  # Delete mount targets
  response = client.delete_mount_target(
    MountTargetId=mount_target_id
  )

  try:
    mount_desc = client.describe_mount_targets(MountTargetId=mount_target_id)
    while mount_desc['MountTargets'][0]['LifeCycleState'] == 'deleting':
      time.sleep(5)
      mount_desc = client.describe_mount_targets(MountTargetId=mount_target_id)
      print("EFS state: {0}".format(mount_desc['MountTargets'][0]['LifeCycleState']))
  except Exception:
    print("EFS Mount Target {0} has been deleted, ignore this error".format(mount_target_id))

  fs = client.delete_file_system(
    FileSystemId=fs_id,
    ClientRequestToken=experiment_id
  )

  try:
    fs_desc = client.describe_file_systems(FileSystemId=fs_id)
    while fs_desc['FileSystems'][0]['LifeCycleState'] == 'deleting':
      time.sleep(5)
      fs_desc = client.describe_file_systems(FileSystemId=fs['FileSystemId'])
      print("EFS state: {0}".format(fs_desc['FileSystems'][0]['LifeCycleState']))
  except Exception:
    print("EFS Filesystem {0} has been deleted, ignore this error".format(fs_id))

def uninstall_fsx(experiment_id, fs_id):
  """Install FSx for Lustre"""
  client = boto3.client('fsx')

  fs = client.delete_file_system(
    FileSystemId=fs_id,
    ClientRequestToken=experiment_id
  )
  try:
    fs_desc = client.describe_file_systems(FileSystemIds=[fs['FileSystemId']])
    while fs_desc['FileSystems'][0]['Lifecycle'] == 'DELETING':
      time.sleep(5)
      # Updates metadata
      fs_desc = client.describe_file_systems(FileSystemIds=[fs['FileSystemId']])
      print("FSX state: {0}".format(fs_desc['FileSystems'][0]['Lifecycle']))
  except Exception:
    print("FSx Lustre FileSystem {0} has been deleted, ignore this error".format(fs_id))

def get_config_entry(file_path, key):
  with open(file_path, "r") as stream:
    cluster_spec = yaml.load(stream)
  return cluster_spec[key]


def uninstall_addon():
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
  vpc_id, subnet_id, security_group_id = get_cluster_network_info()

  fs_id = get_config_try(cluster_manifest_path, "external_file_system_id")


  # Install storage
  if storage_backend == 'fsx':
    # We want to make sure 988 is open for FSx
    ec2 = boto3.resource('ec2')
    security_group = ec2.SecurityGroup(security_group_id)
    security_group.revoke_ingress(IpProtocol="tcp",CidrIp="0.0.0.0/0",FromPort=988,ToPort=988)

    uninstall_fsx(experiment_id, fs_id)
  else if storage_backend == 'efs':

    mount_target_id = get_config_try(cluster_manifest_path, "mount_target_id")
    uninstall_efs(experiment_id, fs_id, mount_target_id)


if __name__ == "__main__":
  uninstall_addon()
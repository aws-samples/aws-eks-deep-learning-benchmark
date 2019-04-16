import argparse
import logging
import yaml
import datetime
import time
import urllib
import os
import boto3
from botocore.exceptions import ClientError


# need to delet PV and PVC first?
def parse_args():
  parser = argparse.ArgumentParser()

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

def get_cluster_network_info(storage_config_path):
  with open(storage_config_path, "r") as stream:
    storage_spec = yaml.load(stream)

  return storage_spec['vpc'], storage_spec['subnet'], storage_spec['security-group']

def uninstall_efs(experiment_id, fs_id, mount_target_id):
  """Install Elastic File System"""

  client = boto3.client('efs')
  # Delete mount targets
  logging.info("Deleting EFS Mount Target")
  try:
    response = client.delete_mount_target(
      MountTargetId=mount_target_id
    )
    mount_desc = client.describe_mount_targets(MountTargetId=mount_target_id)
    while mount_desc['MountTargets'][0]['LifeCycleState'] == 'deleting':
      time.sleep(30)
      mount_desc = client.describe_mount_targets(MountTargetId=mount_target_id)
      logging.info("EFS Mount Target state: %s, wait 30s..", mount_desc['MountTargets'][0]['LifeCycleState'])
  except Exception:
    logging.info("EFS Mount Target %s has been deleted, ignore this error", mount_target_id)

  logging.info("Deleting EFS File System")
  try:
    fs = client.delete_file_system(
      FileSystemId=fs_id,
    )
    fs_desc = client.describe_file_systems(FileSystemId=fs_id)
    while fs_desc['FileSystems'][0]['LifeCycleState'] == 'deleting':
      time.sleep(30)
      fs_desc = client.describe_file_systems(FileSystemId=fs_id)
      logging.info("EFS FileSystem state: %s, wait 30s..", fs_desc['FileSystems'][0]['LifeCycleState'])
  except Exception:
    logging.info("EFS Filesystem %s has been deleted, ignore this error", fs_id)

def uninstall_fsx(experiment_id, fs_id):
  """Install FSx for Lustre"""
  client = boto3.client('fsx')

  try:
    logging.info("Deleting FSx %s File System", fs_id)
    fs = client.delete_file_system(
      FileSystemId=fs_id
    )
    fs_desc = client.describe_file_systems(FileSystemIds=[fs_id])
    while fs_desc['FileSystems'][0]['Lifecycle'] == 'DELETING':
      time.sleep(30)
      # Updates metadata
      fs_desc = client.describe_file_systems(FileSystemIds=[fs_id])
      logging.info("FSX File System state: %s, wait 30s..", fs_desc['FileSystems'][0]['Lifecycle'])
  except ClientError as e:
    logging.error("Received error: %s", e)
    logging.info("FSx Lustre FileSystem %s has been deleted, ignore this error", fs_id)

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
  storage_backend = args.storage_backend
  experiment_id = args.experiment_id

  # read network information from file
  benchmark_dir = str(os.environ['BENCHMARK_DIR'])
  storage_config_path = os.path.join(benchmark_dir, "storage-config.yaml")
  vpc_id, subnet_id, security_group_id = get_cluster_network_info(storage_config_path)

  try:
    fs_id = get_config_entry(storage_config_path, "external-file-system-id")
  except KeyError as e:
    logging.error("Received error: %s", e)
    logging.info("external-file-system-id does not exists which means storage installation may failed. Skip this step")
    return

  # Install storage
  if storage_backend == 'fsx':
    # We want to make sure 988 is open for FSx
    # try:
    #   ec2 = boto3.resource('ec2')
    #   security_group = ec2.SecurityGroup(security_group_id)
    #   security_group.revoke_ingress(IpProtocol="tcp",CidrIp="0.0.0.0/0",FromPort=988,ToPort=988)
    # except ClientError as e:
    #   logging.error("Received error: %s", e)
    #   if e.response['Error']['Code'] != 'InvalidPermission.NotFound':
    #     raise
    #   else:
    #     logging.info("Security Group doesn't have this rule, skip revoking ingress.")

    uninstall_fsx(experiment_id, fs_id)
  elif storage_backend == 'efs':
    mount_target_id = get_config_entry(storage_config_path, "mount-target-id")
    uninstall_efs(experiment_id, fs_id, mount_target_id)
  else:
    raise Exception('Unsupported File Storage')


if __name__ == "__main__":
  uninstall_addon()
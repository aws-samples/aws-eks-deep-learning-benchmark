import argparse
import logging
import yaml
import datetime
import time
import urllib
import os
import boto3
from botocore.exceptions import ClientError


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

  parser.add_argument(
    "--s3_import_path",
    default=None,
    type=str,
    help=("Tag value for cluster key"))

  args, _ = parser.parse_known_args()
  return args

def get_cluster_network_info(storage_config_path):
  with open(storage_config_path, "r") as stream:
    storage_spec = yaml.load(stream)

  return storage_spec['vpc'], storage_spec['subnet'], storage_spec['security-group']

def install_efs(experiment_id, subnet_id, security_group_id):
  """Install Elastic File System"""

  client = boto3.client('efs')

  logging.info("Ceating EFS FileSystem Storage")
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

  logging.info("EFS FileSystem Create Response %s", fs)

  fs_desc = client.describe_file_systems(FileSystemId=fs['FileSystemId'])
  while fs_desc['FileSystems'][0]['LifeCycleState'] != 'available':
    time.sleep(30)
    fs_desc = client.describe_file_systems(FileSystemId=fs['FileSystemId'])
    logging.info("EFS FileSystem state: %s, waiting for 30s..", fs_desc['FileSystems'][0]['LifeCycleState'])

  logging.info("Ceating EFS %s Mount Target with subnet %s and security group %s", fs['FileSystemId'], subnet_id, security_group_id)
  response = client.create_mount_target(
    FileSystemId=fs['FileSystemId'],
    SubnetId=subnet_id,
    SecurityGroups=[
        security_group_id,
    ]
  )

  mount_desc = client.describe_mount_targets(MountTargetId=response['MountTargetId'])
  while mount_desc['MountTargets'][0]['LifeCycleState'] != 'available':
    time.sleep(30)
    mount_desc = client.describe_mount_targets(MountTargetId=response['MountTargetId'])
    logging.info("EFS Mount Target tate: %s, waiting for 30s..", mount_desc['MountTargets'][0]['LifeCycleState'])

  add_config_entry("external-file-system-id", fs['FileSystemId'])
  add_config_entry("mount-target-id", response['MountTargetId'])

  return fs['FileSystemId']


def install_fsx(experiment_id, subnet_id, security_group_id, s3_import_path=None):
  """Install FSx for Lustre"""
  client = boto3.client('fsx')
  logging.info("Creating FSx for Lustre storage")
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

  logging.info("FSx FileSystem Create Response %s", fs)

  fs_desc = client.describe_file_systems(FileSystemIds=[fs['FileSystem']['FileSystemId']])
  while fs_desc['FileSystems'][0]['Lifecycle'] != 'AVAILABLE':
    time.sleep(30)
    fs_desc = client.describe_file_systems(FileSystemIds=[fs['FileSystem']['FileSystemId']])
    logging.info("FSX state: %s, waiting for 30s..", fs_desc['FileSystems'][0]['Lifecycle'])

  # record file system id to delete in the future.
  add_config_entry("external-file-system-id", fs['FileSystem']['FileSystemId'])
  add_config_entry("fsx-dns-name", fs['FileSystem']['DNSName'])

  return fs['FileSystem']['FileSystemId']

def add_config_entry(key, value):
  benchmark_dir = str(os.environ['BENCHMARK_DIR'])
  cluster_manifest_path = os.path.join(benchmark_dir, "storage-config.yaml")

  with open(cluster_manifest_path, "r") as stream:
    cluster_spec = yaml.load(stream)

  with open(cluster_manifest_path, "w") as stream:
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
  storage_backend = args.storage_backend
  experiment_id = args.experiment_id
  s3_import_path = args.s3_import_path

  # read network information from file
  benchmark_dir = str(os.environ['BENCHMARK_DIR'])
  storage_config_path = os.path.join(benchmark_dir, "storage-config.yaml")
  vpc_id, subnet_id, security_group_id = get_cluster_network_info(storage_config_path)

  # Install storage
  if storage_backend == 'fsx':
    # We want to make sure 988 is open for FSx, ClusterSharedSecurityGroup open this port
    # try:
    #   ec2 = boto3.resource('ec2')
    #   security_group = ec2.SecurityGroup(security_group_id)
    #   security_group.authorize_ingress(IpProtocol="tcp",CidrIp="0.0.0.0/0",FromPort=988,ToPort=988)
    # except ClientError as e:
    #   logging.error("Received error: %s", e)
    #   if e.response['Error']['Code'] != 'InvalidPermission.Duplicate':
    #     raise
    #   else:
    #     logging.info("Security Group already has this rule, skip authorizing ingress.")
    fs_id = install_fsx(experiment_id, subnet_id, security_group_id, s3_import_path)
    # create efs
  elif storage_backend == 'efs':
    fs_id = install_efs(experiment_id, subnet_id, security_group_id)

if __name__ == "__main__":
  install_addon()
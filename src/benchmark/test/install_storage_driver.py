import argparse
import logging
import yaml
import datetime
import time
import urllib
import os

from kubeflow.testing import util

def parse_args():
  parser = argparse.ArgumentParser()

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
    "--pvc_name",
    default="dataset-claim",
    type=str,
    help=("Dataset persistent volume claim"))

  args, _ = parser.parse_known_args()
  return args

def install_fsx_driver(fs_id, fsx_dns_name, csi_manifest_folder):
  """Install FSX CSI drivers on the cluster."""
  logging.info("Install FSX CSI Drivers.")

  secret_file_path = csi_manifest_folder+"/secret.yaml"
  with open(secret_file_path, "r") as stream:
    secret_file = yaml.load(stream)

  with open(secret_file_path, "w") as stream:
    secret_file['stringData']['key_id'] = str(os.environ['AWS_ACCESS_KEY_ID'])
    secret_file['stringData']['access_key'] = str(os.environ['AWS_SECRET_ACCESS_KEY'])
    yaml.dump(secret_file, stream, default_flow_style=False, allow_unicode=True)

  util.run(["kubectl", "apply", "-f", "secret.yaml"], cwd=csi_manifest_folder)
  util.run(["kubectl", "apply", "-f", "manifest.yaml"], cwd=csi_manifest_folder)


  pv_path = csi_manifest_folder + "/pv.yaml"
  with open(pv_path, "r") as stream:
    pv_file = yaml.load(stream)

  with open(pv_path, "w") as stream:
    pv_file['spec']['csi']['volumeHandle'] = fs_id
    pv_file['spec']['csi']['volumeAttributes']['dnsname'] = fsx_dns_name
    yaml.dump(pv_file, stream, default_flow_style=False, allow_unicode=True)

  util.run(["kubectl", "apply", "-f", "sc.yaml"], cwd=csi_manifest_folder)
  util.run(["kubectl", "apply", "-f", "pv.yaml"], cwd=csi_manifest_folder)
  util.run(["kubectl", "apply", "-f", "pvc.yaml"], cwd=csi_manifest_folder)

def install_efs_driver(fs_id, csi_manifest_folder):
  """Install EFS CSI drivers on the cluster."""
  logging.info("Install EFS CSI Drivers.")

  util.run(["kubectl", "apply", "-f", "controller.yaml"], cwd=csi_manifest_folder)
  util.run(["kubectl", "apply", "-f", "node.yaml"], cwd=csi_manifest_folder)


  pv_path = csi_manifest_folder + "/pv.yaml"
  with open(pv_path, "r") as stream:
    pv_file = yaml.load(stream)

  with open(pv_path, "w") as stream:
    pv_file['spec']['csi']['volumeHandle'] = fs_id
    yaml.dump(pv_file, stream, default_flow_style=False, allow_unicode=True)

  util.run(["kubectl", "apply", "-f", "sc.yaml"], cwd=csi_manifest_folder)
  util.run(["kubectl", "apply", "-f", "pv.yaml"], cwd=csi_manifest_folder)
  util.run(["kubectl", "apply", "-f", "pvc.yaml"], cwd=csi_manifest_folder)


def get_config_entry(file_path, key):
  with open(file_path, "r") as stream:
    cluster_spec = yaml.load(stream)
  return cluster_spec[key]


def install_addon():
  """Install Benchmark Addons."""
  logging.basicConfig(level=logging.INFO,
                      format=('%(asctime)s %(name)-12s %(levelname)-8s %(message)s'),
                      datefmt='%Y-%m-%dT%H:%M:%S',
                      )
  logging.getLogger().setLevel(logging.INFO)

  args = parse_args()
  base_dir = args.base_dir
  storage_backend = args.storage_backend

  benchmark_dir = str(os.environ['BENCHMARK_DIR'])
  storage_config_path = os.path.join(benchmark_dir, "storage-config.yaml")

  fs_id = get_config_entry(storage_config_path, "external-file-system-id")
  csi_manifest_folder = os.path.join(base_dir, "src", "jeffwan", "ml-benchmark", "deploy", storage_backend)

  # Setup CSI Driver Plugin
  if storage_backend == 'fsx':
    fsx_dns_name = get_config_entry(storage_config_path, "fsx-dns-name")
    install_fsx_driver(fs_id, fsx_dns_name, csi_manifest_folder)
  elif storage_backend == 'efs':
    install_efs_driver(fs_id, csi_manifest_folder)
  else:
    raise Exception('Unsupported File Storage')

if __name__ == "__main__":
  install_addon()
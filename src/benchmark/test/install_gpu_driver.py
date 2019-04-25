import argparse
import logging
import yaml
import datetime
import time
import urllib
import os

from kubernetes import client as k8s_client
from kubernetes.client import rest
from benchmark.test import deploy_utils
from kubeflow.testing import util


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument("--namespace", default='default', type=str, help=("The namespace to use."))
  parser.add_argument("--base_dir", default=None, type=str, help=("The source directory of all repositories."))

  args, _ = parser.parse_known_args()
  return args

def install_gpu_drivers(api_client):
  """Install GPU drivers on the cluster."""
  logging.info("Install GPU Drivers.")
  # Fetch the daemonset to install the drivers.
  # TODO: Get cluster version and then install compatible driver version
  link = "https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v1.11/nvidia-device-plugin.yml"  # pylint: disable=line-too-long
  logging.info("Using daemonset file: %s", link)
  f = urllib.urlopen(link)
  daemonset_spec = yaml.load(f)
  ext_client = k8s_client.ExtensionsV1beta1Api(api_client)
  try:
    namespace = daemonset_spec["metadata"]["namespace"]
    ext_client.create_namespaced_daemon_set(namespace, daemonset_spec)
  except rest.ApiException as e:
    # Status appears to be a string.
    if e.status == 409:
      logging.info("GPU driver daemon set has already been installed")
    else:
      raise

def wait_for_gpu_driver_install(api_client,
                                timeout=datetime.timedelta(minutes=10)):
  """Wait until some nodes are available with GPUs."""

  end_time = datetime.datetime.now() + timeout
  api = k8s_client.CoreV1Api(api_client)
  while datetime.datetime.now() <= end_time:
    nodes = api.list_node()
    for n in nodes.items:
      if n.status.capacity.get("nvidia.com/gpu", 0) > 0:
        logging.info("GPUs are available.")
        return
    logging.info("Waiting for GPUs to be ready.")
    time.sleep(15)
  logging.error("Timeout waiting for GPU nodes to be ready.")
  raise TimeoutError("Timeout waiting for GPU nodes to be ready.")

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
  kubeconfig_path = str(os.environ['KUBECONFIG'])
  api_client = deploy_utils.create_k8s_client(kubeconfig_path)

  # Setup GPU Device Plugin
  install_gpu_drivers(api_client)
  wait_for_gpu_driver_install(api_client)

if __name__ == "__main__":
  install_addon()
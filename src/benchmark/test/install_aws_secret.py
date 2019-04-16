import argparse
import logging
import yaml
import datetime
import time
import urllib
import os
import base64

from kubernetes import client as k8s_client
from kubernetes.client import rest
from benchmark.test import deploy_utils
from kubeflow.testing import util


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "--namespace", default='default', type=str, help=("The namespace to use."))

  parser.add_argument(
    "--aws_secret_name",
    default="aws-secret",
    type=str,
    help=("The aws-secret to be created."))

  args, _ = parser.parse_known_args()
  return args

  raise TimeoutError("Timeout waiting for service %s to be ready.", service_name)

def install_aws_secret(api_client, namespace, secret_name, aws_access_key_id, aws_secret_access_key):
  """Install AWS secret on the cluster.
  Return:
    secret: Secret for AWS credentials
  """
  logging.info("Install AWS secret %s", secret_name)

  corev1_api = k8s_client.CoreV1Api(api_client)
  try:
    secret = k8s_client.V1Secret()
    secret.metadata = k8s_client.V1ObjectMeta(name=secret_name)
    secret.type = "Opaque"
    secret.data = {
      "AWS_ACCESS_KEY_ID": aws_access_key_id,
      "AWS_SECRET_ACCESS_KEY": aws_secret_access_key
      }

    corev1_api.create_namespaced_secret(namespace, secret)
  except rest.ApiException as e:
    # Status appears to be a string.
    if e.status == 409:
      logging.info("Github token has already been installed")
    else:
      raise

def install_addon():
  """Install Benchmark Addons."""
  logging.basicConfig(level=logging.INFO,
                      format=('%(asctime)s %(name)-12s %(levelname)-8s %(message)s'),
                      datefmt='%Y-%m-%dT%H:%M:%S',
                      )
  logging.getLogger().setLevel(logging.INFO)

  args = parse_args()
  namespace = args.namespace
  kubeconfig_path = str(os.environ['KUBECONFIG'])
  api_client = deploy_utils.create_k8s_client(kubeconfig_path)

  # Deploy Github Secret. Can be passed from user's parameter
  # get from env
  access_key_id = str(os.environ['AWS_ACCESS_KEY_ID'])
  access_key = str(os.environ['AWS_SECRET_ACCESS_KEY'])
  install_aws_secret(api_client, namespace, args.aws_secret_name, base64.b64encode(access_key_id), base64.b64encode(access_key))

if __name__ == "__main__":
  install_addon()
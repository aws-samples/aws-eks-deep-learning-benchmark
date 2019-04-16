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
  parser.add_argument(
    "--namespace", default='default', type=str, help=("The namespace to use."))
  parser.add_argument(
    "--base_dir",
    default=None,
    type=str,
    help=("The source directory of all repositories."))

  parser.add_argument(
    "--github_secret_name",
    default="github-token",
    type=str,
    help=("The github token to be created."))

  args, _ = parser.parse_known_args()
  return args

def create_deployment_object():
    # Configureate Pod template container
    container = client.V1Container(
        name="copy-dataset-worker",
        image="seedjeffwan/benchmark-runner:latest",
        
        )
    volume = client.V1Volume(
      persistent_volume_claim=
    )
    # Create and configurate a spec section
    template = client.V1PodTemplateSpec(
        spec=client.V1PodSpec(containers=[container], volumes=[volume]))
    # Create the specification of deployment
    spec = client.ExtensionsV1beta1DeploymentSpec(
        replicas=1,
        template=template)
    # Instantiate the deployment object
    deployment = client.ExtensionsV1beta1Deployment(
        api_version="extensions/v1beta1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=DEPLOYMENT_NAME),
        spec=spec)

    return deployment

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

  extv1_api = k8s_client.ExtensionsV1beta1Deployment(api_client)

  # need pvc, s3 bucket dataset name
  deployment = create_deployment_object()


  # Deploy Github Secret
  github_token = str(os.environ['GITHUB_TOKEN'])
  install_github_secret(api_client, namespace, args.github_secret_name, github_token)

def install_github_secret(api_client, namespace, secret_name, github_token):
  """Install Github secret on the cluster.
  Return:
    secret: Secret for Github token
  """
  logging.info("Install Github secret.")

  corev1_api = k8s_client.CoreV1Api(api_client)
  try:
    secret = client.V1Secret()
    secret.metadata = client.V1ObjectMeta(name=secret_name)
    secret.type = "Opaque"
    secret.data = {"GITHUB_TOKEN": github_token}

    corev1_api.create_namespaced_secret(namespace, secret)
  except rest.ApiException as e:
    # Status appears to be a string.
    if e.status == 409:
      logging.info("GPU driver daemon set has already been installed")
    else:
      raise


if __name__ == "__main__":
  install_addon()
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

  parser.add_argument(
    "--kubeflow_registry",
    default="github.com/jeffwan/kubeflow/tree/master/kubeflow",
    type=str,
    help=("The github token to be created."))

  parser.add_argument(
    "--kubebench_registry",
    default="github.com/kubeflow/kubebench/tree/master/kubebench",
    type=str,
    help=("The github token to be created."))

  args, _ = parser.parse_known_args()
  return args

def install_kubeflow(api_client, app_dir, namespace):
  """Deploy required kubeflow packages to run benchmark"""
  util.run(["ks", "generate", "argo", "argo"], cwd=app_dir)
  util.run(["ks", "generate", "tf-job-operator", "tf-job-operator"], cwd=app_dir)
  util.run(["ks", "generate", "mpi-operator", "mpi-operator"], cwd=app_dir)

  if namespace != 'default':
    cmd = "ks param set tf-job-operator namespace " + namespace
    util.run(cmd.split(), cwd=app_dir)

    cmd = "ks param set mpi-operator namespace " + namespace
    util.run(cmd.split(), cwd=app_dir)

    cmd = "ks param set argo namespace " + namespace
    util.run(cmd.split(), cwd=app_dir)

  cmd = "ks param set mpi-operator image mpioperator/mpi-operator:latest"
  util.run(cmd.split(), cwd=app_dir)

  apply_command = ["ks", "apply", "default", "-c", "argo",
                   "-c", "tf-job-operator",  "-c", "mpi-operator"]

  util.run(apply_command, cwd=app_dir)

def wait_for_kubeflow_install(api_client, namespace):
  """Wait until kubeflow components are up."""
  # Verify that the Argo operator is deployed.
  argo_deployment_name = "workflow-controller"
  logging.info("Verifying Argo controller started.")
  util.wait_for_deployment(api_client, namespace, argo_deployment_name)

  # Verify that the TfJob Operator is actually deployed.
  tf_job_deployment_name = "tf-job-operator"
  logging.info("Verifying TfJob controller started.")
  util.wait_for_deployment(api_client, namespace, tf_job_deployment_name)

  # Verify that the MPI Operator is deployed.
  mpi_job_deployment_name = "mpi-operator"
  logging.info("Verifying MPIJob controller started.")
  util.wait_for_deployment(api_client, namespace, mpi_job_deployment_name)

def install_kubebench_nfs(api_client, app_dir, namespace):
  """Deploy required kubeflow packages to run benchmark"""
  util.run(["ks", "pkg", "install", "kubebench/kubebench-quickstarter"], cwd=app_dir)
  util.run(["ks", "generate", "kubebench-quickstarter-service", "kubebench-quickstarter-service"], cwd=app_dir)
  util.run(["ks", "generate", "kubebench-quickstarter-volume", "kubebench-quickstarter-volume"], cwd=app_dir)

  util.run(["ks", "param", "set", "kubebench-quickstarter-service", "namespace", namespace], cwd=app_dir)
  util.run(["ks", "param", "set", "kubebench-quickstarter-volume", "namespace", namespace], cwd=app_dir)

  apply_command = ["ks", "apply", "default", "-c", "kubebench-quickstarter-service"]
  util.run(apply_command, cwd=app_dir)

  kubebench_nfs_deployment_name = "kubebench-nfs-deploy"
  kubebench_nfs_service_name = "kubebench-nfs-svc"
  logging.info("Verifying NFS deployment started")
  util.wait_for_deployment(api_client, namespace, kubebench_nfs_deployment_name)

  service = get_k8s_service(api_client, namespace, kubebench_nfs_service_name)
  util.run(["ks", "param", "set", "kubebench-quickstarter-volume", "nfsServiceIP", service.spec.cluster_ip], cwd=app_dir)
  apply_command = ["ks", "apply", "default", "-c", "kubebench-quickstarter-volume"]
  util.run(apply_command, cwd=app_dir)

def get_k8s_service(api_client, namespace, service_name):
  """Get service cluster IP.
  Args:
    api_client: K8s api client to use.
    namespace: The name space for the service.
    name: The name of the service.
  Returns:
    service: The deploy object describing the service.
  Raises:
    TimeoutError: If timeout waiting for service to be ready.
  """
  end_time = datetime.datetime.now() + datetime.timedelta(minutes=1)

  api_client = k8s_client.CoreV1Api(api_client)
  while datetime.datetime.now() <= end_time:
    service = api_client.read_namespaced_service(service_name, namespace)
    if not service.spec or not service.spec.cluster_ip:
      logging.info("Waiting for service to be ready.")
      time.sleep(15)
      continue
    logging.info("Service %s is available.", service_name)
    return service

  logging.error("Timeout waiting for service %s to be ready.", service_name)
  raise TimeoutError("Timeout waiting for service %s to be ready.", service_name)


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

  kubeflow_app_dir = os.path.join(base_dir, "ks-app")
  if os.path.exists(kubeflow_app_dir):
    logging.info("kubeflow app dir already exists. skip install")
    return

  # Setup ksonnet application
  app_dir = deploy_utils.setup_ks_app(base_dir, namespace, api_client, args.kubeflow_registry, args.kubebench_registry)

  # Deploy Kubeflow
  install_kubeflow(api_client, app_dir, namespace)
  wait_for_kubeflow_install(api_client, namespace)

  # change the namespace to default to set up nfs-volume and nfs-server
  namespace = "default"

  # Deploy NFS for kubebench
  install_kubebench_nfs(api_client, app_dir, namespace)


if __name__ == "__main__":
  install_addon()
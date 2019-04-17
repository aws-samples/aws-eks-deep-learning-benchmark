import datetime
import logging
import os
import ssl
import time
import uuid
import base64

import boto3
import botocore
from urlparse import urlparse

from kubernetes import client as k8s_client
from kubernetes import config
from kubernetes.client import rest

from kubeflow.testing import util  # pylint: disable=no-name-in-module

def set_clusterrole(namespace):
  cmd = "kubectl create clusterrolebinding default-admin-binding \
          --clusterrole=cluster-admin --serviceaccount=" + namespace + ":default"
  util.run(cmd.split())

def create_k8s_client(kubeconfig):
  # We need to load the kube config so that we can have credentials to
  # talk to the APIServer.
  util.load_kube_config(config_file=kubeconfig, persist_config=False)

  # Create an API client object to talk to the K8s master.
  api_client = k8s_client.ApiClient()

  return api_client

def _setup_test(api_client, run_label):
  """Create the namespace for the test.
  Returns:
    test_dir: The local test directory.
  """

  api = k8s_client.CoreV1Api(api_client)
  namespace = k8s_client.V1Namespace()
  namespace.api_version = "v1"
  namespace.kind = "Namespace"
  namespace.metadata = k8s_client.V1ObjectMeta(
    name=run_label, labels={
      "app": "kubeflow-e2e-test",
    })

  try:
    logging.info("Creating namespace %s", namespace.metadata.name)
    namespace = api.create_namespace(namespace)
    logging.info("Namespace %s created.", namespace.metadata.name)
  except rest.ApiException as e:
    if e.status == 409:
      logging.info("Namespace %s already exists.", namespace.metadata.name)
    else:
      raise

  return namespace

def setup_ks_app(base_app_dir, namespace, api_client, kubeflow_registry, kubebench_registry):
  """Create a ksonnet app for Kubeflow"""
  util.makedirs(base_app_dir)

  logging.info("Using directory to initiate ksonnet application: %s", base_app_dir)

  namespace_name = namespace
  namespace = _setup_test(api_client, namespace_name)
  logging.info("Using namespace: %s", namespace)

  if not os.getenv("GITHUB_TOKEN"):
    logging.warning("GITHUB_TOKEN not set; you will probably hit Github API "
                    "limits.")

  timestamp = datetime.datetime.now()
  app_name = "ks-app"
  app_dir = os.path.join(base_app_dir, app_name)

  # Initialize a ksonnet app.
  util.run(["ks", "init", app_name], cwd=base_app_dir)

  # Set the default namespace.
  util.run(["ks", "env", "set", "default", "--namespace=" + namespace_name], cwd=app_dir)

  # Add required registries
  registries = {
    "kubeflow": kubeflow_registry,
    "kubebench": kubebench_registry
  }
  for r in registries:
    util.run(["ks", "registry", "add", r, registries[r]], cwd=app_dir)

  # Install required packages
  packages = ["kubeflow/common", "kubeflow/argo", "kubeflow/tf-training",
              "kubeflow/kubebench", "kubeflow/mpi-job"]
  for p in packages:
    util.run(["ks", "pkg", "install", p], cwd=app_dir)

  return app_dir

def log_operation_status(operation):
  """A callback to use with wait_for_operation."""
  name = operation.get("name", "")
  status = operation.get("status", "")
  logging.info("Operation %s status %s", name, status)

def wait_for_operation(client,
                       project,
                       op_id,
                       timeout=datetime.timedelta(hours=1),
                       polling_interval=datetime.timedelta(seconds=5),
                       status_callback=log_operation_status):
  """Wait for the specified operation to complete.
  Args:
    client: Client for the API that owns the operation.
    project: project
    op_id: Operation id.
    timeout: A datetime.timedelta expressing the amount of time to wait before
      giving up.
    polling_interval: A datetime.timedelta to represent the amount of time to
      wait between requests polling for the operation status.
  Returns:
    op: The final operation.
  Raises:
    TimeoutError: if we timeout waiting for the operation to complete.
  """
  endtime = datetime.datetime.now() + timeout
  while True:
    try:
      op = client.operations().get(
        project=project, operation=op_id).execute()

      if status_callback:
        status_callback(op)

      status = op.get("status", "")
      # Need to handle other status's
      if status == "DONE":
        return op
    except ssl.SSLError as e:
      logging.error("Ignoring error %s", e)
    if datetime.datetime.now() > endtime:
      raise TimeoutError(
        "Timed out waiting for op: {0} to complete.".format(op_id))
    time.sleep(polling_interval.total_seconds())

  # Linter complains if we don't have a return here even though its unreachable.
  return None

def copy_job_config(src_dir, namespace):
  config.load_kube_config()

  v1 = k8s_client.CoreV1Api()
  nfs_server_pod = None
  ret = v1.list_namespaced_pod(namespace, watch=False)
  for i in ret.items:
    if(i.metadata.labels.get("role") != None) & (i.metadata.labels.get("role") == "nfs-server"):
      nfs_server_pod = i.metadata.name
  if nfs_server_pod is None:
    logging.info("nfs server pod NOT found")
    return 0

  cmd = "kubectl -n " + namespace + " exec " + nfs_server_pod + " -- mkdir -p /exports/config"
  util.run(cmd.split(), cwd=src_dir)

  cmd = "kubectl cp examples/tf_cnn_benchmarks/job_config.yaml " + namespace + \
          "/" + nfs_server_pod + ":/exports/config/job-config.yaml"
  util.run(cmd.split(), cwd=src_dir)

  return 1

def get_nfs_server_ip(name, namespace):

  config.load_kube_config()

  v1 = k8s_client.CoreV1Api()
  server_ip = None
  ret = v1.read_namespaced_service(name, namespace)
  if (ret != None) & (ret.spec.cluster_ip != None):
    server_ip = ret.spec.cluster_ip

  return server_ip

def wait_for_benchmark_job(job_name, namespace, timeout_minutes=20, replicas=1):
  """Wait for benchmark to be complete.
  Args:
    namespace: The name space for the deployment.
    job_name: The name of the benchmark workflow.
    timeout_minutes: Timeout interval in minutes.
    replicas: Number of replicas that must be running.
  Returns:
    deploy: The deploy object describing the deployment.
  Raises:
    TimeoutError: If timeout waiting for deployment to be ready.
  """
  end_time = datetime.datetime.now() + datetime.timedelta(minutes=timeout_minutes)
  config.load_kube_config()

  crd_api = k8s_client.CustomObjectsApi()
  GROUP = "argoproj.io"
  VERSION = "v1alpha1"
  PLURAL = "workflows"

  while datetime.datetime.now() < end_time:
    workflow = crd_api.get_namespaced_custom_object(GROUP, VERSION, namespace, PLURAL, job_name)
    if workflow and workflow['status'] and workflow['status']['phase'] and workflow['status']['phase'] == "Succeeded":
      logging.info("Job Completed")
      return workflow
    logging.info("Waiting for job %s:%s", namespace, job_name)
    time.sleep(10)
  logging.error("Timeout waiting for workflow %s in namespace %s to be "
                "complete", job_name, namespace)
  raise TimeoutError(
    "Timeout waiting for deployment {0} in namespace {1}".format(
      job_name, namespace))

class TimeoutError(Exception):  # pylint: disable=redefined-builtin
  """An error indicating an operation timed out."""

def cleanup_benchmark_job(app_dir, job_name):
  cmd = "ks delete default -c " + job_name
  util.run(cmd.split(), cwd=app_dir)

def cleanup_kb_job(app_dir, job_name):
  cmd = "ks delete default -c " + job_name
  util.run(cmd.split(), cwd=app_dir)
  cmd = "ks delete default -c nfs-volume"
  util.run(cmd.split(), cwd=app_dir)
  cmd = "ks delete default -c nfs-server"
  util.run(cmd.split(), cwd=app_dir)
  cmd = "ks delete default -c argo"
  util.run(cmd.split(), cwd=app_dir)
  cmd = "ks delete default -c tf-job-operator"
  util.run(cmd.split(), cwd=app_dir)
  cmd = "ks delete default -c mpi-operator"
  util.run(cmd.split(), cwd=app_dir)


def download_s3_file(s3_file_path, target_file_path):
  uri = urlparse(s3_file_path)
  bucket_name = uri.netloc
  item_key = uri.path.lstrip('/')

  try:
      s3 = boto3.resource('s3')
      s3.Bucket(bucket_name).download_file(item_key, target_file_path)
  except botocore.exceptions.ClientError as e:
      if e.response['Error']['Code'] == "404":
          logging.error("The object does not exist.")
      else:
          raise Exception("Can not download eksctl cluster config%s".format(s3_file_path))
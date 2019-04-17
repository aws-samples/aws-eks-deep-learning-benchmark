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
from urlparse import urlparse


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "--namespace", default='default', type=str, help=("The namespace to use."))
  parser.add_argument(
    "--s3_import_path", type=str, help=("The S3 dataset to copy to volume."))
  parser.add_argument(
    "--pvc", type=str, help=("Target persistent volume claim."))
  parser.add_argument(
    "--region", type=str, help=("Target persistent volume claim."))
  parser.add_argument(
    "--runner_image", type=str, default="seedjeffwan/benchmark-runner:20190415-fix", help=("Target persistent volume claim."))
  args, _ = parser.parse_known_args()
  return args


# s3://bucket/imagenet/           -> /mnt/imagenet/
# s3://bucket/imagenet            -> /mnt/imagenet/
# s3://bucket                     -> /mnt/
# s3://bucket/                    -> /mnt/
# s3://bucket/train.csv           -> /mnt/
# s3://bucket/imagenet/train.csv  -> /mnt/
def get_target_folder(s3_path):
  target_folder = ''
  ext = os.path.splitext(s3_path)[-1].lower()

  if ext != '':
    return target_folder

  dirs = urlparse(s3_path).path.split('/')
  for dir in dirs:
    if dir != '':
      return os.path.basename(os.path.normpath(s3_path))

  return target_folder

def wait_for_job(api_client,
                        namespace,
                        name,
                        timeout_minutes=20,
                        replicas=1):
  """Wait for deployment to be ready.
  Args:
    api_client: K8s api client to use.
    namespace: The name space for the deployment.
    name: The name of the deployment.
    timeout_minutes: Timeout interval in minutes.
    replicas: Number of replicas that must be running.
  Returns:
    deploy: The deploy object describing the deployment.
  Raises:
    TimeoutError: If timeout waiting for deployment to be ready.
  """
  # Wait for tiller to be ready
  end_time = datetime.datetime.now() + datetime.timedelta(
    minutes=timeout_minutes)

  ext_client = k8s_client.BatchV1Api(api_client)

  while datetime.datetime.now() < end_time:
    deploy = ext_client.read_namespaced_job(name, namespace)
    # ready_replicas could be None
    if (deploy.status.succeeded and
        deploy.status.succeeded >= replicas):
      logging.info("Job %s in namespace %s is ready", name, namespace)
      return deploy
    logging.info("Waiting for job %s in namespace %s", name, namespace)
    time.sleep(10)

  logging.error("Timeout waiting for Job %s in namespace %s to be "
                "ready", name, namespace)
  util.run(["kubectl", "describe", "job", "-n", namespace, name])
  raise TimeoutError(
    "Timeout waiting for job {0} in namespace {1}".format(
      name, namespace))


def create_job_object(runner_image, region, s3_path, pvc_name):
  target_folder = get_target_folder(s3_path)

  # Configureate Pod template container
  container = k8s_client.V1Container(
      name="copy-dataset-worker",
      image=runner_image,
      command=["aws"],
      args=["s3", "sync", s3_path, "/mnt/" + target_folder],
      volume_mounts=[k8s_client.V1VolumeMount(name="data-storage", mount_path='/mnt')],
      env=[k8s_client.V1EnvVar(name="AWS_REGION", value=region),
        k8s_client.V1EnvVar(name="AWS_ACCESS_KEY_ID", value_from=k8s_client.V1EnvVarSource(secret_key_ref=k8s_client.V1SecretKeySelector(key="AWS_ACCESS_KEY_ID", name="aws-secret"))),
        k8s_client.V1EnvVar(name="AWS_SECRET_ACCESS_KEY", value_from=k8s_client.V1EnvVarSource(secret_key_ref=k8s_client.V1SecretKeySelector(key="AWS_SECRET_ACCESS_KEY", name="aws-secret")))
        ],
    )
  volume = k8s_client.V1Volume(
    name='data-storage',
    persistent_volume_claim=k8s_client.V1PersistentVolumeClaimVolumeSource(claim_name=pvc_name)
  )
  # Create and configurate a spec section
  template = k8s_client.V1PodTemplateSpec(
      # metadata=k8s_client.V1ObjectMeta(labels={"app":"copy-dataset-worker"}),
      spec=k8s_client.V1PodSpec(containers=[container], volumes=[volume], restart_policy="OnFailure"))
  # Create the specification of deployment
  spec = k8s_client.V1JobSpec(
      # selector=k8s_client.V1LabelSelector(match_labels={"app":"copy-dataset-worker"}),
      template=template)
  # Instantiate the deployment object
  deployment = k8s_client.V1Job(
      api_version="batch/v1",
      kind="Job",
      metadata=k8s_client.V1ObjectMeta(name=container.name),
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
  kubeconfig_path = str(os.environ['KUBECONFIG'])
  api_client = deploy_utils.create_k8s_client(kubeconfig_path)

  batchv1_api = k8s_client.BatchV1Api(api_client)

  # need pvc, s3 bucket dataset name
  deployment = create_job_object(args.runner_image, args.region, args.s3_import_path, args.pvc)
  batchv1_api.create_namespaced_job(namespace, deployment)

  # describe
  logging.info("Wait for data copy finish.")
  wait_for_job(api_client, namespace, "copy-dataset-worker")
  logging.info("Finish copy data from %s to pvc %s", args.s3_import_path, args.pvc)

if __name__ == "__main__":
  install_addon()
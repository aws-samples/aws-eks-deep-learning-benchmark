import argparse
import logging
import sys
import os
import time

from benchmark.test import deploy_utils
from kubeflow.testing import util  # pylint: disable=no-name-in-module

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument(
    "--namespace", default='default', type=str, help=("The namespace to use."))
  parser.add_argument(
    "--experiment_name", default=None, type=str, help=("The namespace to use."))
  parser.add_argument(
    "--training_job_registry", default='github.com/kubeflow/kubeflow/tree/master/kubeflow',
    type=str, help=("The namespace to use."))
  parser.add_argument(
    "--training_job_pkg", default='mpi-job', type=str, help=("The namespace to use."))
  parser.add_argument(
    "--training_job_prototype", default='mpi-job-custom', type=str, help=("The namespace to use."))
  parser.add_argument(
    "--training_job_config", default=None, type=str, help=("The namespace to use."))

  parser.add_argument(
    "--github_secret_name", default='github-token', type=str, help=("The namespace to use."))

  parser.add_argument(
    "--aws_secret", default='aws-secret', type=str, help=("The namespace to use."))

  parser.add_argument(
    "--aws_access_key_id", default='AWS_ACCESS_KEY_ID', type=str, help=("The namespace to use."))

  parser.add_argument(
    "--aws_secret_access_key", default='AWS_SECRET_ACCESS_KEY', type=str, help=("The namespace to use."))

  parser.add_argument(
    "--aws_region", default='us-west-2', type=str, help=("The aws region to use."))

  parser.add_argument(
    "--data_pvc", default='null', type=str, help=("The dataset persistent volume claim"))

  args, _ = parser.parse_known_args()
  return args

def run_benchmark_job():
  """Submit benchmark jobs to remote kubernetes cluster."""
  args = parse_args()
  app_dir = os.path.join(str(os.environ['BENCHMARK_DIR']), "ks-app")

  kubeconfig_path = str(os.environ['KUBECONFIG'])
  api_client = deploy_utils.create_k8s_client(kubeconfig_path)

  namespace = args.namespace
  job_name = args.experiment_name

  # set the namespace of kb job to default
  namespace = "default"
  # Deploy Kubebench
  util.run(["ks", "generate", "kubebench-job", job_name, "--name=" + job_name], cwd=app_dir)
  job_config_prefix = "ks param set " + job_name + " "

  cmd = job_config_prefix + "mainJobKsRegistry " + args.training_job_registry
  util.run(cmd.split(), cwd=app_dir)
  cmd = job_config_prefix +  "mainJobKsPackage " + args.training_job_pkg
  util.run(cmd.split(), cwd=app_dir)
  cmd = job_config_prefix +  "mainJobKsPrototype " + args.training_job_prototype
  util.run(cmd.split(), cwd=app_dir)
  cmd = job_config_prefix +  "mainJobConfig " + args.training_job_config
  util.run(cmd.split(), cwd=app_dir)

  cmd = job_config_prefix + "awsCredentialsSecret " + args.aws_secret
  util.run(cmd.split(), cwd=app_dir)
  cmd = job_config_prefix + "awsCredentialsSecretAccessKeyId " + args.aws_access_key_id
  util.run(cmd.split(), cwd=app_dir)
  cmd = job_config_prefix + "awsCredentialsSecretAccessKey " + args.aws_secret_access_key
  util.run(cmd.split(), cwd=app_dir)
  cmd = job_config_prefix + "awsRegion " + args.aws_region
  util.run(cmd.split(), cwd=app_dir)

  cmd = job_config_prefix + "githubTokenSecret " + args.github_secret_name
  util.run(cmd.split(), cwd=app_dir)
  cmd = job_config_prefix +  "githubTokenSecretKey GITHUB_TOKEN"
  util.run(cmd.split(), cwd=app_dir)
  cmd = job_config_prefix +  "controllerImage seedjeffwan/configurator:20190415"
  util.run(cmd.split(), cwd=app_dir)
  cmd = job_config_prefix +  "postJobImage null"
  util.run(cmd.split(), cwd=app_dir)
  cmd = job_config_prefix +  "postJobArgs null"
  util.run(cmd.split(), cwd=app_dir)
  cmd = job_config_prefix +  "reporterType null"
  util.run(cmd.split(), cwd=app_dir)

  cmd = job_config_prefix +  "experimentDataPvc " + args.data_pvc
  util.run(cmd.split(), cwd=app_dir)

  # cmd = "ks param set " + job_name + " config_args -- --config-file=" + pvc_mount + \
  #         "/config/" + config_name + ".yaml"
  # util.run(cmd.split(), cwd=app_dir)
  # cmd = "ks param set " + job_name + " report_args -- --output-file=" + pvc_mount + \
  #         "/output/results.csv"
  # util.run(cmd.split(), cwd=app_dir)

  apply_command = ["ks", "apply", "default", "-c", job_name]
  util.run(apply_command, cwd=app_dir)

  # TODO: expose timeout setting here.
  deploy_utils.wait_for_benchmark_job(job_name, namespace)
  deploy_utils.cleanup_benchmark_job(app_dir, job_name)


if __name__ == "__main__":
  run_benchmark_job()
import os
import datetime
import logging
import time
import sys

from kubeflow.testing import util
from benchmark.test import deploy_utils

if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO,
                      format=('%(asctime)s %(name)-12s %(levelname)-8s %(message)s'),
                      datefmt='%Y-%m-%dT%H:%M:%S',
                      )
  logging.getLogger().setLevel(logging.INFO)

  benchmark_dir = str(os.environ['BENCHMARK_DIR'])
  cluster_manifest_path = os.path.join(benchmark_dir, "eksctl-cluster-config.yaml")

  logs = util.run(["eksctl", "delete", "cluster", "--config-file=" + cluster_manifest_path])
  logging.info("Successfully delete cluster")

  logs_dir = os.path.join(benchmark_dir, "logs")
  log_file = os.path.join(logs_dir, "delete_cluster.log")
  with open(log_file, "w") as text_file:
    text_file.write(logs)

  sys.exit(0)
import os
import datetime
import logging
import time
import sys

import kubeflow.testing import util

if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO,
                      format=('%(asctime)s %(name)-12s %(levelname)-8s %(message)s'),
                      datefmt='%Y-%m-%dT%H:%M:%S',
                      )
  logging.getLogger().setLevel(logging.INFO)

  benchmark_dir = str(os.environ['BENCHMARK_DIR'])
  cluster_manifest_path = os.path.join(benchmark_dir, "aws-k8s-tester-eks.yaml")

  logs = util.run(["aws-k8s-tester", "eks", "delete", "cluster", "--path", cluster_manifest_path])
  # logs = util.run(["aws-k8s-tester", "eks", "delete", "cluster", "-h"])
  logging.info("Successfully delete cluster")

  # Collect logs
  logs_dir = os.path.join(benchmark_dir, "output", "logs")
  log_file = os.path.join(logs_dir, "delete_cluster.log")
  with open(log_file, "w") as text_file:
    text_file.write(logs)
 
  sys.exit(0)
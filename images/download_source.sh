set -xe

SRC_DIR=$1

mkdir -p ${SRC_DIR}

BENCHMARK_SRC=${SRC_DIR}/jeffwan/ml-benchmark
KUBEFLOW_TEST_SRC=${SRC_DIR}/kubeflow/testing

if [ ! -d "$BENCHMARK_SRC"]; then
  git clone https://github.com/jeffwan/ml-benchmark.git $BENCHMARK_SRC
fi

if [ ! -d "$KUBEFLOW_TEST_SRC"]; then
  git clone https://github.com/kubeflow/testing.git $KUBEFLOW_TEST_SRC
fi
set -xe

SRC_DIR=$1

mkdir -p ${SRC_DIR}

git clone https://github.com/seedjeffwan/ml-benchmark.git ${SRC_DIR}/seedjeffwan/ml-benchmark
git clone https://github.com/kubeflow/testing.git ${SRC_DIR}/kubeflow/testing

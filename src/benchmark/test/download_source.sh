set -xe

SRC_DIR=$1

mkdir -p ${SRC_DIR}

git clone https://github.com/jeffwan/ml-benchmark.git ${SRC_DIR}/jeffwan/ml-benchmark
#cp -r /Users/shjiaxin/Github/ml-benchmark/ ${SRC_DIR}/jeffwan/ml-benchmark
git clone https://github.com/kubeflow/testing.git ${SRC_DIR}/kubeflow/testing

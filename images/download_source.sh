set -xe

SRC_DIR=$1
ACTIVE_BRANCH=$2

mkdir -p ${SRC_DIR}

BENCHMARK_SRC=${SRC_DIR}/aws-samples/aws-eks-deep-learning-benchmark
KUBEFLOW_TEST_SRC=${SRC_DIR}/kubeflow/testing

if [ ! -d "$BENCHMARK_SRC" ] ; then
    echo "Downloading Github Repository $BENCHMARK_SRC"
    git clone https://github.com/aws-samples/aws-eks-deep-learning-benchmark.git -b $ACTIVE_BRANCH $BENCHMARK_SRC
else
    echo "$BENCHMARK_SRC already exist"
fi

if [ ! -d "$KUBEFLOW_TEST_SRC" ] ; then
    echo "Downloading Github Repository $KUBEFLOW_TEST_SRC"
    git clone https://github.com/kubeflow/testing.git $KUBEFLOW_TEST_SRC
else
    echo "$KUBEFLOW_TEST_SRC already exist"
fi
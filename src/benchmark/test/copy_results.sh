
NAMESPACE=$1
S3_PATH=$2

NFS_POD_NAME=$(kubectl --kubeconfig=$BENCHMARK_DIR/kubeconfig get pods -l role=kubebench-nfs -o jsonpath="{.items[0].metadata.name}")

kubectl cp ${NAMESPACE}/${NFS_POD_NAME}:/exports/kubebench/experiments ${BENCHMARK_DIR}/experiments

BENCHMARK_ID=$(basename $BENCHMARK_DIR)
aws s3 cp ${BENCHMARK_DIR}/ ${S3_PATH}/${BENCHMARK_ID}/ --recursive --exclude "src/*"
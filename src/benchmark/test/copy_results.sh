#!/bin/bash
# This Bash Script is used to copy experiment datasets from training cluster to s3

NAMESPACE=$1
S3_PATH=${2%/}

# Copy experiment data from training cluster to operation cluster
NFS_POD_NAME=$(kubectl --kubeconfig=$BENCHMARK_DIR/kubeconfig get pods -l role=kubebench-nfs -o jsonpath="{.items[0].metadata.name}")
kubectl cp ${NAMESPACE}/${NFS_POD_NAME}:/exports/kubebench/experiments ${BENCHMARK_DIR}/experiments

# Copy all benchmark results to specified S3 location
BENCHMARK_ID=$(basename $BENCHMARK_DIR)
aws s3 cp ${BENCHMARK_DIR}/ ${S3_PATH}/${BENCHMARK_ID}/ --recursive --exclude "src/*"
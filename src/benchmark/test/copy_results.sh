
NAMESPACE=$1

NFS_POD_NAME=$(kubectl get pods -l role=kubebench-nfs -o jsonpath="{.items[0].metadata.name}")

kubectl cp ${NAMESPACE}/${NFS_POD_NAME}:/exports/kubebench/config ${BENCHMARK_DIR}/output/config
kubectl cp ${NAMESPACE}/${NFS_POD_NAME}:/exports/kubebench/experiments ${BENCHMARK_DIR}/output/experiments
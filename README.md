## Prerequisite to run benchmarks
To successfully run benchmark automatically, you need to install following resources in your kubernetes cluster.


### Setup NFS
Benchmark has many steps and it need files to sync status. We setup this NFS to store benchmark configuration, required source files and benchmark results. All files will be synced to S3 bucket after experiment done.

> Note: This is not a real NFS, it's actually a website frontend server to play as NFS. Please check [source](https://github.com/kubernetes/examples/tree/master/staging/volumes/nfs) for details.

```bash
kubectl create -f deploy/benchmark-nfs-svc.yaml
kubectl get svc benchmark-nfs-svc -o=jsonpath={.spec.clusterIP}

# Replace ip in the `deploy/benchmark-nfs-volume.yaml`
kubectl create -f deploy/benchmark-nfs-volume.yaml
```

### Install Argo workflow
Argo Workflows is an open source container-native workflow engine for orchestrating parallel jobs on Kubernetes. Benchmark experiment is an argo workflow and we use this to orchestrate our job and manage jobs.

```bash
kubectl create ns argo
kubectl apply -n argo -f https://raw.githubusercontent.com/argoproj/argo/v2.2.1/manifests/install.yaml

# you can forward port to localhost and look at Argo UI
kubectl port-forward -n argo svc/argo-ui 8080:80

```

### Setup AWS Credential
Replace `YOUR_AWS_ACCESS_KEY_ID` and `YOUR_AWS_SECRET_ACCESS_KEY` with your own aws credentials.
This account needs to have at least following permissions. It will be used in the experiment to create EKS cluster, setup data storage like EFS or FSx for Lustre, write to S3 buckets.

```bash
kubectl apply -f deploy/aws-secret.yaml
```

### Setup Github Token
Replace `YOUR_GITHUB_TOKEN` with your github token. Github token is used with ksonnet otherwise the experiment will quickly runs into GitHub API limits.

```bash
kubectl apply -f deploy/github-token.yaml
```

### Setup S3 buckets
Firstly, please create a bucket for benchmark results. `copy-result` step will sync results to bucket `s3ResultBucket` specified in your configuration.

If you like to use real storage for testing, Please create another S3 bucket and upload your training files there. Please set `s3DatasetBucket` and `storageBackend` in the configuration and workflow will automatically create backend storage like [Amazon Elastic File System](https://aws.amazon.com/efs/) or [Amazon FSx For Lustre](https://aws.amazon.com/fsx/lustre/) and sync files in `s3DatasetBucket` to the storage. During training, storage will be mounted as [Persistent Volume](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) to worker pods.


## Run benchmmark jobs

### How to configure your benchmark jobs

You have two ways to update your benchmark jobs.

### Update your workflow setting using `ks` command

```bash
ks param set workflows ami ami-095922d81242d0528
```

### Update benchmark workflow manifest directly
```
vim ks-app/components/params.libsonnet
```

Once you are done, you can run `ks show default -c workflows > workflow.yaml`. If your input is valid, you will see workflow.yaml in your folder.

This is an argo workflow and you can easily submit to your cluster by `kubectl apply -f workflow.yaml`.


//TODO: add a screenshot of benchmark job.


### Configurable fields

Worker Node:
- ami: 'ami-095922d81242d0528'
- region: 'us-west-2'
- az: 'us-west-2a'
- instanceType: 'p3.2xlarge'
- placementGroup: 'true'
- nodeCount: 1

Kubernetes:
- clusterVersion: '1.11'
- image: 'seedjeffwan/benchmark-runner:latest'
- namespace: 'default'

Training model:
- storageBackend: 'fsx' | 'efs'
- s3DatasetBucket: 'eks-dl-benchmark'
- experiments:
    - experiment: 'experiment-20190327-11',
    - trainingJobConfig: 'mpi/mpi-job-dummy.yaml',
    - trainingJobPkg: 'mpi-job',
    - trainingJobPrototype: 'mpi-job-custom',


Experiment:
- name: '20190329'
- s3ResultBucket: 'dl-benchmark-result'

### Benchmark Workflow
![benchmark-workflow](./benchmark-workflow.png)

## Contributing Guidance

### Test Python module locally
```
export PYTHONPATH=${YOUR_PATH_TO}/kubeflow/testing/py:{YOUR_PATH_TO}/aws-eks-deep-learning-benchmark/src

python -m benchmark.test.install_storage_backend --storage_backend=fsx --experiment_id=001 --s3_import_path=s3://eks-dl-benchmark
```
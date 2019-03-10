## Introduction

This repository contains scripts to train deep learning models optimized to run well on [Amazon Elastic Container Service for Kubernetes](https://aws.amazon.com/eks/). 


To simplify model building, we use ResNet50 from [deep-learning-models](https://github.com/aws-samples/deep-learning-models). Apart from it, process to setup a EKS cluster and file storage for deep learning is also included. 

## Benchmark Steps

### Prepare ImageNet Dataset

The ImageNet dataset is provided by http://www.image-net.org/ . You will need to register and download the following files from the original dataset: ILSVRC2012_img_train.tar.gz and ILSVRC2012_img_val.tar.gz. This contains the original 1.28M images among 1000 classes. Use the scripts provided in [utils](https://github.com/aws-samples/deep-learning-models/tree/master/utils/tensorflow) directory to process the ImageNet images to create TF Records for Tensorflow.

//TODO: is there a way to share S3 dataset to publicly? That will simplify user's setup

Create an S3 bucket and upload training and validation dataset to buckets like this. 

```
➜ aws s3 ls s3://dl-benchmark-dataset/imagenet/train/
2019-02-28 12:03:46   56755552 train-00001-of-01024
2019-02-28 12:03:45   56365180 train-00002-of-01024
......
2019-02-28 12:03:45   56365180 train-01024-of-01024


➜ aws s3 ls s3://dl-benchmark-dataset/imagenet/validation/
2019-02-28 12:14:10   19504012 validation-00001-of-00128
2019-02-28 12:14:10   19624967 validation-00002-of-00128
....
2019-02-28 12:14:10   20063161 validation-00128-of-00128

```

### Create EKS Cluster

To simplify provision process, use [eksctl](https://github.com/weaveworks/eksctl) to create your cluster.

```
eksctl create cluster --name=${CLUSTER_NAME} --nodes=1 --node-type=p3.16xlarge --ssh-access --region=us-west-2 --node-zones=us-west-2a --ssh-public-key ~/.ssh/id_rsa.pub
```

> Note: In order to get higher network performance between host, we put all the machines in one availability zone.

> Note: In you want to create machines within one [Placement Groups](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html) to leverage low-latency without any slowing, you can follow guidance here and manually add node groups using [CloudFormation Template](eks_cluster/amazon-eks-nodegroup-placementgroup.yaml) 

 `eksctl` doesn't support placement group option yet, it's tracked in this [issue](https://github.com/weaveworks/eksctl/issues/479)

### Install NIVIDA Device Plugin
The [NVIDIA device plugin](https://github.com/NVIDIA/k8s-device-plugin) for Kubernetes is a Daemonset that allows you to automatically 
- Expose the number of GPUs on each nodes of your cluster
- Keep track of the health of your GPUs
- Run GPU enabled containers in your Kubernetes cluster.

Enable GPU support in your cluster by deploying the following Daemonset:

```
➜ kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v1.11/nvidia-device-plugin.yml
```

### Create EFS and Lustre File Storage
You don't have to create both file system. Choose the one you will use. 
Please remember to use same `VPC` and `Subnet` as your EKS cluster Node Group. Otherwise, you won't succesfully mount storage.

*EFS*: Please follow [EFS User Guide](https://docs.aws.amazon.com/efs/latest/ug/gs-step-two-create-efs-resources.html) to create EFS. You also need to mount EFS to one of EC2 machines and download S3 dataset into it. 

*FSx for Lustre*: Please follow [FSx for Lustre User Guide](https://docs.aws.amazon.com/fsx/latest/LustreGuide/getting-started.html) to create FSx.  

Remember to integration with S3 and then you will get a Lustre File System backed by S3. No need to move data. 
![fsx-s3-integration](images/fsx-s3-integration.png)

There's another kubernetes way to dynamically provision FSx for Lustre. Please check [Dynamic Provisioning with data repository Example](https://github.com/aws/csi-driver-amazon-fsx/tree/master/examples/kubernetes/dynamic_provisioning_s3)

### Install MPI Operator
The [MPI Operator](https://github.com/kubeflow/mpi-operator) is a component of [Kubeflow](https://github.com/kubeflow/kubeflow) which makes it easy to run allreduce-style distributed training on Kubernetes.
In order to leverage this, `ksonnet` is required in your OS, please follow [ksonnet](https://github.com/ksonnet/ksonnet) to install command. 


```
➜ ks init /tmp/application && cd /tmp/application

# Add Registry
➜ ks registry add kubeflow github.com/kubeflow/kubeflow/tree/master/kubeflow

# Install packages
➜ ks pkg install kubeflow/common@master
➜ ks pkg install kubeflow/mpi-job@master

# Generate Manifests
➜ ks generate mpi-operator mpi-operator

# Deploy
➜ ks apply default -c mpi-operator
```

Now you can submit `MPIJob` to kubernetes. 

### Create CSI Plugin
Please follow [EFS instruction](eks_cluster/efs/README.md) and [FSx for Lustre instruction](eks_cluster/fsx/README.md).

Please confirm you get them ready. 

```
➜ kubectl get sc
NAME            PROVISIONER             AGE
efs-sc          efs.csi.aws.com         3d
fsx-sc          fsx.csi.aws.com         3d

➜ kubectl get pv
NAME                  CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS   CLAIM                          STORAGECLASS   REASON   AGE
efs-pv                60Gi       RWX            Recycle          Bound    default/efs-claim              efs-sc                  3d
fsx-pv                100Gi      RWX            Recycle          Bound    default/fsx-claim              fsx-sc                  1d

➜ kubectl get pvc
NAME                   STATUS   VOLUME                CAPACITY   ACCESS MODES   STORAGECLASS   AGE
efs-claim              Bound    efs-pv                60Gi       RWX            efs-sc         3d
fsx-claim              Bound    fsx-pv                100Gi      RWX            fsx-sc         1d
```

### Build Docker Images
Notice this container images includes nightly version Tensorflow which is compatible with CUDA 10. This also require your AMI install latest [NVIDIA Driver](https://www.nvidia.com/Download/index.aspx?lang=en-us). Please check [compatibility matrixs](https://docs.nvidia.com/deploy/cuda-compatibility/index.html#binary-compatibility) here to install correct version. Minimum Linux x86_64 Driver Version for CUDA 10.0 is 410.48.


Please replace `${repo}/${image}:${tag}` with your docker tags

```
docker build -t ${repo}/${image}:${tag} --build-arg python=3.5 .
```

If you want to save time building your image, you can use `seedjeffwan/tf-cnn-benchmark:cuda10-hd0.16.0-tf1.13.1-py3.5` directly.

### Submit Training Job

Verify configuration and submit training job.
```
kubectl create -f mpi-job-fsx.yaml
```


## FAQ
- *Can I use this to train other models?*  
  Currently, it only has job specs for training Resnet50 with Imagenet using Tensorflow. You can use any other models using this setting but plugin different model images.

- *Can I skip imagenet procressing?*  
  Yes. But you can only use synthetic data in this case. You don't need to create EFS or LustreFS. 

- *Why do you provide EFS and FSx for Lustre? Which one should I use?*  
  Both storage can be used in distributed training. If you consider performance, we recommend you to use Lustre.

## Questions
Please create a Github issue here if you have any suggestions or questions.

# Deep Learning Performance Optimizations

The following optimizations may help you improve the performance of your deep learning jobs running on Amazon EKS. You can follow these steps, then re-run the benchmark utility to see how they change your results.

This is an evolving list of optimizations put together by the Amazon EKS team. If you find an new optimization strategy or have improvement to an optimization below, please contribute!

#### 1\. Use the latest deep learning toolkits
GPU Optimized AMI for EKS comes with latest Nvidia Linux Driver 410.104. Because of this, we can build customized container image with CUDA 10.0, Tensorflow v1.13.1 and compatible cuDNN and NCCL. New versions deliver great performance improvements, and critical bug fixes. See Amazon Deep Learning Containers (https://aws.amazon.com/machine-learning/containers/) for more details.

#### 2\. Set the GPU clock speeds to their maximum frequency
By default, the NVIDIA driver varies the GPU clock speeds. By setting the GPU clock speeds to their maximum frequency, you can consistently achieve the maximum performance with your GPU instances. Check the bootstrap command in this CloudFormation Template. See Optimizing GPU Settings (https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/optimize_gpu.html) for more details.

#### 3\. Launch instances in a Placement Groups (https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html) to leverage low-latency without slowing

You can use this CloudFormation Template (https://github.com/aws-samples/aws-eks-deep-learning-benchmark/blob/master/blog-post-sample/eks_cluster/amazon-eks-nodegroup-placementgroup.yaml) to add new node groups with non-blocking, non-oversubscribed, fully bi-sectional nature of the connectivity.

#### 4\. Use the latest [AWS VPC CNI plugin](https://github.com/aws/amazon-vpc-cni-k8s) to get Jumbo Frame support
All NICs get jumbo frames by default on EKS clusters.

#### 5\. Choose the right storage backend
I/O performance is a key factor for overall performance. Preprocessing (CPU) and model execution of a training step (GPU) run in parallel. While the accelerator is performing training step N, the CPU is preparing the data for step N+1. If you notice your GPU utilization is not always >95%, one possibility is they are waiting for CPU's work to complete. In this case, there's room to improve.

The p3.16xlarge instance has 488GiB memory and your entire training dataset can fit into memory, which means after 1 epoch, your storage backend makes no performance difference. You can leverage local node memory in order to provide throughput and may be able to use a less performant backend.

#### 6\. Use static Kubernetes CPU Management policy to access exclusive CPUs
By default, all the pods and the containers running on a compute node in your Kubernetes cluster can execute on any available cores in the system.

With CPU manager static policy enabled, exclusive CPUs can be allocated for the workload container but not the other containers. In the training case, CPU part could be sensitive to context switches. Using a static policy can be helpful if multiple training jobs share same node.

#### 7\. Use right MPI processor affinity through process binding
Open MPI supports processor affinity on a variety of systems through process binding, in which each MPI process, along with its threads, is "bound" to a specific subset of processing resources (cores, sockets, etc.). The node's operating system will constrain the process to run on only that subset. Judicious bindings can improve performance by reducing resource contention (by spreading processes apart from one another) or improving interprocess communications (by placing processes close to one another).

Binding can also improve reproducibility by eliminating variable process placement. Based on our tests, using `--bind-to socket -map-by slot` is the most optimized option for p3.16xlarge instances.

#### 8\. Optimize CPU Performance by building Tensorflow with Intel®MKL DNN.
Intel® has added optimizations to TensorFlow for Intel® Xeon® and Intel® Xeon Phi™ through the use of the Intel® Math Kernel Library for Deep Neural Networks (Intel® MKL-DNN) optimized primitives. This optimizations can also provide speed improvements for Intel's consumer processors, e.g. i5 and i7 Intel processors.

#### 9\. Optimize Tensorflow parallelize data transformation process and parallelism threads.
The optimal value depends on the hardware and training data. A simple heuristic is to use the number of available CPU cores. This corresponding parameter is `num_parallel_calls`.

A p3.16xlarge instance has 64 vCPUs and one training worker uses 8 GPUs, so we calculate *64 / 8 = 8*. Based on the instance type you use, dividing available CPU cores by the number of GPUs will give you right number for setting the value.

#### 10\. Adjust the thread pools and tuning CPU performance
The corresponding parameters are `intra_op_parallelism_threads` and  `inter_op_parallelism_threads` . Normally, setting `intra_op_parallelism_threads` to the number of physical cores and setting `inter_op_parallelism_threads` to the number of sockets is recommended.

A p3.16xlarge instance has 2 sockets and 16 cores per socket. Since hyper-threading is used, every core has 2 threads. In total, this instance has 64 logical cpus and 32 physical cores. Based on our testing in GPU training, we have not seen a big difference adjusting these parameters. If you don't like to tune them, just assign 0 and system will automatically pick a proper value for you.

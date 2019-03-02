### Software Version
- CUDA_VERSION=10.0
- CUDNN_VERSION=7.4.2.24-1+cuda10.0
- NCCL_VERSION=2.4.2-1+cuda10.0
- TENSORFLOW_VERSION=1.13.1
- OPENMPI_VERSION=4.0.0

### Build Command
Please replace `${repo}/${image}:${tag}` with your docker tags

```
docker build -t ${repo}/${image}:${tag} --build-arg python=3.5 .
```

For users using CUDA 9.0 (compatible with Tensorflow V1.12), use different dockerfile 

```
docker build -t ${repo}/${image}:${tag} --build-arg python=3.5 -f Dockerfile-v1.12 .

```
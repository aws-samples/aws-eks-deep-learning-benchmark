### Software Version
- CUDA_VERSION=10.0
- CUDNN_VERSION=7.4.2.24-1+cuda10.0
- NCCL_VERSION=2.4.2-1+cuda10.0
- TENSORFLOW_VERSION=1.13.1
- OPENMPI_VERSION=4.0.0

### Use pre-built image
Building the docker image will take a few minutes. If you'd like to save some time and skip building your own image, we have one already built for you:

```
seedjeffwan/eks-dl-benchmark:cuda10-tf1.13.1-hvd0.16.0-py3.5
```

### Build your own image
Please replace `${repo}/${image}:${tag}` with your docker tags

For users who like to build from scratch (this dockerfile is different from AWS DL Container)
```
docker build -t ${repo}/${image}:${tag} --build-arg python=3.5 .
```

For users using AWS Deep Learning Container,
```
# You must login to access to the image repository before pulling the image.
$(aws ecr get-login --no-include-email --region us-east-1 --registry-ids 763104351884)

# Build your container image
docker build -t ${repo}/${image}:${tag} -f Dockerfile-aws-dl-container .
```

For users using CUDA 9.0 (compatible with Tensorflow V1.12), use different dockerfile
```
docker build -t ${repo}/${image}:${tag} --build-arg python=3.5 -f Dockerfile-v1.12 .
```


### Difference between Dockerfile
- `Dockerfile` uses distributed Tensorflow without AWS optimization
- `Dockerfiler-aws-dl-container` uses AWS optimized Tensorflow
- `Dockerfile-custom` build Tensorflow from source with MKL optimization
- `Dockerfiler-v1.12` use CUDA 9.0 with compatible Tensorflow v1.12

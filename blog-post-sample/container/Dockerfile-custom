FROM nvidia/cuda:10.0-devel-ubuntu16.04

# TensorFlow v1.13 is coupled to CUDA10.
ENV TENSORFLOW_VERSION=r1.13
ENV CUDNN_VERSION=7.4.2.24-1+cuda10.0
ENV NCCL_VERSION=2.4.2-1+cuda10.0
ENV BAZEL_VERSION=0.21.0

# Python 2.7 or 3.5 is supported by Ubuntu Xenial out of the box
ARG python=3.5
ENV PYTHON_VERSION=${python}

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        curl \
        vim \
        wget \
        pkg-config \
        zip \
        g++ \
        zlib1g-dev \
        unzip \
        ca-certificates \
        libcudnn7=${CUDNN_VERSION} \
        libcudnn7-dev=${CUDNN_VERSION} \
        libnccl2=${NCCL_VERSION} \
        libnccl-dev=${NCCL_VERSION} \
        libjpeg-dev \
        libpng-dev \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-dev

#RUN cp /usr/lib/x86_64-linux-gnu/libcudnn* /usr/local/cuda/lib64/ && \
#    find /usr/local/cuda-10.0/lib64/ -type f -name 'lib*_static.a' -not -name 'libcudart_static.a' -delete && \
#    rm /usr/lib/x86_64-linux-gnu/libcudnn_static_v7.a && \
#    rm /usr/local/cuda-10.0/targets/x86_64-linux/lib/libcudnn.so.7 && \
#    ln -sf /usr/local/cuda-10.0/targets/x86_64-linux/lib/libcudnn.so.7.4.2 /usr/local/cuda-10.0/targets/x86_64-linux/lib/libcudnn.so.7

RUN ln -s /usr/bin/python${PYTHON_VERSION} /usr/bin/python

RUN curl -O https://bootstrap.pypa.io/get-pip.py && \
    python get-pip.py && \
    rm get-pip.py

# Running bazel inside a `docker build` command causes trouble, cf:
#   https://github.com/bazelbuild/bazel/issues/134
# The easiest solution is to set up a bazelrc file forcing --batch.
RUN echo "startup --batch" >>/etc/bazel.bazelrc
RUN echo "build --spawn_strategy=standalone --genrule_strategy=standalone" >>/etc/bazel.bazelrc

# Install bazel, bazel depends on pkg-config zip g++ zlib1g-dev unzip
RUN wget "https://github.com/bazelbuild/bazel/releases/download/${BAZEL_VERSION}/bazel-${BAZEL_VERSION}-installer-linux-x86_64.sh" && \
    chmod +x bazel-*.sh && \
    ./bazel-${BAZEL_VERSION}-installer-linux-x86_64.sh && \
    rm bazel-${BAZEL_VERSION}-installer-linux-x86_64.sh

# Install the TensorFlow pip package dependencies 
RUN pip install six numpy wheel mock h5py
RUN pip install keras_applications==1.0.6 --no-deps 
RUN pip install keras_preprocessing==1.0.5 --no-deps
RUN git clone --branch ${TENSORFLOW_VERSION} --depth=1 https://github.com/tensorflow/tensorflow.git /root/tensorflow

WORKDIR "/root/tensorflow"

# Configure the Tensorflow build
#https://github.com/tensorflow/tensorflow/issues/26001 config for python
ENV CI_BUILD_PYTHON=python \
    LD_LIBRARY_PATH=/usr/local/cuda/extras/CUPTI/lib64:$LD_LIBRARY_PATH \
    TF_NEED_CUDA=1 \
    TF_NEED_MKL=1 \
    TF_DOWNLOAD_MKL=1 \
    TF_ENABLE_XLA=0 \
    CUDA_TOOLKIT_PATH=/usr/local/cuda \
    CUDNN_INSTALL_PATH=/usr/lib/x86_64-linux-gnu \
    NCCL_INSTALL_PATH=/usr/lib/x86_64-linux-gnu \
    NCCL_HDR_PATH=/usr/include \
    TF_CUDA_VERSION=10.0 \
    TF_CUDNN_VERSION=7 \
    TF_NCCL_VERSION=2.4.2 \
    TF_CUDA_COMPUTE_CAPABILITIES=5.2,6.0,6.1,7.0

#RUN sed -i '/toco/s/^/#/' /root/tensorflow/tensorflow/tools/pip_package/BUILD
#RUN sed -i '/toco/s/^/#/' /root/tensorflow/tensorflow/tools/pip_package/build_pip_package.sh

# ldconfig /usr/local/cuda/targets/x86_64-linux/lib/stubs && \
#https://github.com/tensorflow/tensorflow/issues/10289
RUN ln -s /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1 && \  
    LD_LIBRARY_PATH=/usr/local/cuda/lib64/stubs/:${LD_LIBRARY_PATH} \
    tensorflow/tools/ci_build/builds/configured GPU \
    bazel build -j 30 -c opt \
    --config=cuda \
    --config=mkl \
    --cxxopt="-D_GLIBCXX_USE_CXX11_ABI=0" \
    --action_env LD_LIBRARY_PATH="${LD_LIBRARY_PATH}" \
    --verbose_failures \
    //tensorflow/tools/pip_package:build_pip_package

RUN bazel-bin/tensorflow/tools/pip_package/build_pip_package /tmp/pip
RUN pip install --upgrade /tmp/pip/tensorflow-*.whl

# Install Open MPI 4.0.0
RUN mkdir /tmp/openmpi && \
    cd /tmp/openmpi && \
    wget https://download.open-mpi.org/release/open-mpi/v4.0/openmpi-4.0.0.tar.gz && \
    tar zxf openmpi-4.0.0.tar.gz && \
    cd openmpi-4.0.0 && \
    ./configure --enable-orterun-prefix-by-default && \
    make -j $(nproc) all && \
    make install && \
    ldconfig && \
    rm -rf /tmp/openmpi

# Create a wrapper for OpenMPI to allow running as root by default
RUN mv /usr/local/bin/mpirun /usr/local/bin/mpirun.real && \
    echo '#!/bin/bash' > /usr/local/bin/mpirun && \
    echo 'mpirun.real --allow-run-as-root "$@"' >> /usr/local/bin/mpirun && \
    chmod a+x /usr/local/bin/mpirun

# Configure OpenMPI to run good defaults:
#   --bind-to none --map-by slot --mca btl_tcp_if_exclude lo,docker0
RUN echo "hwloc_base_binding_policy = socket" >> /usr/local/etc/openmpi-mca-params.conf && \
    echo "rmaps_base_mapping_policy = slot" >> /usr/local/etc/openmpi-mca-params.conf && \
    echo "btl_tcp_if_exclude = lo,docker0" >> /usr/local/etc/openmpi-mca-params.conf

# Install Horovod, temporarily using CUDA stubs, /usr/local/cuda links to /usr/local/cuda-10.0
# cd to root to avoid `sh: 0: getcwd() failed: No such file or directory` from last step
# Move Horovod Installation after OpenMPI to avoid failure `error: mpicxx -show failed (see error below), is MPI in $PATH?`
# https://github.com/horovod/horovod/issues/137 https://github.com/horovod/horovod/blob/master/docs/troubleshooting.md
RUN cd ~/ && \
    ldconfig /usr/local/cuda/targets/x86_64-linux/lib/stubs && \
    HOROVOD_GPU_ALLREDUCE=NCCL HOROVOD_WITH_TENSORFLOW=1 pip install --no-cache-dir horovod && \
    ldconfig

# Set default NCCL parameters
RUN echo NCCL_DEBUG=INFO >> /etc/nccl.conf

# Install OpenSSH for MPI to communicate between containers
RUN apt-get install -y --no-install-recommends openssh-client openssh-server && \
    mkdir -p /var/run/sshd

# Allow OpenSSH to talk to containers without asking for confirmation
RUN cat /etc/ssh/ssh_config | grep -v StrictHostKeyChecking > /etc/ssh/ssh_config.new && \
    echo "    StrictHostKeyChecking no" >> /etc/ssh/ssh_config.new && \
    mv /etc/ssh/ssh_config.new /etc/ssh/ssh_config

# My repo fix an issue on benchmark master which was not v1.13 compatible
RUN mkdir /code && git clone https://github.com/aws-samples/deep-learning-models.git /code

WORKDIR "/code"

CMD mpirun \
  python models/resnet/tensorflow/train_imagenet_resnet_hvd.py \
    --batch_size=256 \
    --model=resnet50 \
    --num_batches=1000 \
    --fp16 \
    --lr_decay_mode=poly \
    --synthetic
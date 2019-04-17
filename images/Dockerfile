FROM golang:1.12-rc


ARG GOPATH=/go

# Install required softwares
RUN apt-get update && apt-get install -y python-pip python-dev

# Install eksctl
ENV HOME=/root
RUN curl --silent --location "https://github.com/weaveworks/eksctl/releases/download/latest_release/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp && \
    mv /tmp/eksctl /usr/local/bin

# Install aws-iam-authenticator
RUN curl -o aws-iam-authenticator https://amazon-eks.s3-us-west-2.amazonaws.com/1.11.5/2018-12-06/bin/linux/amd64/aws-iam-authenticator && \
    chmod +x ./aws-iam-authenticator && \
    cp ./aws-iam-authenticator /usr/local/bin/ && export PATH=/user/local/bin:$PATH

# Install jsonnet
RUN cd /tmp && \
    wget -O ks.tar.gz \
    https://github.com/ksonnet/ksonnet/releases/download/v0.13.1/ks_0.13.1_linux_amd64.tar.gz && \
    tar -xvf ks.tar.gz && \
    mv ks_0.13.1_linux_amd64/ks /usr/local/bin && \
    chmod a+x /usr/local/bin/ks

# Install kubectl
RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/v1.11.0/bin/linux/amd64/kubectl && \
    mv kubectl /usr/local/bin && \
    chmod a+x /usr/local/bin/kubectl

# Use Python 2.7 by default. TODO: upgrade to 3.6 later
RUN pip install kubernetes \
                request \
                pyyaml \
                boto3 \
                awscli \
                google-api-python-client \
                google-cloud-storage \
                prometheus_client


# Copy utilities
COPY images/download_source.sh /usr/local/bin
COPY images/ /tmp/

# docker build -t ${REGISTRY}/${REPO}:${TAG} -f images/Dockerfile .
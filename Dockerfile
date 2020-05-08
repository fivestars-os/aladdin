### BUILD build-components command ############################################
FROM python:3.8-slim as build-components-builder

# Install packages required to build native library components
RUN apt-get update \
 && apt-get -y --no-install-recommends install \
    gettext \
    gcc \
    g++ \
    make \
    libc6-dev
# We intenionally do not clear the lists here, since the builder layers are not added to
# resulting image.

# Upgrade pip
RUN pip install --upgrade pip

# Install poetry under the root user's home directory
ARG POETRY_VERSION=1.0.5
ADD https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py /tmp/get-poetry.py
RUN python /tmp/get-poetry.py --version $POETRY_VERSION \
 && chmod a+rx /root/.poetry/bin/poetry

# Move to build directory before copying items to non-fixed location
WORKDIR /build

# Build the build-components package to give us the build-components command
COPY build .
RUN  . /root/.poetry/env \
 && cd build-components \
 && poetry build




FROM golang:1.14-buster

RUN apk add --no-cache \
    bash \
    bash-completion \
    bats \
    coreutils \
    curl \
    git \
    groff \
    jq \
    less \
    openssh-client \
    python3 \
    ncurses \
    vim

RUN go get -u -v sigs.k8s.io/aws-iam-authenticator/cmd/aws-iam-authenticator

# Update all needed tool versions here
ARG KUBE_VERSION=1.15.6
ARG KOPS_VERSION=1.15.0
ARG HELM_VERSION=2.16.1
ARG DOCKER_VERSION=18.09.7

RUN	curl -L -o /bin/kubectl https://storage.googleapis.com/kubernetes-release/release/v$KUBE_VERSION/bin/linux/amd64/kubectl \
	&& chmod 755 /bin/kubectl

RUN	curl -L -o /bin/kops https://github.com/kubernetes/kops/releases/download/$KOPS_VERSION/kops-linux-amd64 \
	&& chmod 755 /bin/kops

RUN	curl -L -o- https://storage.googleapis.com/kubernetes-helm/helm-v$HELM_VERSION-linux-amd64.tar.gz | tar -zxvf - && cp linux-amd64/helm \
	/bin/helm && chmod 755 /bin/helm && helm init --client-only

RUN curl -L -o- https://download.docker.com/linux/static/stable/x86_64/docker-$DOCKER_VERSION.tgz | tar -zxvf - && cp docker/docker \
    /usr/bin/docker && chmod 755 /usr/bin/docker

RUN go get -u -v sigs.k8s.io/aws-iam-authenticator/cmd/aws-iam-authenticator

WORKDIR /root/aladdin

# Get the build-components package and other python dependencies
COPY --from="build-components-builder" /build/build-components/dist/build-components-0.1.0.tar.gz build-components-0.1.0.tar.gz

COPY commands/python/requirements.txt commands/python/requirements.txt
RUN pip install --no-cache-dir -r commands/python/requirements.txt

ENV PATH="/root/.local/bin:/root:${PATH}"
COPY . /root/aladdin

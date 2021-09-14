FROM python:3.8.12-buster as build

WORKDIR /root/aladdin

RUN python -m venv /root/.venv
ENV PATH /root/.venv/bin:$PATH

# On some images "sh" is aliased to "dash" which does not support "set -o pipefail".
# We use the "exec" form of RUN to delegate this command to bash instead.
# This is all because we have a pipe in this command and we wish to fail the build
# if any command in the pipeline fails.
ARG POETRY_VERSION=1.1.5
RUN ["/bin/bash", "-c", "set -o pipefail && curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python"]
ENV PATH /root/.poetry/bin:$PATH

ARG POETRY_VIRTUALENVS_CREATE="false"
# Install aladdin python requirements
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

FROM python:3.8.12-slim-buster

# Remove the default $PS1 manipulation
RUN rm /etc/bash.bashrc

RUN apt-get update && \
    apt-get -y --no-install-recommends install \
    bash-completion \
    bats \
    git \
    groff \
    jq \
    less \
    openssl \
    vim-nox \
    curl \
    ssh

RUN pip install --no-cache-dir pip==20.2.3

# Update all needed tool versions here

ARG AWS_IAM_AUTHENTICATOR_VERSION=1.21.2
RUN curl -o /usr/local/bin/aws-iam-authenticator https://amazon-eks.s3.us-west-2.amazonaws.com/$AWS_IAM_AUTHENTICATOR_VERSION/2020-08-04/bin/linux/$(dpkg --print-architecture)/aws-iam-authenticator && \
    chmod 755 /usr/local/bin/aws-iam-authenticator

ARG DOCKER_VERSION=20.10.2
RUN curl -L -o- https://download.docker.com/linux/static/stable/x86_64/docker-$DOCKER_VERSION.tgz | tar -zxvf - && \
    cp docker/docker /usr/local/bin/docker && \
    chmod 755 /usr/local/bin/docker

ARG KUBE_VERSION=1.19.7
RUN curl -L -o /usr/local/bin/kubectl https://storage.googleapis.com/kubernetes-release/release/v$KUBE_VERSION/bin/linux/$(dpkg --print-architecture)/kubectl && \
    chmod 755 /usr/local/bin/kubectl

ARG HELM_VERSION=3.6.3
RUN curl -fsSL https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 -o get-helm-3.sh && \
    chmod 700 get-helm-3.sh && \
    ./get-helm-3.sh --version v${HELM_VERSION}

ARG KOPS_VERSION=1.19.1
RUN curl -Lo kops https://github.com/kubernetes/kops/releases/download/v$KOPS_VERSION/kops-linux-$(dpkg --print-architecture) && \
    chmod +x ./kops && \
    mv ./kops /usr/local/bin/

ARG ISTIO_VERSION=1.9.2
RUN curl -L https://istio.io/downloadIstio | ISTIO_VERSION="$ISTIO_VERSION" sh - && \
    mv /istio-$ISTIO_VERSION/bin/istioctl /usr/local/bin/istioctl

ARG K3D_VERSION=4.4.8
RUN curl -s https://raw.githubusercontent.com/rancher/k3d/main/install.sh | TAG=v$K3D_VERSION bash

WORKDIR /root/aladdin

COPY --from=build /root/.poetry /root/.poetry
COPY --from=build /root/.venv /root/.venv
ENV PATH /root/.venv/bin:/root/.poetry/bin:$PATH
# Install aladdin
COPY . .
ARG POETRY_VIRTUALENVS_CREATE="false"
RUN poetry install

FROM python:3.8.12-buster as build

WORKDIR /root/aladdin

RUN apt-get update && \
    apt-get -y --no-install-recommends install \
    gettext \
    gcc \
    g++ \
    curl

RUN python -m venv /root/.venv
ENV PATH /root/.venv/bin:$PATH

ARG POETRY_VERSION=1.1.10
ENV PATH /root/.local/bin:$PATH
RUN pip install --upgrade pip && \
    curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py -o install-poetry.py && \
    python install-poetry.py --version $POETRY_VERSION
ENV POETRY_VIRTUALENVS_CREATE="false"
ENV POETRY_INSTALLER_PARALLEL="false"
# Poetry needs this to find the venv we created
ENV VIRTUAL_ENV=/root/.venv
# Install aladdin python requirements
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-dev

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

RUN pip install --no-cache-dir pip==21.2.4

# Update all needed tool versions here

ARG AWS_IAM_AUTHENTICATOR_VERSION=1.21.2
RUN curl -o /usr/local/bin/aws-iam-authenticator https://amazon-eks.s3.us-west-2.amazonaws.com/$AWS_IAM_AUTHENTICATOR_VERSION/2021-07-05/bin/linux/$(dpkg --print-architecture)/aws-iam-authenticator && \
    chmod 755 /usr/local/bin/aws-iam-authenticator

ARG DOCKER_VERSION=20.10.2
RUN curl -L -o- https://download.docker.com/linux/static/stable/x86_64/docker-$DOCKER_VERSION.tgz | tar -zxvf - && \
    cp docker/docker /usr/local/bin/docker && \
    chmod 755 /usr/local/bin/docker

ARG DOCKER_COMPOSE_VERSION=1.29.2
RUN curl -L "https://github.com/docker/compose/releases/download/$DOCKER_COMPOSE_VERSION/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
    chmod 755 /usr/local/bin/docker-compose

ARG KUBE_VERSION=1.19.7
RUN curl -L -o /usr/local/bin/kubectl https://storage.googleapis.com/kubernetes-release/release/v$KUBE_VERSION/bin/linux/$(dpkg --print-architecture)/kubectl && \
    chmod 755 /usr/local/bin/kubectl

ARG HELM_VERSION=3.5.2
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

COPY --from=build /root/.local /root/.local
COPY --from=build /root/.venv /root/.venv
ENV PATH /root/.venv/bin:/root/.local/bin:$PATH
# Install aladdin
COPY . .
ENV POETRY_VIRTUALENVS_CREATE="false"
# Poetry needs this to find the venv we created
ENV VIRTUAL_ENV=/root/.venv
RUN poetry install --no-dev

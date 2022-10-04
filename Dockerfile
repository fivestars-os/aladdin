FROM python:3.10.4-bullseye as build

WORKDIR /root/aladdin

RUN apt-get update && \
    apt-get -y --no-install-recommends install \
    gettext \
    gcc \
    g++ \
    curl

RUN python -m venv /root/.venv

ENV PATH /root/.venv/bin:$PATH
# also specified around line 48
ARG POETRY_VERSION=1.2.1
ENV PATH /root/.local/bin:$PATH
RUN pip install --upgrade pip setuptools wheel && \
    curl -sSL https://install.python-poetry.org -o install-poetry.py && \
    python install-poetry.py --version $POETRY_VERSION
ARG POETRY_VIRTUALENVS_CREATE="false"
ARG POETRY_INSTALLER_PARALLEL="false"
# Poetry needs this to find the venv we created
ARG VIRTUAL_ENV=/root/.venv
# Install aladdin python requirements
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-dev

FROM python:3.10.4-slim-bullseye

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
    ssh \
    unzip \
    wget

# also specified around line 15
ARG POETRY_VERSION=1.2.1
ENV PATH /root/.local/bin:$PATH
RUN pip install --upgrade pip setuptools wheel && \
    curl -sSL https://install.python-poetry.org -o install-poetry.py && \
    python install-poetry.py --version $POETRY_VERSION

# Update all needed tool versions here

ARG AWS_CLI_VERSION=2.7.24
RUN curl https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m)-$AWS_CLI_VERSION.zip -o awscliv2.zip && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf aws && rm awscliv2.zip

ARG AWS_IAM_AUTHENTICATOR_VERSION=0.5.9
RUN curl -L \
        "https://github.com/kubernetes-sigs/aws-iam-authenticator/releases/download/v$AWS_IAM_AUTHENTICATOR_VERSION/aws-iam-authenticator_${AWS_IAM_AUTHENTICATOR_VERSION}_$(uname -s)_$(dpkg --print-architecture)" \
        -o /usr/local/bin/aws-iam-authenticator && \
    chmod 755 /usr/local/bin/aws-iam-authenticator

ARG DOCKER_VERSION=20.10.18
RUN curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && \
    VERSION=$DOCKER_VERSION sh /tmp/get-docker.sh

ARG DOCKER_COMPOSE_VERSION=1.29.2
RUN curl -L "https://github.com/docker/compose/releases/download/$DOCKER_COMPOSE_VERSION/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
    chmod 755 /usr/local/bin/docker-compose

ARG DOCKER_COMPOSE_2_VERSION=v2.11.0
RUN curl -L "https://github.com/docker/compose/releases/download/$DOCKER_COMPOSE_2_VERSION/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose-2 && \
    chmod 755 /usr/local/bin/docker-compose-2

ARG KUBE_VERSION=1.23.10
RUN curl -L -o /usr/local/bin/kubectl https://storage.googleapis.com/kubernetes-release/release/v$KUBE_VERSION/bin/linux/$(dpkg --print-architecture)/kubectl && \
    chmod 755 /usr/local/bin/kubectl

ARG HELM_VERSION=3.9.4
RUN curl -fsSL https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 -o get-helm-3.sh && \
    chmod 700 get-helm-3.sh && \
    ./get-helm-3.sh --version v${HELM_VERSION}

ARG KOPS_VERSION=1.23.4
RUN curl -Lo kops https://github.com/kubernetes/kops/releases/download/v$KOPS_VERSION/kops-linux-$(dpkg --print-architecture) && \
    chmod +x ./kops && \
    mv ./kops /usr/local/bin/

ARG ISTIO_VERSION=1.13.7
RUN curl -L https://istio.io/downloadIstio | ISTIO_VERSION="$ISTIO_VERSION" sh - && \
    mv /istio-$ISTIO_VERSION/bin/istioctl /usr/local/bin/istioctl

ARG K3D_VERSION=4.4.8
RUN curl -s https://raw.githubusercontent.com/rancher/k3d/main/install.sh | TAG=v$K3D_VERSION bash

RUN curl -fsSL https://raw.githubusercontent.com/ahmetb/kubectl-aliases/master/.kubectl_aliases -o /etc/profile.d/kubectl_aliases.sh && \
    chmod +x /etc/profile.d/kubectl_aliases.sh

WORKDIR /root/aladdin

COPY --from=build /root/.venv /root/.venv
ENV PATH /root/.venv/bin:$PATH
# Install aladdin
COPY . .
ARG POETRY_VIRTUALENVS_CREATE="false"
ARG POETRY_INSTALLER_PARALLEL="false"
# Poetry needs this to find the venv we created
ARG VIRTUAL_ENV=/root/.venv
RUN poetry install --no-dev

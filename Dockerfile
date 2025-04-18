FROM python:3.10.16-bookworm as build

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
ARG POETRY_VERSION=1.8.2
ENV PATH /root/.local/bin:$PATH
RUN pip install --upgrade pip setuptools wheel && \
    curl -sSL https://install.python-poetry.org -o install-poetry.py && \
    python install-poetry.py --version $POETRY_VERSION
ARG POETRY_VIRTUALENVS_CREATE="false"
# Poetry needs this to find the venv we created
ARG VIRTUAL_ENV=/root/.venv
# Install aladdin python requirements
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

FROM python:3.10.16-slim-bookworm

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
ARG POETRY_VERSION=1.8.2
ENV PATH /root/.local/bin:$PATH
RUN pip install --upgrade pip setuptools wheel && \
    curl -sSL https://install.python-poetry.org -o install-poetry.py && \
    python install-poetry.py --version $POETRY_VERSION

# Update all needed tool versions here

ARG AWS_CLI_VERSION=2.8.11
RUN curl https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m)-$AWS_CLI_VERSION.zip -o awscliv2.zip && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf aws && rm awscliv2.zip

ARG AWS_IAM_AUTHENTICATOR_VERSION=0.5.21
RUN curl -L \
        "https://github.com/kubernetes-sigs/aws-iam-authenticator/releases/download/v$AWS_IAM_AUTHENTICATOR_VERSION/aws-iam-authenticator_${AWS_IAM_AUTHENTICATOR_VERSION}_$(uname -s)_$(dpkg --print-architecture)" \
        -o /usr/local/bin/aws-iam-authenticator && \
    chmod 755 /usr/local/bin/aws-iam-authenticator

ARG DOCKER_VERSION=27.3.1
RUN curl -fsSL https://get.docker.com | bash -s -- --version ${DOCKER_VERSION}

ARG DOCKER_COMPOSE_2_VERSION=v2.32.4
RUN curl -L "https://github.com/docker/compose/releases/download/$DOCKER_COMPOSE_2_VERSION/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
    chmod 755 /usr/local/bin/docker-compose

ARG GITHUB_CLI_VERSION=2.57.0
RUN curl -Ls "https://github.com/cli/cli/releases/download/v$GITHUB_CLI_VERSION/gh_${GITHUB_CLI_VERSION}_linux_$(dpkg --print-architecture).tar.gz" -o github_cli.tar.gz && \
    tar -xzf github_cli.tar.gz && \
    chmod +x ./gh_${GITHUB_CLI_VERSION}_linux_$(dpkg --print-architecture)/bin/gh && \
    mv ./gh_${GITHUB_CLI_VERSION}_linux_$(dpkg --print-architecture)/bin/gh /usr/local/bin/ && \
    rm -rf github_cli.tar.gz && rm -rf gh_${GITHUB_CLI_VERSION}_linux_$(dpkg --print-architecture) && \
    gh version

ARG KUBE_VERSION=1.30.10
RUN curl -fL -o /usr/local/bin/kubectl https://dl.k8s.io/release/v$KUBE_VERSION/bin/linux/$(dpkg --print-architecture)/kubectl && \
    chmod 755 /usr/local/bin/kubectl

ARG HELM_VERSION=3.17.2
RUN curl -fsSL https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 -o get-helm-3.sh && \
    chmod 700 get-helm-3.sh && \
    ./get-helm-3.sh --version v${HELM_VERSION}

ARG KOPS_VERSION=1.30.4
RUN curl -fLo kops https://github.com/kubernetes/kops/releases/download/v$KOPS_VERSION/kops-linux-$(dpkg --print-architecture) && \
    chmod +x ./kops && \
    mv ./kops /usr/local/bin/

ARG ISTIO_VERSION=1.20.8
RUN curl -fL https://istio.io/downloadIstio | ISTIO_VERSION="$ISTIO_VERSION" sh - && \
    mv /istio-$ISTIO_VERSION/bin/istioctl /usr/local/bin/istioctl

RUN curl -fsSL https://raw.githubusercontent.com/ahmetb/kubectl-aliases/master/.kubectl_aliases -o /etc/profile.d/kubectl_aliases.sh && \
    chmod +x /etc/profile.d/kubectl_aliases.sh

WORKDIR /root/aladdin

COPY --from=build /root/.venv /root/.venv
ENV PATH /root/.venv/bin:$PATH
# Install aladdin
COPY . .
ARG POETRY_VIRTUALENVS_CREATE="false"
# Poetry needs this to find the venv we created
ARG VIRTUAL_ENV=/root/.venv
RUN poetry install --only main

ENV ALADDIN_CONTAINER=1

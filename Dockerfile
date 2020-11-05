FROM python:3.8.5-buster as build

WORKDIR /root/aladdin

RUN python -m venv /root/.venv
ENV PATH /root/.venv/bin:$PATH

# On some images "sh" is aliased to "dash" which does not support "set -o pipefail".
# We use the "exec" form of RUN to delegate this command to bash instead.
# This is all because we have a pipe in this command and we wish to fail the build
# if any command in the pipeline fails.
ARG POETRY_VERSION=1.0.10
RUN ["/bin/bash", "-c", "set -o pipefail && curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python"]
ENV PATH /root/.poetry/bin:$PATH

ARG POETRY_VIRTUALENVS_CREATE="false"
# Install aladdin python requirements
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

FROM python:3.8.5-slim-buster

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
    curl

RUN pip install --no-cache-dir pip==20.2.3

ARG AWS_IAM_AUTHENTICATOR_VERSION=1.17.9
RUN curl -o /usr/local/bin/aws-iam-authenticator https://amazon-eks.s3.us-west-2.amazonaws.com/$AWS_IAM_AUTHENTICATOR_VERSION/2020-08-04/bin/linux/amd64/aws-iam-authenticator && \
    chmod 755 /usr/local/bin/aws-iam-authenticator

# Update all needed tool versions here

ARG DOCKER_VERSION=18.09.7
RUN curl -L -o- https://download.docker.com/linux/static/stable/x86_64/docker-$DOCKER_VERSION.tgz | tar -zxvf - && \
    cp docker/docker /usr/local/bin/docker && \
    chmod 755 /usr/local/bin/docker

ARG KUBE_VERSION=1.15.6
RUN curl -L -o /usr/local/bin/kubectl https://storage.googleapis.com/kubernetes-release/release/v$KUBE_VERSION/bin/linux/amd64/kubectl && \
    chmod 755 /usr/local/bin/kubectl

ARG HELM_VERSION=3.3.4
RUN curl -L -o- https://get.helm.sh/helm-v$HELM_VERSION-linux-amd64.tar.gz | tar -zxvf - && \
    cp linux-amd64/helm /usr/local/bin/helm && \
    chmod 755 /usr/local/bin/helm

ARG KOPS_VERSION=1.15.0
RUN curl -L -o /usr/local/bin/kops https://github.com/kubernetes/kops/releases/download/$KOPS_VERSION/kops-linux-amd64 && \
    chmod 755 /usr/local/bin/kops

ARG ISTIO_VERSION=1.6.2
RUN curl -L https://istio.io/downloadIstio | ISTIO_VERSION="$ISTIO_VERSION" sh - && \
    mv /istio-$ISTIO_VERSION/bin/istioctl /usr/local/bin/istioctl

# Install edgectl
RUN curl -fL https://metriton.datawire.io/downloads/linux/edgectl -o /usr/local/bin/edgectl && \
    chmod a+x /usr/local/bin/edgectl

# Add datawire helm repo
RUN helm repo add datawire https://www.getambassador.io

WORKDIR /root/aladdin

COPY --from=build /root/.poetry /root/.poetry
COPY --from=build /root/.venv /root/.venv
ENV PATH /root/.venv/bin:/root/.poetry/bin:$PATH
# Install aladdin
COPY . .
ARG POETRY_VIRTUALENVS_CREATE="false"
RUN poetry install && rm -rf aladdin.egg-info

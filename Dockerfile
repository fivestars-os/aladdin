FROM golang:1.14-buster

RUN apt-get update \
 && apt-get -y --no-install-recommends install \
    bash-completion \
    bats \
    gettext \
    groff \
    jq \
    less \
    python3 \
    python3-pip
# ncurses-bin or libncurses6 ?

RUN ln -fs /usr/bin/python3 /usr/bin/python \
 && ln -fs /usr/bin/pip3 /usr/bin/pip

# This can take a bit of time, so we move it earlier in the build process
RUN go get -u -v sigs.k8s.io/aws-iam-authenticator/cmd/aws-iam-authenticator

# Install poetry under the root user's home directory
ARG POETRY_VERSION=1.0.5
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
ENV PATH="/root/.poetry/bin:${PATH}"
COPY poetry.toml /root/.config/pypoetry/config.toml

# Update all needed tool versions here
ARG DOCKER_VERSION=18.09.7
ARG KUBE_VERSION=1.15.6
ARG HELM_VERSION=2.16.1
ARG KOPS_VERSION=1.15.0

RUN curl -L -o- https://download.docker.com/linux/static/stable/x86_64/docker-$DOCKER_VERSION.tgz | tar -zxvf - && cp docker/docker \
    /usr/bin/docker && chmod 755 /usr/bin/docker

RUN	curl -L -o /bin/kubectl https://storage.googleapis.com/kubernetes-release/release/v$KUBE_VERSION/bin/linux/amd64/kubectl \
	&& chmod 755 /bin/kubectl

RUN	curl -L -o- https://storage.googleapis.com/kubernetes-helm/helm-v$HELM_VERSION-linux-amd64.tar.gz | tar -zxvf - && cp linux-amd64/helm \
	/bin/helm && chmod 755 /bin/helm && helm init --client-only

RUN	curl -L -o /bin/kops https://github.com/kubernetes/kops/releases/download/$KOPS_VERSION/kops-linux-amd64 \
	&& chmod 755 /bin/kops

WORKDIR /root/aladdin

COPY commands/python/requirements.txt commands/python/requirements.txt
RUN pip install --no-cache-dir setuptools==46.4.0 \
 && pip install --no-cache-dir -r commands/python/requirements.txt

COPY build build
RUN cd build/build-components \
 && . ~/.poetry/env \
 && poetry install

COPY . /root/aladdin
ENV PATH="/root/.local/bin:/root:${PATH}"

RUN rm /etc/bash.bashrc











RUN curl -fL https://metriton.datawire.io/downloads/linux/edgectl -o /usr/bin/edgectl \
 && chmod 755 /usr/bin/edgectl

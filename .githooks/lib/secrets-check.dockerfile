FROM python:3.8-slim

RUN apt-get update \
 && apt-get -y --no-install-recommends install \
    build-essential \
    git \
 && rm -rf /var/lib/apt/lists/*

# Install trufflehog
RUN pip install --no-cache-dir trufflehog

# Install AWS git-secrets tool
RUN git clone https://github.com/awslabs/git-secrets.git /usr/var/git-secrets \
 && cd /usr/var/git-secrets \
 && make install \
 && git secrets --register-aws --global

# Expect the repository to be mounted here
WORKDIR /code

CMD /bin/bash

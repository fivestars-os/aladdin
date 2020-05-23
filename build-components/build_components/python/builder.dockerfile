### CREATE A BUILDER IMAGE #############################################################
# This image will hold all of the tools required for building python packages. It will
# be used to build python packages before copying them out using the multi-stage
# builder pattern.
########################################################################################
ARG FROM_IMAGE
FROM $FROM_IMAGE

# Install packages required to build native library components
RUN apt-get update \
 && apt-get -y --no-install-recommends install \
    gettext \
    gcc \
    g++ \
    make \
    libc6-dev
# We intenionally do not clear the lists here, as one may wish to derive their own
# builder image from this one, and it doesn't make sense to force them to do their
# own apt-get update. The image size here isn't as much of a concern, since none of
# these build tools will end-up in the final built image.

# Upgrade pip
RUN pip install --upgrade pip

# Configure pip
COPY pip.conf /etc/pip.conf

# Install poetry under the root user's home directory
ARG POETRY_VERSION
ADD https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py /tmp/get-poetry.py
RUN python /tmp/get-poetry.py --version $POETRY_VERSION \
 && chmod a+rx /root/.poetry/bin/poetry

# Configure poetry
COPY poetry.toml /root/.config/pypoetry/config.toml

# Move to build directory before copying items to non-fixed location
WORKDIR /build

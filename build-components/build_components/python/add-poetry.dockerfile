### INSTALL THE POETRY PACKAGE MANAGER #################################################
# Copy the poetry tool and its configuration into the target image. This also includes
# a bit of pip global configuration since poetry uses it under the hood (as do our
# own tools).
########################################################################################
ARG BUILDER_IMAGE
ARG FROM_IMAGE

# We'll copy over the builder image's poetry installation
FROM $BUILDER_IMAGE as builder

FROM $FROM_IMAGE

# Configure pip
COPY --from="builder" /etc/pip.conf /etc/pip.conf

# Copy installed python packages from the builder image to a system directory in the
# this image. While this isn't strictly how poetry is expected to be installed, it's
# not violating any assumptions. We'll use the XDG_CONFIG_HOME to inform poetry where
# it can read its config from add the .poetry/bin directory to the PATH so any user
# can use it.
COPY --from="builder" /root/.poetry /usr/local/share/.poetry

# Configure poetry
COPY --from="builder" /root/.config/pypoetry /usr/local/etc/pypoetry
ENV XDG_CONFIG_HOME /usr/local/etc

# Add poetry to PATH
ENV PATH $PATH:/usr/local/share/.poetry/bin

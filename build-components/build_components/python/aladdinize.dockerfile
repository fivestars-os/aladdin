### BASE IMAGE BUILD ###################################################################
# This is where we install our common boilerplate for aladdin project components.
# These items are only really important for images that will contain your custom
# functionality. If you do not need this boilerplate override this behavior by providing
# your own custom image.base tag in your component.yaml.
#
# If you wish to further customize your image with a dockerfile, say to provide an
# ENTRYPOINT or such, create a Dockerfile in your component directory and it will be
# applied immediately following this one. Be sure to use the FROM_IMAGE pattern seen
# here.
#
# If you do not wish to apply this boilerplate to your image, set image.aladdinize to
# false in your component.yaml.
########################################################################################
ARG FROM_IMAGE
FROM $FROM_IMAGE

# Pre-compile python core library code
ARG PYTHON_OPTIMIZE
RUN python $PYTHON_OPTIMIZE -m compileall

# Use our own special directory for our code
WORKDIR /code
ENV PYTHONPATH /code

# Create the unprivileged user account
ARG ADD_TO_SUDOERS
RUN useradd -m -U -d /home/aladdin-user aladdin-user \
 && if "$ADD_TO_SUDOERS"; then \
        apt-get update && apt-get -y --no-install-recommends install sudo && rm -rf /var/lib/apt/lists/*; \
        echo >> /etc/sudoers "aladdin-user ALL=(ALL) NOPASSWD: ALL"; \
    fi

# Switch to the unprivileged user account
USER aladdin-user

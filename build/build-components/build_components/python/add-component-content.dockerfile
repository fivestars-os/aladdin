### POPULATE IMAGE BUILD ###############################################################
# This is where we copy the component's code into our eventual concrete image.
########################################################################################
ARG FROM_IMAGE
FROM $FROM_IMAGE

# Copy component code to the WORKDIR
COPY . .

# Install the component itself (this installs any poetry scripts as command line commands)
ARG COMPONENT
ARG POETRY_INSTALL_COMPONENT
RUN if $POETRY_INSTALL_COMPONENT; then cd "$COMPONENT" && poetry install; fi

# Pre-compile optimized bytecode for our component packages
ARG PYTHON_OPTIMIZE
RUN python $PYTHON_OPTIMIZE -m compileall .
### END POPULATE IMAGE BUILD ###########################################################
# We now have the beginnings of a functional image with the python dependencies specific
# to the component we're building it for and it's application code. This process will be
# repeated for all of a component's dependency components and then one final time for
# the component itself.
########################################################################################

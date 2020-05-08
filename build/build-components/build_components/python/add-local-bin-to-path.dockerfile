### ADD LOCAL BIN TO PATH ##############################################################
# This is where we add the poetry packages' bin directory to the USER's path
########################################################################################
ARG FROM_IMAGE
FROM $FROM_IMAGE

ARG USER_HOME=/root
ENV PATH $USER_HOME/.local/bin:$PATH

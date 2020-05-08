########################################################################################
# This dockerfile allows us to create a temporary image for inspection purposes.
# Specifically, we wish to know the user, their main group and their home directory.
# These values are used to install component library dependencies, as poetry assumes
# one will be installing packages in a user's home directory and with their permissions.
# It assumes that the FROM_IMAGE already has the container user setup with a home
# directory.
########################################################################################
ARG FROM_IMAGE
FROM $FROM_IMAGE

CMD "/bin/sh"
ENTRYPOINT []

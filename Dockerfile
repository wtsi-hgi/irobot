FROM ubuntu:trusty
MAINTAINER Christopher Harrison <ch12@sanger.ac.uk>

# Install Ubuntu system packages
RUN apt-get update \
 && apt-get -y install python \
                       krb5-user \
                       wget \
                       libfuse2 \
                       libgssapi-krb5-2

# Download and install iRODS client with Kerberos plugin
RUN wget ftp://ftp.renci.org/pub/irods/releases/4.1.10/ubuntu14/irods-icommands-4.1.10-ubuntu14-x86_64.deb \
         ftp://ftp.renci.org/pub/irods/plugins/irods_auth_plugin_krb/1.4/irods-auth-plugin-krb-1.4-ubuntu14-x86_64.deb \
 && dpkg -i irods-icommands-4.1.10-ubuntu14-x86_64.deb \
            irods-auth-plugin-krb-1.4-ubuntu14-x86_64.deb \
 && apt-get -fy install

# TODO: Upgrade to Xenial?
FROM ubuntu:trusty
MAINTAINER Christopher Harrison <ch12@sanger.ac.uk>

ENV TMP_DIRECTORY="/$TMPDIR/irobot"
ENV IROBOT_DIRECTORY=/irobot

# TODO: This could be a buildarg if supported on target platforms
ENV IRODS_KERBEROS_SUPPORT=1

RUN mkdir -p "${TMP_DIRECTORY}"
WORKDIR "${TMP_DIRECTORY}"

ADD docker/install-irods.sh install-irods.sh
RUN ./install-irods.sh

ADD docker/install-baton.sh install-baton.sh
RUN ./install-baton.sh
ENV LD_LIBRARY_PATH="/usr/local/lib:/usr/lib:/lib"

ADD requirements.txt requirements.txt
RUN pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

RUN rm -rf "${TMP_DIRECTORY}"
RUN mkdir -p "${IROBOT_DIRECTORY}"
WORKDIR "${IROBOT_DIRECTORY}"

ADD . ./

ENTRYPOINT ["${IROBOT_DIRECTORY}/docker/setup.sh"]

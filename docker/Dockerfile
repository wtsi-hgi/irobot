# TODO: Upgrade to Xenial?
FROM ubuntu:trusty
MAINTAINER Christopher Harrison <ch12@sanger.ac.uk>

ENV TMP_DIRECTORY="/$TMPDIR/irobot"
ENV IROBOT_DIRECTORY=/irobot

RUN mkdir -p "${TMP_DIRECTORY}"
WORKDIR "${TMP_DIRECTORY}"

ADD docker/install-irods.sh install-irods.sh
RUN ./install-irods.sh

ADD docker/install-baton.sh install-baton.sh
RUN ./install-baton.sh
ENV LD_LIBRARY_PATH="/usr/local/lib:/usr/lib:/lib"

RUN rm -rf "${TMP_DIRECTORY}"
RUN mkdir -p "${IROBOT_DIRECTORY}"
WORKDIR "${IROBOT_DIRECTORY}"

ADD . ./
RUN pip install -r requirements.txt

ENTRYPOINT ["${IROBOT_DIRECTORY}/docker/setup.sh"]

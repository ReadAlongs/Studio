FROM debian:buster-slim

ENV APPHOME /opt/readalong-studio
ENV LANG=en_US.UTF-8
ENV PORT 5000

# TODO: remove portaudio19
RUN apt-get update && apt-get install -y \
        python3 \
        python3-pip \
        git \
        swig \
        libpulse-dev \
        portaudio19-dev


COPY . $APPHOME
WORKDIR $APPHOME

# Install ReadAlong-Studio
RUN python3 -m pip install -e .


ENTRYPOINT [ "python3", "run.py" ]

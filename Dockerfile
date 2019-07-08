FROM debian:buster-slim

ENV APPHOME /opt/readalong-studio
ENV PORT 5000

# Install system dependencies
#  - swig: required by pocketsphinx
#  - libpulse-dev: required by pocketsphinx
#  - portaudio19-dev: required by pocketsphinx
RUN apt-get update && apt-get install -y \
        python3 \
        python3-pip \
        git \
        swig \
        libpulse-dev \
        portaudio19-dev \
        ffmpeg


COPY . $APPHOME
WORKDIR $APPHOME

# Install ReadAlong-Studio
RUN python3 -m pip install -e .

#ENTRYPOINT [ "python3", "run.py" ]
CMD tail -f /dev/null

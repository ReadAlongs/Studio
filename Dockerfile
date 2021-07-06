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
        ffmpeg \
        vim-nox

# Install 3rd party dependencies in their own layer, for faster rebuilds when we
# change ReadAlong-Studio source code
ADD requirements.txt $APPHOME/requirements.txt
RUN python3 -m pip install -r $APPHOME/requirements.txt
# RUN python3 -m pip install gunicorn # If you want to run production server
RUN git clone https://github.com/roedoejet/g2p.git
RUN cd g2p && python3 -m pip install -e .

# Install ReadAlong-Studio itself
COPY . $APPHOME
WORKDIR $APPHOME
RUN python3 -m pip install -e .
RUN python3 -m pip install gevent
CMD gunicorn -k gevent -w 1 readalongs.app:app --bind 0.0.0.0:5000

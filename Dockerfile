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
RUN python3 -m pip install gevent
ADD requirements.txt $APPHOME/requirements.txt
RUN python3 -m pip install -r $APPHOME/requirements.txt
# RUN python3 -m pip install gunicorn # If you want to run production server

# We don't want Docker to cache the installation of g2p or Studio, so place them
# after COPY . $APPHOME, which almost invariable invalidates the cache.
COPY . $APPHOME
WORKDIR $APPHOME
# Get and install the latest g2p
RUN git clone https://github.com/roedoejet/g2p.git
RUN cd g2p && python3 -m pip install -e .
# Install ReadAlong-Studio itself
RUN python3 -m pip install -e .

# Run the default gui (on localhost:5000)
CMD python3 ./run.py

# For a production server, comment out the default gui CMD above, and run the
# gui using gunicorn instead:
# CMD gunicorn -k gevent -w 1 readalongs.app:app --bind 0.0.0.0:5000

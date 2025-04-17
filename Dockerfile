FROM alpine:latest AS runtime

ENV APPHOME=/opt/readalong-studio

# Lean, optimized installation of system dependencies
RUN apk add python3 py3-numpy py3-yaml git ffmpeg

FROM runtime AS build
WORKDIR $APPHOME
RUN apk add python3-dev py3-pip gcc g++ musl-dev ninja
RUN python3 -m venv --system-site-packages $APPHOME/venv
RUN git clone https://github.com/roedoejet/g2p.git
COPY requirements*.txt $APPHOME/
RUN . $APPHOME/venv/bin/activate \
    && python3 -m pip install -r $APPHOME/requirements.txt
RUN . $APPHOME/venv/bin/activate \
    && python3 -m pip install soundswallower
RUN cd $APPHOME/g2p \
    && . $APPHOME/venv/bin/activate python3 -m pip install -e .
# Do this after all the above so we don't needlessly rebuild
COPY . $APPHOME/Studio
RUN cd $APPHOME/Studio \
    && . $APPHOME/venv/bin/activate \
    && python3 -m pip install -e .

FROM runtime
COPY --from=build $APPHOME $APPHOME
WORKDIR $APPHOME
ENV VIRTUAL_ENV=$APPHOME/venv
ENV PATH=$VIRTUAL_ENV/bin:$PATH

# Run this container with `docker run -d -p 8000:8000` for local
# testing, or use `-p` to map whichever host port you want to 8000 on
# the container. Set ORIGIN to the base URL of your Studio-Web for
# production deployments.

ENV PORT=8000
ENV ORIGIN=http://localhost:4200
EXPOSE $PORT
SHELL ["/bin/sh", "-c"]
CMD gunicorn -w 4 -k uvicorn.workers.UvicornWorker readalongs.web_api:web_api_app --bind 0.0.0.0:$PORT

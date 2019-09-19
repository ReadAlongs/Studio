FROM ubuntu:18.04

MAINTAINER Patrick Littell "patrick.littell@nrc.gc.ca"

RUN apt-get update -y && \
    apt-get install -y python-pip python-dev

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app
RUN mkdir /data

RUN pip install -r requirements.txt

COPY . /app

CMD [ "app.py" ]

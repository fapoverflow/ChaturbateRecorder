FROM python:3.7.3-alpine3.9

RUN apk update
RUN apk add --no-cache libffi-dev libxml2-dev libxslt-dev # tzdata

#ENV TZ 'Europe/Paris'

COPY requirements.txt /opt/ChaturbateRecorder/requirements.txt
WORKDIR /opt/ChaturbateRecorder

RUN pip install -U pip setuptools
RUN pip install -r requirements.txt

COPY . /opt/ChaturbateRecorder/

EXPOSE 443
EXPOSE 8081

ENTRYPOINT run.sh

FROM python:3.7.3-alpine3.9

RUN apk update
RUN apk add --no-cache bash g++ gcc build-base libffi-dev libxml2 libxml2-dev libxslt-dev

COPY requirements.txt /opt/ChaturbateRecorder/requirements.txt
WORKDIR /opt/ChaturbateRecorder

RUN pip install -U pip setuptools
RUN pip install -r requirements.txt

COPY . /opt/ChaturbateRecorder/

EXPOSE 443
EXPOSE 80
#EXPOSE 8081

ENTRYPOINT python /opt/ChaturbateRecorder/ChaturbateRecorder.py

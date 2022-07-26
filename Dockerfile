FROM python:3.10-slim

ENV CONTAINER_HOME=/data
ENV PYTHONUNBUFFERED=1

ADD . $CONTAINER_HOME
WORKDIR $CONTAINER_HOME

ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN pip install -r requirements.txt
CMD python main.py
FROM python:3.10-slim

ENV CONTAINER_HOME=/data
ENV PYTHONUNBUFFERED=1

ADD . $CONTAINER_HOME
WORKDIR $CONTAINER_HOME

RUN sudo echo "America/New_York" > /etc/timezone
RUN sudo dpkg-reconfigure -f noninteractive tzdata

RUN pip install -r requirements.txt
CMD python main.py
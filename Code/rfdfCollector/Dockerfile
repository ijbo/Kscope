FROM python:3.8

WORKDIR /home/rfdfCollector
COPY requirements.txt ./
COPY app/ ./app
RUN apt-get update
RUN apt-get install -y docker.io
RUN pip install --no-cache-dir -r requirements.txt


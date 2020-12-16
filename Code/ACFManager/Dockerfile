FROM python:3.8

WORKDIR /home/ACFManager
COPY requirements.txt ./
COPY src/ ./src
RUN apt update
RUN apt install sshpass
RUN pip install --no-cache-dir -r requirements.txt
COPY acfstart.sh ./acfstart.sh
COPY acfstop.sh ./acfstop.sh
COPY __init__.py ./__init__.py
ENTRYPOINT ["/bin/bash", "-c", "./acfstart.sh"]


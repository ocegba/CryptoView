FROM python:3.11-buster

WORKDIR /app
ADD app .

ADD  requirements.txt .

# Installer Java
RUN apt-get update && \
    apt-get install -y openjdk-11-jre-headless && \
    rm -rf /var/lib/apt/lists/*

RUN  pip install -r requirements.txt

CMD [ "python", "main.py" ]
# Instantiate Ubuntu 20.04
FROM ubuntu:20.04
LABEL description="Server Image"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install curl -y
RUN apt-get install pkg-config -y

# install nginx
RUN apt-get -y install nginx
RUN apt-get install python3-certbot-nginx -y

# ffmpeg
RUN apt-get install ffmpeg -y

RUN apt-get -y install python3
RUN apt-get -y install python3-pip


# create project directory and contents
RUN mkdir /app
COPY . /app
WORKDIR /app

RUN pip3 install -r scripts/server/python_requirements.txt
RUN bash scripts/server/setup.sh

# Open port and run
EXPOSE 80
EXPOSE 443
CMD ["bash", "scripts/server/run_all.sh"]


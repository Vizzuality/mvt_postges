FROM python:3.7

ENV USER maptest
RUN apt-get update && apt-get install -y bash git gcc \
  build-essential postgresql postgresql-client postgresql-contrib
RUN addgroup $USER && useradd -ms /bin/bash $USER -g $USER

COPY . /opt/app
WORKDIR /opt/app

RUN pip install -r requirements.txt

# Tell Docker we are going to use this ports
EXPOSE 5000
USER $USER
# Launch script
ENTRYPOINT ["sh","./entrypoint.sh"]






FROM python:3.7
MAINTAINER Vizzuality Science Team info@vizzuality.com

ENV USER maptest
RUN apt-get update && apt-get install -y bash git gcc 
RUN addgroup $USER && useradd -ms /bin/bash $USER -g $USER

WORKDIR /opt
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

# Tell Docker we are going to use this ports
EXPOSE 5100
USER $USER
# Launch script
ENTRYPOINT ["sh","./entrypoint.sh"]






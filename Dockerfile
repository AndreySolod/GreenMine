FROM python:3.13

RUN apt update && apt -y dist-upgrade && mkdir /greenmine \
    && apt install -y wget apt-transport-https ca-certificates python3 python-is-python3 python3-pip nmap
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && apt install -y ./google-chrome-stable_current_amd64.deb

WORKDIR /greenmine
COPY ./requirements.production.txt /greenmine/requirements.txt
RUN pip3 install --upgrade pip && pip3 install -r /greenmine/requirements.txt
COPY ./app /greenmine/app
COPY ./default_database_value /greenmine/default_database_value
COPY ./migrations /greenmine/migrations
COPY ./config.py /greenmine/config.py
COPY ./GreenMine.py /greenmine/GreenMine.py
COPY ./run_celery.py /greenmine/run.py
COPY ./docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh && mkdir logs
ENV FLASK_APP=/greenmine/GreenMine.py
CMD ["/docker-entrypoint.sh"]

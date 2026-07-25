FROM python:3.9


WORKDIR /srv/PleaseGraduate
COPY . /srv/PleaseGraduate/

RUN pip install -r requirements.txt
RUN pip install uwsgi

CMD ["bash", "docker_cmd.sh", "prod"]
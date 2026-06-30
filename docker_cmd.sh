#!/bin/bash

# 도커 컨테이너 내부에서 실행될 스크립트

PROFILE=$1

service cron start

if [ -n "$PORT" ]; then
    # Render와 같이 PORT 환경 변수가 주어지는 플랫폼용 설정 (HTTP 프로토콜 사용)
    echo "Running on Render/Cloud platform with PORT=$PORT"
    python manage.py crontab add --settings=project.settings.prod
    uwsgi --http :$PORT --module project.wsgi:application --master --processes 4 --threads 2
elif [ "$PROFILE" == "dev" ]; then
    python manage.py crontab add --settings=project.settings.dev
    cd /srv/PleaseGraduate/dev/
    uwsgi --ini uwsgi.ini
else
    python manage.py crontab add --settings=project.settings.prod
    cd /srv/PleaseGraduate/deploy/
    uwsgi --ini uwsgi.ini
fi

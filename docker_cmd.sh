#!/bin/bash

# 도커 컨테이너 내부에서 실행될 스크립트

PROFILE=$1

if [ -n "$PORT" ]; then
    # Render와 같이 PORT 환경 변수가 주어지는 플랫폼용 설정 (HTTP 프로토콜 사용)
    echo "Running on Render/Cloud platform with PORT=$PORT"
    uwsgi --http :$PORT --module project.wsgi:application --master --processes 4 --threads 2
elif [ "$PROFILE" == "dev" ]; then
    cd /srv/PleaseGraduate/dev/
    uwsgi --ini uwsgi.ini
else
    cd /srv/PleaseGraduate/deploy/
    uwsgi --ini uwsgi.ini
fi


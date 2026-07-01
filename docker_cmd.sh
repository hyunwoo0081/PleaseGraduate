#!/bin/bash

# 도커 컨테이너 내부에서 실행될 스크립트

PROFILE=$1

if [ -n "$PORT" ]; then
    # Render와 같이 PORT 환경 변수가 주어지는 플랫폼용 설정 (HTTP 프로토콜 사용)
    echo "Running on Render/Cloud platform with PORT=$PORT"
    export DJANGO_SETTINGS_MODULE=project.settings.prod
    
    # 데이터베이스 마이그레이션 및 테이블 생성 스크립트 실행
    echo "Running database migrations..."
    python manage.py migrate --noinput
    echo "Running setup_database.py..."
    python setup_database.py
    echo "Running import_excel_data.py..."
    python import_excel_data.py
    
    uwsgi --http :$PORT --module project.wsgi:application --master --processes 4 --threads 2 --buffer-size 65535
elif [ "$PROFILE" == "dev" ]; then
    cd /srv/PleaseGraduate/dev/
    uwsgi --ini uwsgi.ini
else
    cd /srv/PleaseGraduate/deploy/
    uwsgi --ini uwsgi.ini
fi


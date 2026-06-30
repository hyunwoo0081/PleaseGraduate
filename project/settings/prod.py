from .base import *

DEBUG = False

ALLOWED_HOSTS = [ '.please-graduate.com' ]  # 배포전 변경

# static file 경로 설정
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'app', 'static')
]
STATIC_ROOT = os.path.join(BASE_DIR, 'deploy/col_static')
STATIC_URL = '/static/'
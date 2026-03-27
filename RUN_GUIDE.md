# PleaseGraduate 실행 가이드

이 프로젝트는 Docker 환경에서 Django와 uWSGI를 기반으로 실행됩니다. 환경에 따라 아래 순서대로 설정을 진행해 주세요.

---

## 1. 공통 준비 사항

### 환경 변수 설정 (`.env`)
프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 아래 내용을 입력합니다. (파일 경로: `./.env`)

```env
# Django 설정
SECRET_KEY=your_secret_key_here
DEBUG=True

# Database 설정 (MySQL 사용 시 필수)
DB_NAME=pleasegraduate
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=db  # Docker Compose 내부 서비스 이름 또는 호스트 IP
```

---

## 2. 개발 환경 (Development)
로컬에서 코드를 수정하며 테스트하는 환경입니다. 호스트와 컨테이너 간의 볼륨이 동기화됩니다.

### 실행 순서
1. **컨테이너 빌드 및 실행**
   ```powershell
   docker-compose -f dev/docker-compose.yml up -d --build
   ```

2. **데이터베이스 테이블 생성 (최초 1회)**
   - Django 기본 테이블 생성:
     ```powershell
     docker-compose -f dev/docker-compose.yml exec django python manage.py migrate --settings=project.settings.dev
     ```
   - `managed = False` 모델용 테이블 및 기초 데이터 생성 (사용자 커스텀 스크립트):
     ```powershell
     docker-compose -f dev/docker-compose.yml exec django python setup_database.py
     ```

3. **서버 접속**
   - 주소: `http://localhost:8000`

---

## 3. 배포 환경 (Production)
실제 서버에 배포하기 위한 환경입니다. 정적 파일 및 uWSGI 소켓 설정을 포함합니다.

### 실행 순서
1. **환경 변수 체크**
   배포 환경용 `docker-compose.yml`은 Docker 이미지 정보가 필요합니다. 터미널에 환경 변수가 설정되어 있어야 합니다.
   ```powershell
   $env:DOCKER_USERNAME="username"
   $env:DOCKER_REPOSITORY="repo"
   $env:DOCKER_TAG="latest"
   ```

2. **컨테이너 실행**
   ```powershell
   docker-compose -f deploy/docker-compose.yml up -d
   ```

3. **정적 파일 모으기 (최초 1회)**
   ```powershell
   docker-compose -f deploy/docker-compose.yml exec django python manage.py collectstatic --settings=project.settings.prod --noinput
   ```

---

## 4. API 테스트 방법
서버가 정상적으로 띄워졌다면 아래 명령어로 졸업 요건 판정 API를 테스트할 수 있습니다.

```powershell
curl -X POST http://localhost:8000/api/v1/graduation/check-excel/ `
  -F "student_id=19011094" `
  -F "major=컴퓨터공학과" `
  -F "year=2019" `
  -F "excel=@test_data/기이수성적조회_20260327.xlsx"
```

---

## 5. 주의 사항 (Windows 사용자)
- **줄 바꿈(Line Ending):** `docker_cmd.sh` 파일은 반드시 **LF** 형식이어야 합니다. CRLF로 저장될 경우 Docker 내부에서 실행되지 않습니다.
- **Docker Desktop:** 실행 전 Docker Desktop이 활성화되어 있는지 확인하세요.

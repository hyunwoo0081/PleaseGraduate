# Render 배포 가이드 (무료 플랜 및 대외비 관리용)

이 가이드는 Render.com의 Web Service(Docker 기반) 환경을 활용하여, 대외비 데이터를 노출하지 않고 무료 플랜의 제한된 자원(영구 디스크 없음, SQLite 사용)을 극복하여 서비스를 배포하는 방법을 안내합니다.

---

## 1. 배포 개념 및 구조

Render의 무료 플랜은 서버가 일정 시간 유휴 상태가 되면 꺼졌다가 요청이 올 때 다시 켜지는 구조를 가지며, **영구 디스크(Persistent Volume)를 사용할 수 없어 서버가 재부팅될 때마다 SQLite 데이터베이스(`db.sqlite3`)가 완전히 초기화**됩니다.

이 제한을 해결하고 대외비 데이터를 보호하기 위해 다음과 같은 메커니즘을 사용합니다:
1. **대외비 데이터 보호**: 기밀성 있는 졸업 요건 및 강의 정보 엑셀 파일들을 GitHub 저장소에 올리지 않고, 로컬에서 **Base64(평문 텍스트)로 인코딩**하여 Render의 **Secret Files**로 안전하게 주입합니다.
2. **부팅 시 데이터베이스 자동 구성**: 서버가 켜질 때마다 `docker_cmd.sh` 내부에서 Django 마이그레이션이 실행되고, `import_excel_data.py` 스크립트가 `/etc/secrets/`에 마운트된 Base64 텍스트 데이터를 디코딩하여 SQLite 데이터베이스를 즉시 재구성(초기화 및 로드)합니다.

---

## 2. 로컬 엑셀 파일 Base64 변환하기

대외비로 유지되어야 하는 엑셀 파일들을 Render의 Secret Files에 등록하기 위해, 제공하는 `encode_excel.py` 유틸리티 스크립트를 사용하여 단일 Base64 텍스트 파일(`.txt`)로 변환합니다.

### 변환 순서:
1. `standard` 탭과 `major` 탭이 포함되어 있는 단일 엑셀 파일(예: `database_data.xlsx`)을 다음 경로 중 하나에 위치시킵니다:
   * `./test_data/database_data.xlsx`
   * `./dev/update_table/database_data.xlsx`
   * `./database_data.xlsx` (프로젝트 루트)
2. 로컬 터미널에서 아래 명령어를 실행하여 변환을 수행합니다:
   ```bash
   python encode_excel.py
   ```
3. 실행이 완료되면 프로젝트 루트에 `render_secrets/` 디렉토리가 생성되고, 그 내부에 `database_data_base64.txt` 파일이 저장됩니다. 이 파일의 내용이 Render Secret Files로 업로드할 대상입니다.

---

## 3. Render 설정

### Web Service 생성
1. Render 대시보드에서 **New +** > **Web Service**를 클릭합니다.
2. 이 프로젝트의 GitHub 저장소를 연결합니다.
3. 서비스 환경 설정:
   * **Language**: `Docker`로 선택 (루트 디렉토리의 `Dockerfile`을 자동으로 인식해 빌드합니다)
   * **Instance Type**: `Free` (무료 요금제)

### Environment Variables (환경 변수) 설정
**Environment** 탭으로 이동하여 아래의 환경 변수들을 구성합니다.

| Key | Value | 설명 |
| :--- | :--- | :--- |
| `SECRET_KEY` | `임의의 길고 무작위한 보안 문자열` | Django의 보안 키 |
| `DEBUG` | `False` | 운영(Production) 환경 모드 설정 |

### Secret Files 설정
동일한 **Environment** 탭 내 **Secret Files** 항목에서 생성한 Base64 텍스트 파일을 업로드하거나 복사해서 붙여넣습니다.

* **Filename**: `database_data_base64.txt`

> **Note**: 위 파일은 컨테이너 내부의 `/etc/secrets/database_data_base64.txt` 경로에 마운트되며, 컨테이너 부팅 시 실행되는 `import_excel_data.py`에 의해 감지되어 `standard` 및 `major` 테이블의 데이터로 각각 자동 주입됩니다. (만약 예전 방식처럼 여러 개의 개별 파일로 올리시려면, 파일명을 `standard_base64.txt`, `major_base64.txt` 형태로 등록하셔도 하위 호환 작동합니다.)

---

## 4. 모니터링 및 동작 확인

1. **빌드 로그 확인**: 
   Render가 Dockerfile을 감지하여 패키지를 설치하고 이미지 빌드 과정을 완료하는지 모니터링합니다.
2. **배포 및 구동 로그 확인**: 
   서버가 구동되면서 아래와 같은 형태의 로그가 남으면 정상적으로 데이터베이스 세팅 및 데이터 로드가 성공한 것입니다:
   ```text
   Running database migrations...
   Operations to perform:
     Apply all migrations: admin, auth, contenttypes, sessions, messages, staticfiles
   ...
   Running setup_database.py...
   Running import_excel_data.py...
   Loading standard from Render Secret File (/etc/secrets/standard_base64.txt)...
   Standard imported successfully.
   Loading major from Render Secret File (/etc/secrets/major_base64.txt)...
   Major imported successfully.
   ...
   All excel imports completed!
   uWSGI http bound on :10000
   ```
3. **API 테스트**:
   배포된 Render primary URL을 사용해 다음과 같이 `POST` 요청을 날려 200 OK 응답이 나오는지 확인합니다:
   ```bash
   curl -X POST \
     -F "student_id=20201234" \
     -F "major=컴퓨터공학과" \
     -F "year=2020" \
     -F "excel=@your_grade_excel.xlsx" \
     https://<your-service-name>.onrender.com/api/v1/graduation/check-excel/
   ```

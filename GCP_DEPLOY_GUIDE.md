# GCP 배포 가이드 (사내 API 용)

이 가이드는 GCP Compute Engine(VM)을 사용하여 졸업 요건 판정 API를 사내에서 사용하기 위한 세팅 과정을 안내합니다.

---

## 1. GCP Compute Engine 설정

### VM 인스턴스 생성
1.  **GCP 콘솔** > **Compute Engine** > **VM 인스턴스** 로 이동합니다.
2.  **인스턴스 만들기**를 클릭합니다.
    -   **이름:** `please-graduate-api`
    -   **지역:** 사내와 가까운 곳 (예: `asia-northeast3` 서울)
    -   **머신 유형:** `e2-micro`(테스트용) 또는 `e2-small`(사내 운영 권장)
    -   **부팅 디스크:** `Ubuntu 20.04 LTS` 또는 `22.04 LTS`
    -   **방화벽:** `HTTP 트래픽 허용`, `HTTPS 트래픽 허용` 체크
3.  만들기를 완료합니다.

### 고정 외부 IP 및 방화벽 설정
1.  **VPC 네트워크** > **IP 주소** 에서 방금 만든 인스턴스의 외부 IP를 **정적**으로 예약합니다.
2.  **VPC 네트워크** > **방화벽** 에서 규칙을 추가합니다.
    -   **이름:** `allow-django-api`
    -   **소스 IPv4 범위:** `0.0.0.0/0` (사내 전용이라면 사내 IP 대역만 넣으세요)
    -   **프로토콜 및 포트:** TCP `8000` (API 포트)

---

## 2. VM 서버 초기 세팅 (SSH 접속 후)

VM에 SSH로 접속하여 아래 명령어를 차례대로 실행하여 Docker를 설치합니다.

```bash
# 1. 시스템 업데이트 및 Docker 설치
sudo apt-get update
sudo apt-get install -y docker.io docker-compose

# 2. Docker 권한 설정 (로그아웃 후 재접속 필요할 수 있음)
sudo chmod 666 /var/run/docker.sock

# 3. 배포 디렉토리 생성
sudo mkdir -p /srv/deploy
sudo chown -R $USER:$USER /srv
```

---

## 3. GitHub Secrets 설정

GitHub 저장소의 `Settings` > `Secrets and variables` > `Actions` 에 다음 값을 등록합니다.

| 이름 | 설명 | 예시 |
| :--- | :--- | :--- |
| `GCP_INSTANCE_HOST` | VM의 고정 외부 IP | `34.xx.xx.xx` |
| `GCP_INSTANCE_USERNAME` | VM 접속 계정명 | `ubuntu` |
| `GCP_INSTANCE_PRIVATE_KEY` | SSH Private Key 내용 | `-----BEGIN RSA PRIVATE KEY----- ...` |
| `SECRET_KEY` | Django 보안키 | 임의의 긴 문자열 |
| `DOCKER_USERNAME` | Docker Hub 아이디 | `yourid` |
| `DOCKER_PASSWORD` | Docker Hub 비밀번호 | `yourpassword` |
| `DOCKER_REPOSITORY` | Docker 저장소 이름 | `pleasegraduate` |
| `DOCKER_TAG` | 이미지 태그 | `latest` |

---

## 4. 배포 실행

1.  GitHub 상단의 **Actions** 탭으로 이동합니다.
2.  좌측 메뉴에서 **Deploy to GCP** 워크플로우를 선택합니다.
3.  **Run workflow** 버튼을 눌러 배포를 시작합니다.
4.  배포가 완료되면 `http://[GCP_IP]:8000/api/v1/graduation/check-excel/`로 요청을 보낼 수 있습니다.

---

## 5. 데이터 업데이트 방법
졸업 요건 기준 데이터(`test_data/database_data.xlsx`)를 수정하여 GitHub에 푸시하고 다시 배포(Run workflow)하면, 자동으로 서버의 데이터베이스가 최신화됩니다.

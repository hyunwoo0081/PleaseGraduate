# Graduation Requirement Check API

졸업요건 판정 API – `PleaseGraduate` 기반 무인증 REST API

---

## 엔드포인트

### `POST /api/v1/graduation/check-excel/`

세종대학교 학사정보시스템에서 내려받은 **기이수성적 엑셀(.xlsx)** 파일을 업로드하면
졸업요건 판정 결과를 JSON으로 반환합니다.

---

## 요청 (Request)

**Content-Type:** `multipart/form-data`

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `excel` | file | ✅ | `.xlsx` 기이수성적 파일 |
| `student_id` | string | ✅ | 요청 식별자 (학번 형태 권장, 예: `20000001`) |
| `major` | string | ✅ | 전공명 (`Standard.user_dep`와 매칭, 예: `컴퓨터공학과`) |
| `year` | int | ✅ | 입학년도 2자리 (`Standard.user_year`와 매칭, 예: `20`) |
| `name` | string | | 이름 (기본값: `student_id`) |
| `major_status` | string | | 복수/연계전공 여부 (기본값: `해당없음`) |
| `eng` | string | | 영어인증 정보 (기본값: `해당없음`) |
| `book` | string | | 고전독서 현황 4자리 문자열 (기본값: `0000`) |
| `include_recommendations` | bool | | 추천과목 포함 여부 (기본값: `true`) |
| `include_rule_evidence` | bool | | 규칙별 근거 포함 여부 (기본값: `true`) |

---

## 성공 응답 (200 OK)

```json
{
  "result": {
    "summary": {
      "pass": true,
      "computed_at": "2024-06-01T12:00:00+09:00"
    },
    "areas": [
      {
        "area_id": "major_essential",
        "name": "전공필수",
        "required": 36,
        "earned": 36,
        "deficit": 0,
        "pass": true,
        "evidence": {
          "recom_selection": []
        }
      },
      {
        "area_id": "major_selection",
        "name": "전공선택",
        "required": 39,
        "earned": 42,
        "deficit": -3,
        "pass": true,
        "evidence": {
          "remain": 0,
          "recom_selection": []
        }
      },
      {
        "area_id": "book",
        "name": "고전독서",
        "required": null,
        "earned": 10,
        "deficit": null,
        "pass": true,
        "evidence": {
          "W": 4, "E": 2, "EW": 3, "S": 1, "total": 10
        }
      }
    ],
    "rules": [
      {
        "rule_id": "major_essential",
        "name": "전공필수",
        "passed": true,
        "required": 36,
        "earned": 36,
        "deficit": 0,
        "evidence": {}
      },
      {
        "rule_id": "total",
        "name": "총학점",
        "passed": true,
        "required": 130,
        "earned": 145,
        "deficit": -15,
        "evidence": {}
      }
    ],
    "raw": {
      "result_context": {
        "exists": { "ce": 1, "cs": 1, "la_balance": 0, "b": 1, "english": 1, "multi": 0 },
        "user_info": { "id": "20000001", "name": "홍길동", "major": "컴퓨터공학과", "year": 20 },
        "book": { "W": 4, "E": 2, "EW": 3, "S": 1, "total": 10, "pass": 1 },
        "major_essential": { "standard_num": 36, "user_num": 36, "lack": 0, "pass": 1 },
        "total": { "standard_num": 130, "user_num": 145, "pass": 1 }
      }
    }
  }
}
```

---

## 에러 응답

모든 에러 응답은 아래 구조를 공유합니다:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "설명 메시지",
    "details": {}
  }
}
```

| HTTP 상태 | `error.code` | 원인 |
|---|---|---|
| 422 | `VALIDATION_ERROR` | 필수 필드 누락 또는 형식 오류 |
| 400 | `INVALID_EXCEL_FORMAT` | Excel 파일 형식/내용 오류 |
| 404 | `STANDARD_NOT_FOUND` | `major`/`year` 조합의 기준 데이터 없음 |
| 500 | `INTERNAL_ERROR` | 계산 중 내부 오류 |

### 예: 필수 필드 누락 (422)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "필수 필드가 누락되었습니다.",
    "details": {
      "missing_fields": ["student_id", "year"]
    }
  }
}
```

### 예: Excel 형식 오류 (400)

```json
{
  "error": {
    "code": "INVALID_EXCEL_FORMAT",
    "message": "엑셀 내용이 다릅니다. 수정하지 않은 엑셀파일을 올려주세요."
  }
}
```

### 예: 기준 미존재 (404)

```json
{
  "error": {
    "code": "STANDARD_NOT_FOUND",
    "message": "전공(없는학과)/학번(99)에 해당하는 기준이 존재하지 않습니다."
  }
}
```

---

## curl 요청 예시

```bash
curl -X POST https://<host>/api/v1/graduation/check-excel/ \
  -F "excel=@/path/to/grade.xlsx" \
  -F "student_id=20000001" \
  -F "major=컴퓨터공학과" \
  -F "year=20" \
  -F "name=홍길동" \
  -F "major_status=해당없음" \
  -F "eng=해당없음" \
  -F "book=4231" \
  -F "include_recommendations=true" \
  -F "include_rule_evidence=true"
```

---

## 동작 원리 (Approach A)

1. Excel 파싱/검증 → DataFrame  
2. `temp_user_id` (`api_<uuid>`) 생성  
3. `NewUserInfo`에 임시 사용자 row 생성  
4. `UserGrade`에 성적 데이터 insert  
5. `f_result(temp_user_id)` 호출 → `result_context` 생성  
6. 필요 시 `f_en_result(temp_user_id)` 호출 (공학인증)  
7. 응답 JSON 구성  
8. `try/finally`로 임시 데이터 삭제 (항상 실행)

---

## 주의사항

- 인증/세션 없이 호출 가능한 무인증 API입니다.
- 요청 처리 후 임시 DB 데이터는 반드시 삭제됩니다.
- `major` 값은 DB의 `Standard.user_dep` 컬럼 값과 정확히 일치해야 합니다.
- `book` 필드는 고전독서 현황 4자리 숫자 문자열 (W/E/EW/S 순서)입니다. 예: `"4231"` = W:4, E:2, EW:3, S:1

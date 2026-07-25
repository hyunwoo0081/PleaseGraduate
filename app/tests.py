"""
졸업요건 판정 API 테스트
Django TestCase 기반 최소 테스트.
"""
import io
import json
import openpyxl
from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory
from django.urls import reverse

from app.services.excel_parser import parse_sejong_grade_excel, ExcelFormatError
from app.views.api import check_excel


# ─── 헬퍼: 유효한 엑셀 파일 생성 ───────────────────────────────────────────

def _make_excel(rows=None, bad_columns=False):
    """
    세종대 형식의 기이수성적 엑셀을 BytesIO로 생성한다.
    rows: list of dicts with column values. None이면 빈 데이터.
    bad_columns: True이면 컬럼명을 잘못 설정.
    """
    wb = openpyxl.Workbook()
    ws = wb.active

    # 원본 엑셀: 실제로는 행 1-2가 헤더 이전 잡행, 행 3이 컬럼명, 행 4가 빈 행
    # parse_sejong_grade_excel 에서 delete_rows(1,2) -> delete_rows(2) 처리
    # 즉 결과적으로 남는 구조:
    #   행1: 컬럼명
    #   행2: (비어있음, 삭제 후 drop)
    #   행3~: 데이터
    #
    # 역산: ws에 다음과 같이 넣어야 파서가 올바르게 읽음
    #   행1: (잡행1)
    #   행2: (잡행2)
    #   행3: 컬럼명
    #   행4: (빈 행 역할 - 파서가 df.iloc[0,:]로 컬럼 설정 후 df.iloc[1:,:]로 데이터 추출)
    #   행5~: 데이터

    if bad_columns:
        columns = ['잘못된', '컬럼', '형식']
    else:
        columns = ['순번', '년도', '학기', '학수번호', '교과목명', '이수구분',
                   '교직영역', '선택영역', '학점', '평가방식', '등급', '평점', '개설학과코드']

    ws.append(['dummy_row_1'])      # 행1: 잡행
    ws.append(['dummy_row_2'])      # 행2: 잡행
    ws.append(columns)              # 행3: 컬럼명
    ws.append([''] * len(columns))  # 행4: 빈 행 (파서 df.iloc[0] 이후 drop)

    if rows:
        for i, r in enumerate(rows, start=1):
            ws.append([
                i,                          # 순번
                r.get('년도', '2023'),
                r.get('학기', '1학기'),
                r.get('학수번호', '1234'),
                r.get('교과목명', '테스트과목'),
                r.get('이수구분', '전필'),
                r.get('교직영역', ''),
                r.get('선택영역', ''),
                r.get('학점', 3),
                r.get('평가방식', '절대평가'),
                r.get('등급', 'A'),
                r.get('평점', 4.5),
                r.get('개설학과코드', 'CS'),
            ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    buf.name = 'test.xlsx'
    return buf


# ─── excel_parser 단위 테스트 ────────────────────────────────────────────────

class ExcelParserTest(TestCase):

    def test_wrong_extension_raises(self):
        buf = io.BytesIO(b'not an excel')
        buf.name = 'grade.csv'
        with self.assertRaises(ExcelFormatError):
            parse_sejong_grade_excel(buf)

    def test_bad_columns_raises(self):
        buf = _make_excel(bad_columns=True)
        with self.assertRaises(ExcelFormatError):
            parse_sejong_grade_excel(buf)

    def test_valid_excel_returns_dataframe(self):
        rows = [
            {'년도': '2023', '학기': '1학기', '학수번호': '1234', '교과목명': '알고리즘',
             '이수구분': '전필', '선택영역': '', '학점': 3, '등급': 'A'},
        ]
        buf = _make_excel(rows=rows)
        df = parse_sejong_grade_excel(buf)
        self.assertEqual(len(df), 1)
        self.assertIn('학수번호', df.columns)

    def test_invalid_grade_rows_removed(self):
        rows = [
            {'학수번호': '1111', '교과목명': '합격과목', '등급': 'B', '학점': 3},
            {'학수번호': '2222', '교과목명': 'F과목', '등급': 'F', '학점': 3},
            {'학수번호': '3333', '교과목명': 'NP과목', '등급': 'NP', '학점': 2},
        ]
        buf = _make_excel(rows=rows)
        df = parse_sejong_grade_excel(buf)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['교과목명'], '합격과목')


# ─── API 뷰 테스트 ───────────────────────────────────────────────────────────

class CheckExcelAPITest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def _post(self, data, files=None):
        post_data = dict(data)
        if files:
            post_data.update(files)
        return self.factory.post('/api/v1/graduation/check-excel', data=post_data)

    def test_missing_fields_returns_422(self):
        request = self.factory.post('/api/v1/graduation/check-excel', data={})
        response = check_excel(request)
        self.assertEqual(response.status_code, 422)
        body = json.loads(response.content)
        self.assertEqual(body['error']['code'], 'VALIDATION_ERROR')

    def test_bad_excel_returns_400(self):
        buf = io.BytesIO(b'not excel content')
        buf.name = 'bad.xlsx'
        request = self._post(
            {'student_id': '20000001', 'major': '컴퓨터공학과', 'year': '20'},
            {'excel': buf},
        )
        response = check_excel(request)
        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content)
        self.assertEqual(body['error']['code'], 'INVALID_EXCEL_FORMAT')

    @patch('app.views.api.Standard')
    def test_standard_not_found_returns_404(self, mock_standard):
        mock_standard.objects.filter.return_value.exists.return_value = False
        buf = _make_excel(rows=[])
        request = self._post(
            {'student_id': '20000001', 'major': '없는학과', 'year': '20'},
            {'excel': buf},
        )
        response = check_excel(request)
        self.assertEqual(response.status_code, 404)
        body = json.loads(response.content)
        self.assertEqual(body['error']['code'], 'STANDARD_NOT_FOUND')

    @patch('app.views.api.f_result')
    @patch('app.views.api.Standard')
    @patch('app.views.api.UserGrade')
    @patch('app.views.api.NewUserInfo')
    def test_success_returns_200_with_required_keys(
            self, mock_user_info, mock_user_grade, mock_standard, mock_f_result):
        # Standard 존재
        mock_standard.objects.filter.return_value.exists.return_value = True
        mock_standard.objects.get.return_value = MagicMock(pro=None)
        # NewUserInfo / UserGrade mock
        mock_user_instance = MagicMock()
        mock_user_info.return_value = mock_user_instance
        mock_user_grade.return_value = MagicMock()
        mock_user_grade.objects.filter.return_value.delete.return_value = None
        mock_user_info.objects.filter.return_value.delete.return_value = None
        # f_result mock
        mock_f_result.return_value = {
            'exists': {'ce': 0, 'cs': 0, 'la_balance': 0, 'b': 0, 'english': 0, 'multi': 0},
            'user_info': {'id': 'api_xxx', 'name': '테스트', 'major': '컴퓨터공학과', 'year': 20},
            'book': {'pass': 1, 'total': 10},
            'major_essential': {'standard_num': 36, 'user_num': 36, 'lack': 0, 'pass': 1},
            'major_selection': {'standard_num': 39, 'user_num': 39, 'remain': 0, 'lack': 0, 'pass': 1},
            'total': {'standard_num': 130, 'user_num': 135, 'pass': 1},
        }

        buf = _make_excel(rows=[
            {'학수번호': '1234', '교과목명': '알고리즘', '이수구분': '전필', '학점': 3, '등급': 'A'},
        ])
        request = self._post(
            {'student_id': '20000001', 'major': '컴퓨터공학과', 'year': '20'},
            {'excel': buf},
        )
        response = check_excel(request)
        self.assertEqual(response.status_code, 200)
        temp_student_id = mock_user_info.call_args.kwargs['student_id']
        self.assertLessEqual(len(temp_student_id), 10)
        body = json.loads(response.content)
        self.assertIn('result', body)
        result = body['result']
        self.assertIn('summary', result)
        self.assertIn('areas', result)
        self.assertIn('rules', result)
        self.assertIn('raw', result)
        self.assertIn('pass', result['summary'])
        self.assertIn('computed_at', result['summary'])
        self.assertIn('result_context', result['raw'])

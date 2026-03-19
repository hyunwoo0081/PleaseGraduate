"""
Sejong 학사정보시스템 "기이수성적" 엑셀 파일을 파싱하는 서비스 모듈.
f_mod_grade 의 파싱/검증 로직을 재사용 가능한 함수로 분리한 것.
"""
import openpyxl
import pandas as pd


# 성적표 엑셀의 필수 컬럼 목록 (순번 제외 후)
REQUIRED_COLUMNS = [
    '년도', '학기', '학수번호', '교과목명', '이수구분',
    '교직영역', '선택영역', '학점', '평가방식', '등급', '평점', '개설학과코드',
]

# 인정되지 않는 등급
INVALID_GRADES = ['F', 'FA', 'NP']

# UserGrade 저장에 불필요한 컬럼
DROP_COLUMNS = ['교직영역', '평가방식', '등급', '평점', '개설학과코드']


class ExcelFormatError(Exception):
    """Excel 파일 형식/내용이 올바르지 않을 때 발생하는 예외."""
    pass


def parse_sejong_grade_excel(file) -> pd.DataFrame:
    """
    세종대학교 학사정보시스템에서 내려받은 기이수성적 엑셀(.xlsx)을 읽어
    정제된 DataFrame으로 반환한다.

    반환 컬럼:
        년도, 학기, 학수번호, 교과목명, 이수구분, 선택영역, 학점

    Raises:
        ExcelFormatError: 파일 형식이나 내용이 기대와 다를 때.
    """
    # 확장자 검사
    filename = getattr(file, 'name', '')
    if not str(filename).lower().endswith('.xlsx'):
        raise ExcelFormatError('잘못된 파일 형식입니다. 확장자가 xlsx인 파일을 올려주세요.')

    try:
        wb = openpyxl.load_workbook(file)
        ws = wb.active
        # 원본 엑셀은 1~4행 중 컬럼명 행을 제외하고 삭제해야 함
        ws.delete_rows(1, 2)
        ws.delete_rows(2)
        df = pd.DataFrame(ws.values)
        df.columns = df.iloc[0, :]
        df = df.iloc[1:, :]
        df = df.drop(['순번'], axis=1)
    except ExcelFormatError:
        raise
    except Exception:
        raise ExcelFormatError('엑셀 내용이 다릅니다. 수정하지 않은 엑셀파일을 올려주세요.')

    # 컬럼명 검증
    if list(df.columns) != REQUIRED_COLUMNS:
        raise ExcelFormatError('엑셀 내용이 다릅니다. 수정하지 않은 엑셀파일을 올려주세요.')

    df.fillna('', inplace=True)

    # F / FA / NP 과목 제거
    drop_idx = [i for i, row in df.iterrows() if row['등급'] in INVALID_GRADES]
    df.drop(drop_idx, inplace=True)

    # 불필요 컬럼 삭제
    df.drop(DROP_COLUMNS, axis=1, inplace=True)

    return df

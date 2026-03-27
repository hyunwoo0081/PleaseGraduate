"""
졸업요건 판정 API
POST /api/v1/graduation/check-excel
"""
import uuid
import datetime
import traceback

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ..models import NewUserInfo, UserGrade, Standard
from ..services.excel_parser import parse_sejong_grade_excel, ExcelFormatError
from .calculate import f_result, f_en_result


def _error(code: str, message: str, status: int, details: dict = None) -> JsonResponse:
    body = {'error': {'code': code, 'message': message}}
    if details:
        body['error']['details'] = details
    return JsonResponse(body, status=status)


def _build_summary(result_context: dict) -> dict:
    total = result_context.get('total', {})
    return {
        'pass': bool(total.get('pass', 0)),
        'computed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def _build_areas(result_context: dict) -> list:
    areas = []

    def _area(area_id, name, ctx, required_key='standard_num', earned_key='user_num', lack_key='lack'):
        if ctx is None:
            return
        required = ctx.get(required_key)
        earned = ctx.get(earned_key)
        deficit = ctx.get(lack_key)
        areas.append({
            'area_id': area_id,
            'name': name,
            'required': required,
            'earned': earned,
            'deficit': deficit,
            'pass': bool(ctx.get('pass', 0)),
            'evidence': {k: v for k, v in ctx.items()
                         if k not in ('standard_num', 'user_num', 'lack', 'pass')},
        })

    _area('major_essential', '전공필수', result_context.get('major_essential'))
    _area('major_selection', '전공선택', result_context.get('major_selection'))
    _area('core_essential', '교양필수', result_context.get('core_essential'))
    _area('core_selection', '교양선택', result_context.get('core_selection'))
    _area('la_balance', '균형교양', result_context.get('la_balance'))
    _area('basic', '기초교양', result_context.get('basic'))
    _area('multi_major_essential', '복수/연계전공필수', result_context.get('multi_major_essential'))
    _area('multi_major_selection', '복수/연계전공선택', result_context.get('multi_major_selection'))

    book_ctx = result_context.get('book')
    if book_ctx is not None:
        areas.append({
            'area_id': 'book',
            'name': '고전독서',
            'required': None,
            'earned': book_ctx.get('total'),
            'deficit': None,
            'pass': bool(book_ctx.get('pass', 0)),
            'evidence': {k: v for k, v in book_ctx.items() if k != 'pass'},
        })

    eng_ctx = result_context.get('english')
    if eng_ctx is not None:
        areas.append({
            'area_id': 'english',
            'name': '영어인증',
            'required': None,
            'earned': None,
            'deficit': None,
            'pass': bool(eng_ctx.get('pass', 0)),
            'evidence': {k: v for k, v in eng_ctx.items() if k != 'pass'},
        })

    return areas


def _build_rules(result_context: dict) -> list:
    rules = []
    areas = _build_areas(result_context)
    for area in areas:
        rules.append({
            'rule_id': area['area_id'],
            'name': area['name'],
            'passed': area['pass'],
            'required': area['required'],
            'earned': area['earned'],
            'deficit': area['deficit'],
            'evidence': area['evidence'],
        })
    total_ctx = result_context.get('total')
    if total_ctx:
        rules.append({
            'rule_id': 'total',
            'name': '총학점',
            'passed': bool(total_ctx.get('pass', 0)),
            'required': total_ctx.get('standard_num'),
            'earned': total_ctx.get('user_num'),
            'deficit': (total_ctx.get('standard_num', 0) - total_ctx.get('user_num', 0))
                       if total_ctx.get('standard_num') is not None else None,
            'evidence': {},
        })
    return rules


@csrf_exempt
@require_POST
def check_excel(request):
    # ── 1. 필수 폼 필드 검증 ──────────────────────────────────────────────
    student_id = request.POST.get('student_id', '').strip()
    major = request.POST.get('major', '').strip()
    year_str = request.POST.get('year', '').strip()

    missing = []
    if not student_id:
        missing.append('student_id')
    if not major:
        missing.append('major')
    if not year_str:
        missing.append('year')
    if 'excel' not in request.FILES:
        missing.append('excel')
    if missing:
        return _error('VALIDATION_ERROR', '필수 필드가 누락되었습니다.', 422,
                      {'missing_fields': missing})

    try:
        year = int(year_str)
    except ValueError:
        return _error('VALIDATION_ERROR', 'year는 정수여야 합니다.', 422)

    name = request.POST.get('name', '').strip() or student_id
    major_status = request.POST.get('major_status', '해당없음').strip() or '해당없음'
    eng = request.POST.get('eng', '해당없음').strip() or '해당없음'
    book = request.POST.get('book', '0000').strip() or '0000'
    include_recommendations = request.POST.get('include_recommendations', 'true').lower() != 'false'
    include_rule_evidence = request.POST.get('include_rule_evidence', 'true').lower() != 'false'

    # ── 2. Excel 파싱 ─────────────────────────────────────────────────────
    try:
        df = parse_sejong_grade_excel(request.FILES['excel'])
    except ExcelFormatError as exc:
        return _error('INVALID_EXCEL_FORMAT', str(exc), 400)

    # ── 3. Standard 존재 검증 ─────────────────────────────────────────────
    if not Standard.objects.filter(user_dep=major, user_year=year).exists():
        return _error(
            'STANDARD_NOT_FOUND',
            f'전공({major})/학번({year})에 해당하는 기준이 존재하지 않습니다.',
            404,
        )

    # ── 4. 임시 사용자 생성 ───────────────────────────────────────────────
    temp_id = f'api_{uuid.uuid4().hex[:20]}'
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        temp_user = NewUserInfo(
            student_id=temp_id,
            password='',
            year=year,
            major=major,
            major_status=major_status,
            name=name,
            book=book,
            eng=eng,
            register_time=now_str,
        )
        temp_user.save()

        # ── 5. UserGrade 삽입 ─────────────────────────────────────────────
        for _, row in df.iterrows():
            ug = UserGrade(
                student_id=temp_id,
                major=major,
                year=str(row['년도']),
                semester=str(row['학기']),
                subject_num=str(row['학수번호']).lstrip('0'),
                subject_name=str(row['교과목명']),
                classification=str(row['이수구분']),
                selection=str(row['선택영역']) if row['선택영역'] != '' else None,
                grade=float(row['학점']),
            )
            ug.save()

        # ── 6. 졸업요건 계산 ──────────────────────────────────────────────
        try:
            result_context = f_result(temp_id)
        except Exception:
            return _error('INTERNAL_ERROR', f'졸업요건 계산 중 오류가 발생했습니다: {traceback.format_exc()}', 500)

        # 공학인증 결과 (Standard에 pro 필드가 있을 경우에만)
        en_result_context = None
        try:
            std = Standard.objects.get(user_dep=major, user_year=year)
            if std.pro:
                en_result_context = f_en_result(temp_id)
        except Exception:
            pass

        # ── 7. 응답 구성 ──────────────────────────────────────────────────
        summary = _build_summary(result_context)
        areas = _build_areas(result_context)
        rules = _build_rules(result_context)

        if not include_recommendations:
            for area in areas:
                area['evidence'].pop('recom_selection', None)
                area['evidence'].pop('recom_essential', None)
                area['evidence'].pop('recom', None)
            for rule in rules:
                rule['evidence'].pop('recom_selection', None)
                rule['evidence'].pop('recom_essential', None)
                rule['evidence'].pop('recom', None)

        if not include_rule_evidence:
            for area in areas:
                area['evidence'] = {}
            for rule in rules:
                rule['evidence'] = {}

        raw = {'result_context': result_context}
        if en_result_context:
            raw['en_result_context'] = en_result_context

        return JsonResponse({
            'result': {
                'summary': summary,
                'areas': areas,
                'rules': rules,
                'raw': raw,
            }
        }, status=200)

    finally:
        # ── 8. 임시 데이터 cleanup (항상 실행) ───────────────────────────
        UserGrade.objects.filter(student_id=temp_id).delete()
        NewUserInfo.objects.filter(student_id=temp_id).delete()

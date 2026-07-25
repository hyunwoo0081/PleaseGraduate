import os
import django
import pandas as pd
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.dev')
django.setup()

from django.db import connection
from app.models import (
    Standard, Major, AllLecture, NewLecture, ChangedClassification, 
    UserInfo, UserGrade, NewUserInfo, SubjectGroup
)

def setup_managed_tables():
    # 모든 관련 모델 추가
    models = [
        Standard, Major, AllLecture, NewLecture, ChangedClassification, 
        UserInfo, UserGrade, NewUserInfo, SubjectGroup
    ]
    with connection.schema_editor() as schema_editor:
        for model in models:
            model._meta.managed = True
            try:
                schema_editor.create_model(model)
                print(f"Table for {model.__name__} created.")
            except Exception as e:
                print(f"Table for {model.__name__} already exists or error: {e}")

def load_data_from_excel():
    # 19학번 컴퓨터공학과 데이터 기본 생성 (최소 요건)
    Standard.objects.get_or_create(
        user_dep='컴퓨터공학과',
        user_year=2019,
        defaults={
            'index': 1,
            'sum_score': 130,
            'major_essential': 18,
            'major_selection': 42,
            'core_essential': 9,
            'core_selection': 12,
            'la_balance': 15,
            'basic': 12,
            'ce_list': '',
            'cs_list': '',
            'b_list': '',
            'english': {}, 
            'sum_eng': 1,
        }
    )
    Major.objects.get_or_create(
        major='컴퓨터공학과',
        defaults={'college': '소프트웨어융합대학', 'department': '컴퓨터공학과'}
    )
    print("Essential data loaded.")

if __name__ == "__main__":
    setup_managed_tables()
    load_data_from_excel()

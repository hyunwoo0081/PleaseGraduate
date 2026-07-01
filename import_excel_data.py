import os
import django
import pandas as pd
import json
import base64
import io

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.prod')
django.setup()

from app.models import (
    Standard, Major, AllLecture, NewLecture, ChangedClassification, 
    SubjectGroup
)
from django_pandas.io import read_frame

# 단일 파일 후보 경로들 (로컬용)
SINGLE_FILE_CANDIDATES = [
    "./test_data/database_data.xlsx",
    "./dev/update_table/database_data.xlsx",
    "./database_data.xlsx"
]

def load_database_excel():
    # 1. Render Secret File (Base64 평문 텍스트) 존재 여부 확인
    secret_path = "/etc/secrets/database_data_base64.txt"
    if os.path.exists(secret_path):
        print(f"Loading single database file from Render Secret File ({secret_path})...")
        try:
            with open(secret_path, "r", encoding="utf-8") as f:
                b64_data = f.read().strip()
            binary_data = base64.b64decode(b64_data)
            return io.BytesIO(binary_data), True
        except Exception as e:
            print(f"[-] Error decoding Render Secret File: {e}")
            return None, False

    # 2. 로컬/GCP 단일 파일 확인
    for path in SINGLE_FILE_CANDIDATES:
        if os.path.exists(path):
            print(f"Loading single database file from local path ({path})...")
            return path, True

    return None, False

def find_sheet(sheet_names, targets):
    for sheet in sheet_names:
        if sheet.lower() in [t.lower() for t in targets]:
            return sheet
    return None

def get_sheet_df(excel_file, sheet_targets):
    if excel_file is None:
        return None
    try:
        xl = pd.ExcelFile(excel_file)
        matched = find_sheet(xl.sheet_names, sheet_targets)
        if matched:
            return xl.parse(matched)
        return None
    except Exception as e:
        print(f"[-] Error reading sheet {sheet_targets}: {e}")
        return None

# 개별 파일 fallback 로딩 (하위 호환성 유지)
def get_fallback_excel_df(name, local_dir):
    secret_path = f"/etc/secrets/{name}_base64.txt"
    if os.path.exists(secret_path):
        print(f"Loading {name} from Render Secret File ({secret_path})...")
        try:
            with open(secret_path, "r", encoding="utf-8") as f:
                b64_data = f.read().strip()
            binary_data = base64.b64decode(b64_data)
            return pd.read_excel(io.BytesIO(binary_data), index_col=None)
        except Exception as e:
            print(f"[-] Error decoding Render Secret File for {name}: {e}")
            return None

    if os.path.exists(local_dir) and os.listdir(local_dir):
        file_name = os.listdir(local_dir)[0]
        full_path = os.path.join(local_dir, file_name)
        print(f"Loading {name} from local file ({full_path})...")
        try:
            return pd.read_excel(full_path, index_col=None)
        except Exception as e:
            print(f"[-] Error reading local file for {name}: {e}")
            return None

    return None

def update_standard(excel_file, is_single):
    if is_single:
        df = get_sheet_df(excel_file, ["standard", "기준"])
    else:
        df = get_fallback_excel_df("standard", './dev/update_table/standard/')

    if df is None:
        print("[-] Standard data not found, skipping.")
        return
        
    df.fillna(0, inplace=True)
    Standard.objects.all().delete()
    
    for i, row in df.iterrows():
        new_st = Standard()
        new_st.index = i
        new_st.user_year = row['user_year']
        new_st.user_dep = row['user_dep']
        new_st.sum_score = int(row['sum_score'])
        new_st.major_essential = int(row['major_essential'])
        new_st.major_selection = int(row['major_selection'])
        new_st.core_essential = int(row['core_essential'])
        new_st.core_selection = int(row['core_selection'])
        new_st.la_balance = int(row['la_balance'])
        new_st.basic = int(row['basic'])
        new_st.ce_list = str(row['ce_list'])
        new_st.cs_list = str(row['cs_list'])
        new_st.b_list = str(row['b_list'])
        new_st.english = json.dumps(eval(str(row['english'])))
        new_st.sum_eng = int(row['sum_eng'])
        new_st.pro = int(row['pro'])
        new_st.bsm = int(row['bsm'])
        new_st.eng_major = int(row['eng_major'])
        new_st.build_sel_num = int(row['build_sel_num'])
        new_st.pro_ess_list = str(row['pro_ess_list'])
        new_st.bsm_ess_list = str(row['bsm_ess_list'])
        new_st.bsm_sel_list = str(row['bsm_sel_list'])
        new_st.build_start = str(int(row['build_start']))
        new_st.build_sel_list = str(row['build_sel_list'])
        new_st.build_end = str(int(row['build_end']))
        new_st.eng_major_list = str(row['eng_major_list'])
        new_st.save()
    print("[+] Standard imported successfully.")

def update_major(excel_file, is_single):
    if is_single:
        df = get_sheet_df(excel_file, ["major", "전공"])
    else:
        df = get_fallback_excel_df("major", './dev/update_table/major/')

    if df is None:
        print("[-] Major data not found, skipping.")
        return
        
    df.fillna('', inplace=True)
    Major.objects.all().delete()
    
    for i, row in df.iterrows():
        new_m = Major()
        new_m.college = row['college']
        new_m.major = row['major']
        new_m.department = row['department']
        new_m.save()
    print("[+] Major imported successfully.")

def update_subject_group(excel_file, is_single):
    if is_single:
        df = get_sheet_df(excel_file, ["subject_group", "대체과목"])
    else:
        df = get_fallback_excel_df("subject_group", './dev/update_table/subject_group/')

    if df is None:
        print("[-] SubjectGroup data not found, skipping.")
        return
        
    need_col = ['group_num', 'subject_num']
    df.drop([d for d in list(df) if d not in need_col], axis=1, inplace=True)
    df.fillna('', inplace=True)
    
    SubjectGroup.objects.all().delete()
    
    for i, row in df.iterrows():
        new_sg = SubjectGroup()
        new_sg.group_num = int(row['group_num'])
        new_sg.subject_num = int(row['subject_num'])
        new_sg.save()
    print("[+] SubjectGroup imported successfully.")

def update_changed_classification(excel_file, is_single):
    if is_single:
        df = get_sheet_df(excel_file, ["changed_classification", "이수구분변경"])
    else:
        df = get_fallback_excel_df("changed_classification", './dev/update_table/changed_classification/')

    if df is None:
        print("[-] ChangedClassification data not found, skipping.")
        return
        
    need_col = ['subject_num','year','classification']
    df.drop([d for d in list(df) if d not in need_col], axis=1, inplace=True)
    df.fillna('', inplace=True)
    
    ChangedClassification.objects.all().delete()
    
    for i, row in df.iterrows():
        new_cc = ChangedClassification()
        new_cc.index = i
        new_cc.subject_num = row['subject_num']
        new_cc.year = int(row['year'])
        new_cc.classification = row['classification']
        new_cc.save()
    print("[+] ChangedClassification imported successfully.")

def make_merge_df(excel_file, is_single):
    if is_single:
        df_1 = get_sheet_df(excel_file, ["2nd_semester", "2학기강의"])
        df_2 = get_sheet_df(excel_file, ["1st_semester", "1학기강의"])
    else:
        df_1 = get_fallback_excel_df("2nd_semester", './dev/update_table/2nd_semester/')
        df_2 = get_fallback_excel_df("1st_semester", './dev/update_table/1st_semester/')

    if df_1 is None or df_2 is None:
        return None, None
        
    need_col = ['학수번호', '교과목명', '이수구분', '선택영역', '학점']
    
    df_1.drop([d for d in list(df_1) if d not in need_col], axis=1, inplace=True)
    df_1['학수번호'] = pd.to_numeric(df_1['학수번호'])
    df_1.drop_duplicates(['학수번호'], inplace=True, ignore_index=True)
    
    df_2.drop([d for d in list(df_2) if d not in need_col], axis=1, inplace=True)
    df_2['학수번호'] = pd.to_numeric(df_2['학수번호'])
    df_2.drop_duplicates(['학수번호'], inplace=True, ignore_index=True)
    
    group_snum = [int(row.subject_num) for row in SubjectGroup.objects.all()]
    delete_candidate = []
    for s_num in df_1[df_1["학수번호"].isin(group_snum)]["학수번호"].to_list():
        try:
            g_num = SubjectGroup.objects.get(subject_num=s_num).group_num
            sg_qs = SubjectGroup.objects.filter(group_num=g_num)
            for row in sg_qs:
                delete_candidate.append(int(row.subject_num))
        except SubjectGroup.DoesNotExist:
            pass
            
    df_2 = df_2[~df_2["학수번호"].isin(delete_candidate)]
    df_2.reset_index(inplace=True, drop=True)
    
    df_merge = pd.concat([df_1, df_2])
    df_merge.drop_duplicates(['학수번호'], inplace=True, ignore_index=True)
    df_merge.fillna('', inplace=True)
    
    def convert_classification(classification):
        if classification == "교양필수": return "교필"
        elif classification == "교양선택": return "교선"
        elif classification == "전공선택": return "전선"
        elif classification == "전공필수": return "전필"
        elif classification == "학문기초교양필수": return "기필"
        elif classification == "공통교양필수": return "공필"
        elif classification == "균형교양필수": return "균필"
        elif classification == "무관후보생교육": return "ROTC"
        else: return classification
    df_merge["이수구분"] = df_merge["이수구분"].apply(convert_classification)
    s_num_list = df_merge['학수번호'].tolist()
    return df_merge, s_num_list

def update_lecture(excel_file, is_single):
    df_merge, s_num_list = make_merge_df(excel_file, is_single)
    if df_merge is None or s_num_list is None:
        print("[-] Lecture data/sheets not found, skipping.")
        return
        
    print("Importing lectures...")
    NewLecture.objects.all().delete()
    for s_num in s_num_list:
        new_nl = NewLecture()
        new_nl.subject_num = s_num
        new_nl.save()
        
    df_al = read_frame(AllLecture.objects.all())
    if not df_al.empty:
        df_al.rename(columns={'subject_num': '학수번호', 'subject_name': '교과목명',
                     'classification': '이수구분', 'selection': '선택영역', 'grade': '학점'}, inplace=True)
        for i, row in df_al.iterrows():
            if int(row['학수번호']) in s_num_list:
                df_al.drop(i, inplace=True)
        df_new_al = pd.concat([df_al, df_merge])
    else:
        df_new_al = df_merge

    AllLecture.objects.all().delete()
    for i, row in df_new_al.iterrows():
        new_al = AllLecture()
        new_al.subject_num = row['학수번호']
        new_al.subject_name = row['교과목명']
        new_al.classification = row['이수구분']
        new_al.selection = row['선택영역']
        new_al.grade = row['학점']
        new_al.save()
    print("[+] Lectures imported successfully.")

if __name__ == '__main__':
    excel_file, is_single = load_database_excel()
    
    update_standard(excel_file, is_single)
    update_major(excel_file, is_single)
    update_subject_group(excel_file, is_single)
    update_changed_classification(excel_file, is_single)
    update_lecture(excel_file, is_single)
    print("All excel imports completed!")

import streamlit as st
import pandas as pd
from fpdf import FPDF
import requests
from io import BytesIO
from datetime import date
from dateutil.relativedelta import relativedelta

# --- 1. قاعدة بيانات المشاريع ---
PROJECTS_DATABASE = {
    "SILA MASDAR": {
        "url": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=0&single=true&output=csv",
        "gov_pct": 2.0, "admin_fees": 625, "res_fee": 20000
    },
    "KHALIFA CITY": {
        "url": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1491192679&single=true&output=csv",
        "gov_pct": 1.0, "admin_fees": 625, "res_fee": 20000
    },
    "SENSI": {
        "url": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=0&single=true&output=csv", 
        "gov_pct": 2.0, "admin_fees": 625, "res_fee": 50000
    },
    "RHILLS": {
        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=517225281&single=true&output=csv",
        "gov_pct": 4.0, "admin_fees": 1194, "res_fee": 20000 
    }
}

PHOTO_BANK_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1714647206&single=true&output=csv"
LOGO_URL = "https://i.ibb.co/3sbsK2S/Reportage-Logo.png"

# --- 2. وظائف التحميل والحساب ---
@st.cache_data
def load_google_sheet(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip() 
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return df
    except: return None

# (دوال الحساب و PDF تبقى كما هي في الكود الأصلي لتوفير المساحة)
# [دالة get_handover_date و calculate_ultra_flexible_plan و create_sales_offer_pdf]

# --- 3. واجهة المستخدم ---
st.set_page_config(page_title="Reportage Smart Agent", layout="wide")
st.title("🏗️ Reportage Sales AI")

with st.sidebar:
    st.header("🏢 Settings")
    selected_project = st.selectbox("Project:", list(PROJECTS_DATABASE.keys()))
    proj_info = PROJECTS_DATABASE[selected_project]
    df_inventory = load_google_sheet(proj_info["url"])
    df_photos = load_google_sheet(PHOTO_BANK_URL)
    # ... (باقي المدخلات: الخطط، الخصم، الخ)

if df_inventory is not None:
    unit_id = st.selectbox("Unit:", df_inventory['Plot + Unit No.'].unique())
    unit_data = df_inventory[df_inventory['Plot + Unit No.'] == unit_id].iloc[0]
    
    # --- منطق البحث المطور عن الصور (Smart Search for SENSI Fix) ---
    layout_url = None
    if df_photos is not None:
        try:
            # تنظيف البيانات
            df_photos['clean_proj'] = df_photos['Project'].astype(str).str.upper().str.strip()
            df_photos['clean_bed'] = df_photos['Bedrooms'].astype(str).str.replace('.0', '', regex=False).str.strip()
            df_photos['clean_sub'] = df_photos['Sub-type'].astype(str).str.upper().str.strip()
            
            p_key = selected_project.split()[0].upper() # سيعطي SENSI
            unit_bed = str(unit_data.get('Bedrooms', '')).replace('.0', '').strip()
            unit_sub = str(unit_data.get('Sub-type', '')).upper().strip()

            # 1. فحص لو كان المشروع SENSI (عشان مشكلة حرف S و N في شيت الصور)
            if p_key == "SENSI":
                # ابحث عن أي صف يحتوي على SENSI أو SESNI ونفس عدد الغرف والـ Sub-type
                match = df_photos[
                    (df_photos['clean_proj'].str.contains("SENSI") | df_photos['clean_proj'].str.contains("SESNI")) & 
                    (df_photos['clean_bed'] == unit_bed) & 
                    (df_photos['clean_sub'] == unit_sub)
                ]
            else:
                # البحث العادي لبقية المشاريع
                match = df_photos[
                    (df_photos['clean_proj'].str.contains(p_key)) & 
                    (df_photos['clean_bed'] == unit_bed) & 
                    (df_photos['clean_sub'] == unit_sub)
                ]

            # 2. لو ملقاش تطابق دقيق (مثلاً الـ Sub-type مختلف في الكتابة)
            if match.empty:
                if p_key == "SENSI":
                     match = df_photos[
                        (df_photos['clean_proj'].str.contains("SENSI") | df_photos['clean_proj'].str.contains("SESNI")) & 
                        (df_photos['clean_bed'] == unit_bed)
                    ]
                else:
                    match = df_photos[
                        (df_photos['clean_proj'].str.contains(p_key)) & 
                        (df_photos['clean_bed'] == unit_bed)
                    ]

            if not match.empty:
                layout_url = match.iloc[0]['Layout_URL']
        except: layout_url = None

    # --- عرض النتائج والـ PDF ---
    # (استخدم نفس كود عرض المقياس والجداول والـ Download Button اللي عندك)

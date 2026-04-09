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

# --- 2. الخطط المتاحة ---
ALL_PLANS = {
    "30% DP / 5% Disc / 70% Handover": {"dp_pct": 30, "disc": 5, "default_monthly": 0.0},
    "5% DP / 5% Disc / 1% Monthly": {"dp_pct": 5, "disc": 5, "default_monthly": 1.0},
    "5% DP / 0% Disc / 1% Monthly": {"dp_pct": 5, "disc": 0, "default_monthly": 1.0},
    "20% DP / 15% Disc / 1% Monthly": {"dp_pct": 20, "disc": 15, "default_monthly": 1.0},
    "20% DP / 2% Disc / 10%@12m / 70% HO": {"dp_pct": 20, "disc": 2, "default_monthly": 0.0, "is_special": True},
    "Plan 12 (Cash 40% Disc)": {"dp_pct": 100, "disc": 40, "default_monthly": 0.0}
}

# --- وظائف مساعدة ---
@st.cache_data
def load_google_sheet(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except: return None

def clean_num(val):
    """تنظيف الأرقام من الفواصل والنصوص الغريبة"""
    if pd.isna(val) or str(val).strip() == "": return 0.0
    try:
        return float(str(val).replace(',', '').replace('AED', '').strip())
    except: return 0.0

def get_handover_date(unit_data):
    for col in ['Handover Date', 'Handover', 'Completion Date', 'HANDOVER DATE']:
        val = unit_data.get(col)
        if val and str(val).lower() != 'nan':
            try: return pd.to_datetime(val).date()
            except: continue
    return date(2027, 12, 31)

def calculate_ultra_flexible_plan(selling_price, plan_cfg, settings, start_date, handover_date, res_fee):
    plan = []
    plan.append({"Milestone": "Reservation Fee (Booking)", "Date": "Now", "Percent": "-", "Amount": res_fee})
    
    dp_pct = plan_cfg['dp_pct']
    total_dp_val = (selling_price * (dp_pct / 100))
    dp_after_booking = max(0, total_dp_val - res_fee)
    dp_months = settings['dp_months']
    
    if dp_pct > 0:
        if dp_months > 1:
            for i in range(dp_months):
                d = start_date + relativedelta(months=i)
                plan.append({"Milestone": f"DP Installment {i+1}", "Date": d.strftime("%b-%y"), "Percent": f"{(dp_pct/dp_months):.1f}%", "Amount": dp_after_booking / dp_months})
        else:
            plan.append({"Milestone": "DP Balance Payment", "Date": start_date.strftime("%b-%y"), "Percent": f"{dp_pct}%", "Amount": dp_after_booking})
    
    if plan_cfg.get("is_special"):
        special_rec_date = start_date + relativedelta(months=12)
        plan.append({"Milestone": "Special Installment (10%)", "Date": special_rec_date.strftime("%b-%y"), "Percent": "10%", "Amount": selling_price * 0.10})
    
    monthly_pct = settings['monthly_pct'] / 100
    curr_d = start_date + relativedelta(months=max(1, dp_months))
    while curr_d < handover_date:
        if settings['recovery_freq'] > 0:
            m_diff = (curr_d.year - start_date.year) * 12 + curr_d.month - start_date.month
            if m_diff > 0 and m_diff % settings['recovery_freq'] == 0:
                plan.append({"Milestone": "Recovery Payment", "Date": curr_d.strftime("%b-%y"), "Percent": f"{settings['recovery_pct']}%", "Amount": selling_price * (settings['recovery_pct'] / 100)})
        
        amt = selling_price * monthly_pct
        if amt > 0:
            plan.append({"Milestone": "Monthly Installment", "Date": curr_d.strftime("%b-%y"), "Percent": f"{settings['monthly_pct']}%", "Amount": amt})
        curr_d += relativedelta(months=1)
    
    total_inst = sum(item['Amount'] for item in plan)
    plan.append({"Milestone": "TOTAL INSTALLMENT", "Date": "---", "Percent": "---", "Amount": total_inst})
    
    handover_amt = selling_price - total_inst
    if handover_amt > 1:
        plan.append({"Milestone": "Balance Handover", "Date": handover_date.strftime("%b-%y"), "Percent": "Balance", "Amount": handover_amt})
    return plan

# --- واجهة Streamlit ---
st.set_page_config(page_title="Reportage Smart Agent", layout="wide")
st.title("🏗️ Reportage Sales AI")

with st.sidebar:
    st.header("🏢 Settings")
    selected_project = st.selectbox("Project:", list(PROJECTS_DATABASE.keys()))
    proj_info = PROJECTS_DATABASE[selected_project]
    
    df_inventory = load_google_sheet(proj_info["url"])
    df_photos = load_google_sheet(PHOTO_BANK_URL)
    
    selected_plan = st.selectbox("Plan:", list(ALL_PLANS.keys()))
    default_m_pct = ALL_PLANS[selected_plan].get("default_monthly", 1.0)
    extra_disc = st.number_input("Extra Discount %", 0.0, 15.0, 0.0)
    
    st.subheader("Structure")
    m_pct = st.number_input("Monthly %", 0.0, 5.0, float(default_m_pct))
    dp_m = st.number_input("DP Split (Months):", 1, 24, 1)
    r_freq = st.selectbox("Recovery (Months):", [0, 6, 12])
    r_pct = st.number_input("Recovery %", 0.0, 20.0, 0.0)

if df_inventory is not None:
    # التأكد من وجود عمود Unit No
    unit_col = 'Plot + Unit No.' if 'Plot + Unit No.' in df_inventory.columns else df_inventory.columns[0]
    unit_id = st.selectbox("Select Unit:", df_inventory[unit_col].unique())
    unit_data = df_inventory[df_inventory[unit_col] == unit_id].iloc[0]
    
    h_date = get_handover_date(unit_data)
    
    # حساب الحسابات المالية
    orig_price = clean_num(unit_data.get('Original Price (AED)', 0))
    parking = clean_num(unit_data.get('parking', 0))
    total_disc_pct = ALL_PLANS[selected_plan]['disc'] + extra_disc
    
    selling_price = (orig_price * (1 - total_disc_pct/100)) + parking
    gov_fees = (selling_price * (proj_info["gov_pct"] / 100)) + proj_info["admin_fees"]
    
    financials = {
        'u_price': orig_price, 'disc_pct': total_disc_pct, 
        'disc_val': orig_price * (total_disc_pct/100), 
        'selling_price': selling_price, 'gov_fees': gov_fees
    }
    
    settings = {'dp_months': dp_m, 'monthly_pct': m_pct, 'recovery_freq': r_freq, 'recovery_pct': r_pct}
    schedule = calculate_ultra_flexible_plan(selling_price, ALL_PLANS[selected_plan], settings, date.today(), h_date, proj_info["res_fee"])
    
    # --- البحث الذكي عن الصور ---
    layout_url = None
    if df_photos is not None:
        try:
            p_key = selected_project.split()[0].upper()
            unit_bed = str(unit_data.get('Bedrooms', '')).replace('.0', '').strip()
            
            # فلترة ذكية
            match = df_photos[
                (df_photos['Project'].astype(str).str.upper().str.contains(p_key)) & 
                (df_photos['Bedrooms'].astype(str).str.contains(unit_bed))
            ]
            if not match.empty:
                layout_url = match.iloc[0]['Layout_URL']
        except: layout_url = None

    # العرض
    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("Selling Price", f"{selling_price:,.2f} AED")
    col2.metric("Gov. Fees", f"{gov_fees:,.2f} AED")
    col3.metric("Total Amount", f"{selling_price + gov_fees:,.2f} AED")
    
    st.subheader("📊 Payment Schedule")
    st.table(pd.DataFrame(schedule).assign(Amount=lambda x: x['Amount'].map('{:,.2f}'.format)))

    if layout_url:
        st.image(layout_url, caption=f"Layout for {unit_id}", use_container_width=True)
else:
    st.error("Could not load inventory. Please check the Google Sheet URL.")

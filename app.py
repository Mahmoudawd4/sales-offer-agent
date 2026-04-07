import streamlit as st
import pandas as pd
from fpdf import FPDF
import requests
from io import BytesIO
from datetime import date
from dateutil.relativedelta import relativedelta

# --- 1. قاعدة بيانات الروابط ---
PROJECTS_DATABASE = {
    "SILA MASDAR": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=0&single=true&output=csv",
    "KHALIFA CITY": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1491192679&single=true&output=csv"
}

PHOTO_BANK_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1714647206&single=true&output=csv"
LOGO_URL = "https://i.ibb.co/3sbsK2S/Reportage-Logo.png" 

# --- 2. قاموس الخطط المحدث بالإضافات الجديدة ---
ALL_PLANS = {
    "10% DP / 10% Disc / 1% Monthly": {"dp_pct": 10, "disc": 10, "default_monthly": 1.0},
    "20% DP / 10% Disc / 1% Monthly": {"dp_pct": 20, "disc": 10, "default_monthly": 1.0},
    "30% DP / 15% Disc / 1% Monthly": {"dp_pct": 30, "disc": 15, "default_monthly": 1.0},
    "20% DP / 2% Disc / 10%@12m / 70% HO": {"dp_pct": 20, "disc": 2, "default_monthly": 0.0, "is_special": True},
    "25% Discount Cash": {"dp_pct": 100, "disc": 25, "default_monthly": 0.0},
    "30% Discount Cash": {"dp_pct": 100, "disc": 30, "default_monthly": 0.0},
    "18% Discount Cash": {"dp_pct": 100, "disc": 18, "default_monthly": 0.0},
    "No discount (Full in 1 month)": {"dp_pct": 100, "disc": 0, "default_monthly": 0.0},
    "0% DP / 0% Disc / 1% Monthly": {"dp_pct": 0, "disc": 0, "default_monthly": 1.0},
    "Plan 12 (Cash 40% Disc)": {"dp_pct": 100, "disc": 40, "default_monthly": 0.0}
}

@st.cache_data
def load_google_sheet(url):
    try:
        df = pd.read_csv(url)
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return df
    except Exception as e:
        return None

def calculate_ultra_flexible_plan(selling_price, plan_cfg, settings, start_date, handover_date):
    plan = []
    res_fee = 20000
    plan.append({"Milestone": "Reservation Fee (Booking)", "Date": "Now", "Percent": "-", "Amount": res_fee})
    
    dp_pct = plan_cfg['dp_pct']
    # حساب قيمة الـ DP الكلية ثم طرح الحجز منها
    total_dp_val = (selling_price * (dp_pct / 100))
    dp_after_booking = max(0, total_dp_val - res_fee)
    
    dp_months = settings['dp_months']
    
    # توزيع الدفعة المقدمة
    if dp_pct > 0:
        if dp_months > 1:
            for i in range(dp_months):
                d = start_date + relativedelta(months=i)
                plan.append({"Milestone": f"DP Installment {i+1}", "Date": d.strftime("%b-%y"), "Percent": f"{(dp_pct/dp_months):.1f}%", "Amount": dp_after_booking / dp_months})
        else:
            plan.append({"Milestone": "DP Balance Payment", "Date": start_date.strftime("%b-%y"), "Percent": f"{dp_pct}%", "Amount": dp_after_booking})

    # معالجة خطة الـ 70% الخاصة (10% بعد سنة)
    if plan_cfg.get("is_special"):
        special_rec_date = start_date + relativedelta(months=12)
        plan.append({"Milestone": "Special Installment (10%)", "Date": special_rec_date.strftime("%b-%y"), "Percent": "10%", "Amount": selling_price * 0.10})

    # الأقساط الشهرية العادية
    monthly_pct = settings['monthly_pct'] / 100
    curr_d = start_date + relativedelta(months=max(1, dp_months))
    
    while curr_d < handover_date:
        # Recovery Payments
        if settings['recovery_freq'] > 0:
            m_diff = (curr_d.year - start_date.year) * 12 + curr_d.month - start_date.month
            if m_diff > 0 and m_diff % settings['recovery_freq'] == 0:
                plan.append({"Milestone": "Recovery Payment", "Date": curr_d.strftime("%b-%y"), "Percent": f"{settings['recovery_pct']}%", "Amount": selling_price * (settings['recovery_pct'] / 100)})
        
        # Monthly
        amt = selling_price * monthly_pct
        if amt > 0:
            plan.append({"Milestone": "Monthly Installment", "Date": curr_d.strftime("%b-%y"), "Percent": f"{settings['monthly_pct']}%", "Amount": amt})
        curr_d += relativedelta(months=1)

    # --- إضافة صف إجمالي الأقساط قبل الاستلام ---
    total_installments = sum(item['Amount'] for item in plan)
    plan.append({"Milestone": "TOTAL INSTALLMENT", "Date": "---", "Percent": "---", "Amount": total_installments})

    # دفعة الاستلام
    handover_amt = selling_price - total_installments
    if handover_amt > 1:
        plan.append({"Milestone": "Balance Handover", "Date": handover_date.strftime("%b-%y"), "Percent": "Balance", "Amount": handover_amt})
    
    return plan

def create_sales_offer_pdf(unit_data, financials, schedule, layout_url, plan_name, project_name):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image(LOGO_URL, x=10, y=8, w=35)
    except: pass
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 15, f"SALES OFFER - {project_name}", ln=True, align='C')
    pdf.ln(5)

    # ... (بقية كود الـ PDF كما هو لضمان الصور والمواصفات) ...
    if layout_url and str(layout_url) != 'nan':
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(layout_url, headers=headers, timeout=10)
            img_data = BytesIO(response.content)
            pdf.image(img_data, x=135, y=35, w=60)
        except: pass

    pdf.set_xy(10, 35)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(110, 8, " UNIT SPECIFICATIONS", 0, 1, 'L', True)
    pdf.set_font("Arial", size=10); pdf.set_text_color(0)
    specs = [
        f"Unit No: {unit_data.get('Plot + Unit No.', 'N/A')}",
        f"Unit Type: {unit_data.get('UNIT TYPE', 'N/A')}",
        f"Bedrooms: {unit_data.get('Bedrooms', 'N/A')}",
        f"Sub-type: {unit_data.get('Sub-type', 'N/A')}",
        f"Total Area: {unit_data.get('Total Area (Sq.ft)', '0')} SQFT",
        f"View: {unit_data.get('View', 'N/A')}"
    ]
    for spec in specs: pdf.cell(110, 6, f" {spec}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11); pdf.set_fill_color(240, 240, 240)
    pdf.cell(110, 8, f" FINANCIAL SUMMARY - {plan_name}", 0, 1, 'L', True)
    pdf.set_font("Arial", size=10)
    pdf.cell(60, 6, "Original Price:", 0); pdf.cell(50, 6, f"{financials['u_price']:,.2f} AED", 0, 1, 'R')
    pdf.cell(60, 6, f"Discount ({financials['disc_pct']}%):", 0); pdf.cell(50, 6, f"- {financials['disc_val']:,.2f} AED", 0, 1, 'R')
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(60, 8, "Total Selling Price:", 0); pdf.cell(50, 8, f"{financials['selling_price']:,.2f} AED", 0, 1, 'R')
    
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(44, 62, 80); pdf.set_text_color(255, 255, 255)
    pdf.cell(60, 10, " Milestone", 1, 0, 'L', True); pdf.cell(40, 10, " Date", 1, 0, 'C', True)
    pdf.cell(30, 10, " %", 1, 0, 'C', True); pdf.cell(60, 10, " Amount (AED)", 1, 1, 'R', True)

    pdf.set_text_color(0); pdf.set_font("Arial", size=9)
    for row in schedule:
        # تمييز صف الإجمالي في الـ PDF
        if row['Milestone'] == "TOTAL INSTALLMENT":
            pdf.set_font("Arial", 'B', 9); pdf.set_fill_color(220, 220, 220)
            pdf.cell(60, 8, f" {row['Milestone']}", 1, 0, 'L', True)
            pdf.cell(40, 8, f" {row['Date']}", 1, 0, 'C', True)
            pdf.cell(30, 8, f" {row['Percent']}", 1, 0, 'C', True)
            pdf.cell(60, 8, f"{row['Amount']:,.2f} ", 1, 1, 'R', True)
            pdf.set_font("Arial", size=9); pdf.set_fill_color(255, 255, 255)
        else:
            pdf.cell(60, 8, f" {row['Milestone']}", 1)
            pdf.cell(40, 8, f" {row['Date']}", 1, 0, 'C')
            pdf.cell(30, 8, f" {row['Percent']}", 1, 0, 'C')
            pdf.cell(60, 8, f"{row['Amount']:,.2f} ", 1, 1, 'R')
            
    return pdf.output(dest='S')

# --- واجهة التطبيق ---
st.set_page_config(page_title="Reportage Smart Agent", layout="wide")
st.title("🏗️ Reportage Sales AI")

with st.sidebar:
    st.header("🏢 Settings")
    selected_project = st.selectbox("Project:", list(PROJECTS_DATABASE.keys()))
    df_inventory = load_google_sheet(PROJECTS_DATABASE[selected_project])
    df_photos = load_google_sheet(PHOTO_BANK_URL)
    
    selected_plan = st.selectbox("Plan:", list(ALL_PLANS.keys()))
    default_m_pct = ALL_PLANS[selected_plan].get("default_monthly", 1.0)
    extra_disc = st.number_input("Extra Discount %", 0.0, 15.0, 0.0)
    
    st.subheader("Structure")
    m_pct = st.number_input("Monthly %", 0.0, 5.0, default_m_pct)
    dp_m = st.number_input("DP Split (Months):", 1, 24, 1)
    r_freq = st.selectbox("Recovery (Months):", [0, 6, 12])
    r_pct = st.number_input("Recovery %", 0.0, 20.0, 0.0)

if df_inventory is not None:
    unit_id = st.selectbox("Unit:", df_inventory['Plot + Unit No.'].unique())
    unit_data = df_inventory[df_inventory['Plot + Unit No.'] == unit_id].iloc[0]

    # الحسابات
    u_price = float(str(unit_data.get('Original Price (AED)', '0')).replace(',', ''))
    total_disc_pct = ALL_PLANS[selected_plan]['disc'] + extra_disc
    selling_price = (u_price * (1 - total_disc_pct/100)) + float(str(unit_data.get('parking', '0')).replace(',', ''))
    
    # التواريخ
    try: handover_finish_date = pd.to_datetime(unit_data.get('Handover Date', '2029-09-01')).date()
    except: handover_finish_date = date(2029, 9, 1)

    financials = {'u_price': u_price, 'disc_pct': total_disc_pct, 'disc_val': u_price * (total_disc_pct/100), 'parking': 0, 'selling_price': selling_price}
    settings = {'dp_months': dp_m, 'monthly_pct': m_pct, 'recovery_freq': r_freq, 'recovery_pct': r_pct}
    
    schedule = calculate_ultra_flexible_plan(selling_price, ALL_PLANS[selected_plan], settings, date.today(), handover_finish_date)

    # البحث عن الصورة
    try:
        p_key = selected_project.split()[0].upper()
        match = df_photos[(df_photos['Project'].astype(str).str.upper().str.contains(p_key)) & 
                          (df_photos['Bedrooms'].astype(str) == str(unit_data['Bedrooms'])) & 
                          (df_photos['Sub-type'].astype(str) == str(unit_data['Sub-type']))]
        layout_url = match.iloc[0]['Layout_URL'] if not match.empty else None
    except: layout_url = None

    # العرض
    st.divider()
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader(f"📊 Unit {unit_id} - {selected_plan}")
        # تمييز صف الإجمالي في الجدول المعروض
        st.dataframe(pd.DataFrame(schedule).style.format({"Amount": "{:,.2f}"}), use_container_width=True)
    
    with c2:
        if layout_url: st.image(layout_url, use_container_width=True)
        st.metric("Final Selling Price", f"{selling_price:,.2f} AED")
        pdf_bytes = create_sales_offer_pdf(unit_data, financials, schedule, layout_url, selected_plan, selected_project)
        st.download_button("Download PDF", data=bytes(pdf_bytes), file_name=f"Offer_{unit_id}.pdf", use_container_width=True)

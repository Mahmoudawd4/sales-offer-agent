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

# --- 2. قاموس الخطط المحدث بالإضافات المطلوبة ---
ALL_PLANS = {
    "10% DP / 10% Disc / 1% Monthly": {"dp_pct": 10, "disc": 10, "default_monthly": 1.0},
    "20% DP / 10% Disc / 1% Monthly": {"dp_pct": 20, "disc": 10, "default_monthly": 1.0},
    "30% DP / 15% Disc / 1% Monthly": {"dp_pct": 30, "disc": 15, "default_monthly": 1.0},
    "20% DP / 2% Disc / 10% @12m / 70% HO": {"dp_pct": 20, "disc": 2, "default_monthly": 0.0, "special_recovery": 10},
    "18% Discount Cash": {"dp_pct": 100, "disc": 18, "default_monthly": 0.0, "is_cash": True},
    "25% Discount Cash": {"dp_pct": 100, "disc": 25, "default_monthly": 0.0, "is_cash": True},
    "30% Discount Cash": {"dp_pct": 100, "disc": 30, "default_monthly": 0.0, "is_cash": True},
    "No Discount - Full within month": {"dp_pct": 100, "disc": 0, "default_monthly": 0.0, "is_cash": True},
    "Plan A (5% DP / 5% Disc)": {"dp_pct": 5, "disc": 5, "default_monthly": 1.0},
}

@st.cache_data
def load_google_sheet(url):
    try:
        df = pd.read_csv(url)
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return df
    except: return None

# --- 3. دالة الحسابات المتطورة ---
def calculate_ultra_flexible_plan(selling_price, plan_cfg, settings, start_date, handover_date):
    plan = []
    res_fee = 20000
    plan.append({"Milestone": "Reservation Fee", "Date": "Now", "Percent": "-", "Amount": res_fee})
    
    dp_pct = plan_cfg['dp_pct']
    total_dp_val = (selling_price * (dp_pct / 100))
    remaining_dp = total_dp_val - res_fee
    dp_months = settings['dp_months']
    
    if dp_pct > 0:
        for i in range(dp_months):
            d = start_date + relativedelta(months=i)
            plan.append({"Milestone": f"DP Installment {i+1}", "Date": d.strftime("%b-%y"), "Percent": f"{(dp_pct/dp_months):.1f}%", "Amount": max(0, remaining_dp / dp_months)})

    if "special_recovery" in plan_cfg:
        rec_date = start_date + relativedelta(months=12)
        plan.append({"Milestone": "Payment after 12 Months", "Date": rec_date.strftime("%b-%y"), "Percent": "10%", "Amount": selling_price * 0.10})

    if not plan_cfg.get("is_cash", False) and settings['monthly_pct'] > 0:
        monthly_pct = settings['monthly_pct'] / 100
        curr_d = start_date + relativedelta(months=max(1, dp_months))
        while curr_d < handover_date:
            amt = selling_price * monthly_pct
            plan.append({"Milestone": "Monthly Installment", "Date": curr_d.strftime("%b-%y"), "Percent": f"{settings['monthly_pct']}%", "Amount": amt})
            curr_d += relativedelta(months=1)

    # إضافة سطر الإجمالي قبل دفعة الاستلام
    total_inst = sum(item['Amount'] for item in plan)
    plan.append({"Milestone": "TOTAL INSTALLMENT", "Date": "Pre-Handover", "Percent": "-", "Amount": total_inst})

    handover_amt = selling_price - total_inst
    if handover_amt > 1:
        plan.append({"Milestone": "Final Handover / Balance", "Date": handover_date.strftime("%b-%y"), "Percent": "Balance", "Amount": handover_amt})
    
    return plan

# --- 4. دالة إنشاء الـ PDF ---
def create_sales_offer_pdf(unit_data, financials, schedule, layout_url, plan_name, project_name):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image(LOGO_URL, x=10, y=8, w=35)
    except: pass
    
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 15, f"SALES OFFER - {project_name}", ln=True, align='C')
    
    # تفاصيل الوحدة (Specifications)
    pdf.set_xy(10, 35)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(110, 8, " UNIT SPECIFICATIONS", 0, 1, 'L', True)
    pdf.set_font("Arial", size=10)
    specs = [
        f"Unit No: {unit_data.get('Plot + Unit No.', 'N/A')}",
        f"Unit Type: {unit_data.get('UNIT TYPE', 'N/A')}",
        f"Bedrooms: {unit_data.get('Bedrooms', 'N/A')}",
        f"Sub-type: {unit_data.get('Sub-type', 'N/A')}",
        f"Total Area: {unit_data.get('Total Area (Sq.ft)', '0')} SQFT",
        f"View: {unit_data.get('View', 'N/A')}"
    ]
    for spec in specs: pdf.cell(110, 6, f" {spec}", ln=True)

    # الملخص المالي
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11); pdf.set_fill_color(240, 240, 240)
    pdf.cell(110, 8, f" FINANCIAL SUMMARY - {plan_name}", 0, 1, 'L', True)
    pdf.set_font("Arial", size=10)
    pdf.cell(60, 6, "Original Price:"); pdf.cell(50, 6, f"{financials['u_price']:,.2f} AED", ln=True, align='R')
    pdf.cell(60, 6, f"Discount ({financials['disc_pct']}%):"); pdf.cell(50, 6, f"- {financials['disc_val']:,.2f} AED", ln=True, align='R')
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(60, 8, "Total Selling Price:"); pdf.cell(50, 8, f"{financials['selling_price']:,.2f} AED", ln=True, align='R')

    # إضافة الصورة إذا وجدت
    if layout_url:
        try:
            res = requests.get(layout_url, timeout=5)
            img = BytesIO(res.content)
            pdf.image(img, x=130, y=35, w=70)
        except: pass

    # جدول الأقساط
    pdf.ln(10)
    pdf.set_fill_color(44, 62, 80); pdf.set_text_color(255, 255, 255)
    pdf.cell(60, 10, " Milestone", 1, 0, 'L', True)
    pdf.cell(35, 10, " Date", 1, 0, 'C', True)
    pdf.cell(25, 10, " %", 1, 0, 'C', True)
    pdf.cell(50, 10, " Amount", 1, 1, 'R', True)
    
    pdf.set_text_color(0); pdf.set_font("Arial", size=9)
    for row in schedule:
        fill = row['Milestone'] == "TOTAL INSTALLMENT"
        if fill: pdf.set_fill_color(230, 230, 230)
        pdf.cell(60, 8, row['Milestone'], 1, 0, 'L', fill)
        pdf.cell(35, 8, row['Date'], 1, 0, 'C', fill)
        pdf.cell(25, 8, row['Percent'], 1, 0, 'C', fill)
        pdf.cell(50, 8, f"{row['Amount']:,.2f}", 1, 1, 'R', fill)

    return pdf.output(dest='S')

# --- 5. واجهة التطبيق ---
st.set_page_config(layout="wide", page_title="Reportage Agent")
st.title("🏗️ Reportage Sales Pro")

with st.sidebar:
    selected_project = st.selectbox("Project:", list(PROJECTS_DATABASE.keys()))
    df_inv = load_google_sheet(PROJECTS_DATABASE[selected_project])
    df_photos = load_google_sheet(PHOTO_BANK_URL)
    
    selected_plan = st.selectbox("Plan:", list(ALL_PLANS.keys()))
    extra_disc = st.number_input("Extra Disc %", 0.0, 15.0, 0.0)
    m_pct = st.number_input("Monthly %", 0.0, 5.0, float(ALL_PLANS[selected_plan]['default_monthly']))
    dp_m = st.number_input("DP Split (Months)", 1, 24, 1)

if df_inv is not None:
    unit_id = st.selectbox("Unit:", df_inv['Plot + Unit No.'].unique())
    unit_data = df_inv[df_inv['Plot + Unit No.'] == unit_id].iloc[0]

    # الحسابات
    u_price = float(str(unit_data.get('Original Price (AED)', '0')).replace(',', ''))
    parking = float(str(unit_data.get('parking', '0')).replace(',', ''))
    total_disc = ALL_PLANS[selected_plan]['disc'] + extra_disc
    disc_val = u_price * (total_disc/100)
    selling_price = (u_price - disc_val) + parking

    h_date_str = str(unit_data.get('Handover Date', '2029-09-01'))
    try: h_date = pd.to_datetime(h_date_str).date()
    except: h_date = date(2029, 9, 1)

    financials = {'u_price': u_price, 'disc_pct': total_disc, 'disc_val': disc_val, 'selling_price': selling_price}
    schedule = calculate_ultra_flexible_plan(selling_price, ALL_PLANS[selected_plan], {'dp_months': dp_m, 'monthly_pct': m_pct}, date.today(), h_date)

    # البحث عن الصورة
    try:
        p_key = selected_project.split()[0].upper()
        match = df_photos[(df_photos['Project'].str.upper().str.contains(p_key)) & 
                          (df_photos['Bedrooms'].astype(str) == str(unit_data['Bedrooms'])) & 
                          (df_photos['Sub-type'].astype(str) == str(unit_data['Sub-type']))]
        layout_url = match.iloc[0]['Layout_URL'] if not match.empty else None
    except: layout_url = None

    # العرض
    st.divider()
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Unit Details")
        st.write(f"**Bedrooms:** {unit_data['Bedrooms']} | **Type:** {unit_data['UNIT TYPE']} | **View:** {unit_data['View']}")
        st.table(pd.DataFrame(schedule).style.format({"Amount": "{:,.2f}"}))
    
    with col2:
        if layout_url: st.image(layout_url, caption="Unit Layout")
        st.metric("Total Selling Price", f"{selling_price:,.2f} AED")
        pdf_bytes = create_sales_offer_pdf(unit_data, financials, schedule, layout_url, selected_plan, selected_project)
        st.download_button("Download PDF", data=bytes(pdf_bytes), file_name=f"Offer_{unit_id}.pdf")

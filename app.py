import streamlit as st
import pandas as pd
from fpdf import FPDF
import requests
from io import BytesIO
from datetime import date
from dateutil.relativedelta import relativedelta

# --- قاعدة بيانات الروابط ---
PROJECTS_DATABASE = {
    "SILA MASDAR": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=0&single=true&output=csv",
    "KHALIFA CITY": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1491192679&single=true&output=csv"
}

PHOTO_BANK_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1714647206&single=true&output=csv"
LOGO_URL = "https://i.ibb.co/3sbsK2S/Reportage-Logo.png" 

# --- خطط الدفع ---
ALL_PLANS = {
    "Plan A (5% DP / 5% Disc)": {"dp_pct": 5, "disc": 5},
    "Plan 2 (10% DP / 5% Disc)": {"dp_pct": 10, "disc": 5},
    "Plan 7 (20% DP / 15% Disc)": {"dp_pct": 20, "disc": 15},
    "Plan 11 (30% DP / 5% Disc)": {"dp_pct": 30, "disc": 5},
    "Plan 12 (Cash 40% Disc)": {"dp_pct": 100, "disc": 40},
    "Plan 15 (20/80)": {"dp_pct": 20, "disc": 0}
}

@st.cache_data
def load_google_sheet(url):
    try:
        df = pd.read_csv(url)
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return df
    except: return None

def calculate_plan(selling_price, plan_cfg, settings, start_date, handover_date):
    plan = []
    res_fee = 20000
    plan.append({"Milestone": "Reservation Fee", "Date": "Now", "Percent": "-", "Amount": res_fee})
    
    dp_pct = plan_cfg['dp_pct']
    dp_val = (selling_price * (dp_pct / 100)) - res_fee
    
    # تقسيم الدفعة الأولى
    dp_m = settings['dp_months']
    for i in range(dp_m):
        d = start_date + relativedelta(months=i)
        plan.append({"Milestone": f"DP Installment {i+1}", "Date": d.strftime("%b-%y"), "Percent": f"{(dp_pct/dp_m):.1f}%", "Amount": dp_val / dp_m})

    # الأقساط الشهرية حتى تاريخ التسليم
    curr_d = start_date + relativedelta(months=max(1, dp_m))
    monthly_pct = settings['monthly_pct'] / 100
    
    while curr_d < handover_date:
        amt = selling_price * monthly_pct
        if amt > 0:
            plan.append({"Milestone": "Monthly Installment", "Date": curr_d.strftime("%b-%y"), "Percent": f"{settings['monthly_pct']}%", "Amount": amt})
        curr_d += relativedelta(months=1)

    total_paid = sum(item['Amount'] for item in plan)
    handover_amt = selling_price - total_paid
    if handover_amt > 1:
        plan.append({"Milestone": "Handover Payment", "Date": handover_date.strftime("%b-%y"), "Percent": "Balance", "Amount": handover_amt})
    return plan

def create_pdf(unit_data, financials, schedule, layout_url, plan_name, project_name):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image(LOGO_URL, x=10, y=8, w=35)
    except: pass

    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 15, f"OFFICIAL OFFER: {project_name}", ln=True, align='C')
    
    if layout_url:
        try:
            res = requests.get(layout_url, timeout=5)
            img = BytesIO(res.content)
            pdf.image(img, x=140, y=35, w=55)
        except: pass

    pdf.set_xy(10, 35)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(110, 8, " UNIT DETAILS", 1, 1, 'L')
    pdf.set_font("Arial", size=10)
    pdf.cell(110, 6, f"Unit No: {unit_data.get('Plot + Unit No.', 'N/A')}", 0, 1)
    pdf.cell(110, 6, f"Type: {unit_data.get('Bedrooms', 'N/A')} - {unit_data.get('Sub-type', 'N/A')}", 0, 1)
    pdf.cell(110, 6, f"Area: {unit_data.get('Total Area (Sq.ft)', '0')} SQFT", 0, 1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(110, 8, " FINANCIAL SUMMARY", 1, 1, 'L')
    pdf.set_font("Arial", size=10)
    pdf.cell(60, 6, "Selling Price:", 0)
    pdf.cell(50, 6, f"{financials['selling_price']:,.2f} AED", 0, 1, 'R')
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(60, 10, " Milestone", 1); pdf.cell(40, 10, " Date", 1); pdf.cell(60, 10, " Amount", 1, 1)
    for row in schedule:
        pdf.cell(60, 8, row['Milestone'], 1)
        pdf.cell(40, 8, str(row['Date']), 1)
        pdf.cell(60, 8, f"{row['Amount']:,.2f}", 1, 1, 'R')
    
    return pdf.output(dest='S')

# --- الواجهة الرئيسية ---
st.set_page_config(layout="wide")
st.title("🚀 Multi-Project Sales Agent")

with st.sidebar:
    st.header("Select Project")
    selected_proj = st.selectbox("Project:", list(PROJECTS_DATABASE.keys()))
    df_inv = load_google_sheet(PROJECTS_DATABASE[selected_proj])
    df_photos = load_google_sheet(PHOTO_BANK_URL)
    
    st.divider()
    sel_plan = st.selectbox("Payment Plan:", list(ALL_PLANS.keys()))
    m_pct = st.number_input("Monthly %", 0.0, 5.0, 1.0)
    dp_m = st.number_input("DP Split (Months)", 1, 12, 1)

if df_inv is not None:
    unit_id = st.selectbox("Unit No:", df_inv['Plot + Unit No.'].unique())
    unit_data = df_inv[df_inv['Plot + Unit No.'] == unit_id].iloc[0]

    # جلب الإعدادات من الشيت
    parking = float(str(unit_data.get('parking', '0')).replace(',', ''))
    h_date_str = str(unit_data.get('Handover Date', '2029-09-01'))
    h_date = pd.to_datetime(h_date_str).date()

    # الحسابات
    u_price = float(str(unit_data['Original Price (AED)']).replace(',', ''))
    disc_pct = ALL_PLANS[sel_plan]['disc']
    selling_price = (u_price * (1 - disc_pct/100)) + parking
    
    # البحث عن الصورة
    match = df_photos[(df_photos['Project'] == selected_proj) & 
                      (df_photos['Bedrooms'].astype(str) == str(unit_data['Bedrooms'])) & 
                      (df_photos['Sub-type'] == unit_data['Sub-type'])]
    l_url = match.iloc[0]['Layout_URL'] if not match.empty else None

    # العرض
    col1, col2 = st.columns([2,1])
    with col1:
        st.subheader(f"Offer for {selected_proj} - {unit_id}")
        sched = calculate_plan(selling_price, ALL_PLANS[sel_plan], {'dp_months': dp_m, 'monthly_pct': m_pct}, date.today(), h_date)
        st.table(pd.DataFrame(sched))
    
    with col2:
        if l_url: st.image(l_url, caption="Unit Layout")
        financials = {'selling_price': selling_price, 'parking': parking}
        if st.button("Generate PDF"):
            pdf_out = create_pdf(unit_data, financials, sched, l_url, sel_plan, selected_proj)
            st.download_button("Download Offer", data=bytes(pdf_out), file_name=f"{selected_proj}_{unit_id}.pdf")

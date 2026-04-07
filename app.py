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

# --- 2. قاموس الخطط المحدث كلياً ---
ALL_PLANS = {
    "10% DP / 10% Disc / 1% Monthly": {"dp_pct": 10, "disc": 10, "type": "standard"},
    "20% DP / 10% Disc / 1% Monthly": {"dp_pct": 20, "disc": 10, "type": "standard"},
    "30% DP / 15% Disc / 1% Monthly": {"dp_pct": 30, "disc": 15, "type": "standard"},
    "0% DP / 0% Disc / 1% Monthly": {"dp_pct": 0, "disc": 0, "type": "standard"},
    "20% DP / 2% Disc / 10% @12m / 70% HO": {"dp_pct": 20, "disc": 2, "type": "special", "recovery_at_12": 10, "ho_pct": 70},
    "25% Discount Cash": {"dp_pct": 100, "disc": 25, "type": "cash"},
    "30% Discount Cash": {"dp_pct": 100, "disc": 30, "type": "cash"},
    "18% Discount Cash": {"dp_pct": 100, "disc": 18, "type": "cash"},
    "No Discount - Full within month": {"dp_pct": 100, "disc": 0, "type": "cash"}
}

@st.cache_data
def load_google_sheet(url):
    try:
        df = pd.read_csv(url)
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return df
    except: return None

# --- 3. دالة الحسابات المالية (خصم Booking وحساب الإجمالي) ---
def calculate_plan_v3(selling_price, plan_cfg, settings, start_date, handover_date):
    plan = []
    booking_fee = 20000
    plan.append({"Milestone": "Booking Fee", "Date": "Now", "Percent": "-", "Amount": booking_fee})
    
    dp_pct = plan_cfg['dp_pct']
    total_dp_needed = (selling_price * (dp_pct / 100))
    remaining_dp = total_dp_needed - booking_fee
    dp_months = settings['dp_months']
    
    # توزيع الـ DP المتبقي
    if remaining_dp > 0:
        for i in range(dp_months):
            d = start_date + relativedelta(months=i)
            plan.append({"Milestone": f"DP Installment {i+1}", "Date": d.strftime("%b-%y"), "Percent": f"{(dp_pct/dp_months):.1f}%", "Amount": remaining_dp / dp_months})
    elif total_dp_needed > 0 and remaining_dp <= 0:
        # إذا كان الـ DP المطلوب أصغر من أو يساوي الـ 20 ألف (يتم تعديل الـ Booking ليساوي الـ DP)
        plan[0]["Amount"] = total_dp_needed

    if plan_cfg.get("type") == "special":
        # خطة الـ 70% عند الاستلام
        rec_date = start_date + relativedelta(months=12)
        plan.append({"Milestone": "Payment after 12 Months", "Date": rec_date.strftime("%b-%y"), "Percent": f"{plan_cfg['recovery_at_12']}%", "Amount": selling_price * (plan_cfg['recovery_at_12'] / 100)})
        plan.append({"Milestone": "Handover Payment", "Date": handover_date.strftime("%b-%y"), "Percent": f"{plan_cfg['ho_pct']}%", "Amount": selling_price * (plan_cfg['ho_pct'] / 100)})
    
    elif plan_cfg.get("type") == "cash":
        # خطط الكاش (الباقي بعد شهر)
        total_paid = sum(item['Amount'] for item in plan)
        plan.append({"Milestone": "Final Settlement", "Date": (start_date + relativedelta(months=1)).strftime("%b-%y"), "Percent": "Balance", "Amount": selling_price - total_paid})
    
    else:
        # الخطط الشهرية العادية
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

        total_paid_so_far = sum(item['Amount'] for item in plan)
        if (selling_price - total_paid_so_far) > 1:
            plan.append({"Milestone": "Final Handover", "Date": handover_date.strftime("%b-%y"), "Percent": "Balance", "Amount": selling_price - total_paid_so_far})

    return plan

# --- 4. دالة إنشاء PDF ---
def create_pdf(unit_data, financials, schedule, layout_url, plan_name, project_name):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image(LOGO_URL, x=10, y=8, w=35)
    except: pass
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 15, f"OFFICIAL OFFER - {project_name}", ln=True, align='C')
    
    if layout_url:
        try:
            res = requests.get(layout_url, timeout=5)
            pdf.image(BytesIO(res.content), x=135, y=35, w=60)
        except: pass

    pdf.set_xy(10, 35)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(110, 8, " UNIT DETAILS", 1, 1, 'L')
    pdf.set_font("Arial", size=10)
    pdf.cell(110, 6, f"Unit: {unit_data.get('Plot + Unit No.', 'N/A')}", 0, 1)
    pdf.cell(110, 6, f"Type: {unit_data.get('Bedrooms', 'N/A')} - {unit_data.get('Sub-type', 'N/A')}", 0, 1)
    pdf.cell(110, 6, f"Total Area: {unit_data.get('Total Area (Sq.ft)', '0')} SQFT", 0, 1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(110, 8, f" FINANCIALS - {plan_name}", 1, 1, 'L')
    pdf.set_font("Arial", size=10)
    pdf.cell(60, 6, "Selling Price:", 0); pdf.cell(50, 6, f"{financials['selling_price']:,.2f} AED", 0, 1, 'R')
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(60, 8, " Milestone", 1); pdf.cell(35, 8, " Date", 1); pdf.cell(25, 8, " %", 1); pdf.cell(50, 8, " Amount", 1, 1)
    pdf.set_font("Arial", size=9)
    for row in schedule:
        pdf.cell(60, 7, row['Milestone'], 1)
        pdf.cell(35, 7, row['Date'], 1, 0, 'C')
        pdf.cell(25, 7, row['Percent'], 1, 0, 'C')
        pdf.cell(50, 7, f"{row['Amount']:,.2f}", 1, 1, 'R')
    
    return pdf.output(dest='S')

# --- 5. واجهة التطبيق الرئيسية ---
st.set_page_config(layout="wide", page_title="Reportage Agent")
st.title("🏗️ Reportage Sales Expert")

with st.sidebar:
    st.header("🏢 Project Selection")
    selected_project = st.selectbox("Choose Project:", list(PROJECTS_DATABASE.keys()))
    df_inv = load_google_sheet(PROJECTS_DATABASE[selected_project])
    df_photos = load_google_sheet(PHOTO_BANK_URL)
    
    st.divider()
    selected_plan = st.selectbox("Payment Plan:", list(ALL_PLANS.keys()))
    extra_disc = st.number_input("Extra Discount %", 0.0, 15.0, 0.0)
    m_pct = st.number_input("Monthly %", 0.0, 5.0, 1.0)
    dp_m = st.number_input("DP Months", 1, 24, 1)
    r_freq = st.selectbox("Recovery (Months)", [0, 6, 12])
    r_pct = st.number_input("Recovery %", 0.0, 20.0, 0.0)

if df_inv is not None:
    unit_id = st.selectbox("Select Unit:", df_inv['Plot + Unit No.'].unique())
    unit_data = df_inv[df_inv['Plot + Unit No.'] == unit_id].iloc[0]

    # جلب البيانات
    parking = float(str(unit_data.get('parking', '0')).replace(',', ''))
    h_date_str = str(unit_data.get('Handover Date', '2029-09-01'))
    try: h_date = pd.to_datetime(h_date_str).date()
    except: h_date = date(2029, 9, 1)

    # الحسابات
    u_price = float(str(unit_data.get('Original Price (AED)', '0')).replace(',', ''))
    total_disc = ALL_PLANS[selected_plan]['disc'] + extra_disc
    selling_price = (u_price * (1 - total_disc/100)) + parking
    
    settings = {'dp_months': dp_m, 'monthly_pct': m_pct, 'recovery_freq': r_freq, 'recovery_pct': r_pct}
    schedule = calculate_plan_v3(selling_price, ALL_PLANS[selected_plan], settings, date.today(), h_date)

    # البحث عن الصور
    try:
        p_key = selected_project.split()[0].upper()
        match = df_photos[(df_photos['Project'].str.upper().str.contains(p_key)) & 
                          (df_photos['Bedrooms'].astype(str).str.strip() == str(unit_data['Bedrooms']).strip()) & 
                          (df_photos['Sub-type'].astype(str).str.strip() == str(unit_data['Sub-type']).strip())]
        layout_url = match.iloc[0]['Layout_URL'] if not match.empty else None
    except: layout_url = None

    # العرض
    st.divider()
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(f"Offer: {selected_project} - Unit {unit_id}")
        df_display = pd.DataFrame(schedule)
        st.table(df_display.style.format({"Amount": "{:,.2f}"}))
        st.markdown(f"### 💰 **TOTAL INSTALLMENTS: {df_display['Amount'].sum():,.2f} AED**")
        
    with col2:
        if layout_url: st.image(layout_url, use_container_width=True)
        else: st.warning("No Layout Image found")
        
        financials = {'selling_price': selling_price, 'u_price': u_price, 'disc_pct': total_disc, 'disc_val': u_price*(total_disc/100), 'parking': parking}
        pdf_out = create_pdf(unit_data, financials, schedule, layout_url, selected_plan, selected_project)
        st.download_button("Download PDF Offer", data=bytes(pdf_out), file_name=f"Offer_{unit_id}.pdf")

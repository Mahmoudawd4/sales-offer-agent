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
    "10% DP / 10% Disc / 1% Monthly": {"dp_pct": 10, "disc": 10, "default_monthly": 1.0, "type": "standard"},
    "20% DP / 10% Disc / 1% Monthly": {"dp_pct": 20, "disc": 10, "default_monthly": 1.0, "type": "standard"},
    "30% DP / 15% Disc / 1% Monthly": {"dp_pct": 30, "disc": 15, "default_monthly": 1.0, "type": "standard"},
    "0% DP / 0% Disc / 1% Monthly": {"dp_pct": 0, "disc": 0, "default_monthly": 1.0, "type": "standard"},
    "20% DP / 2% Disc / 10% @12m / 70% HO": {"dp_pct": 20, "disc": 2, "default_monthly": 0.0, "type": "special", "recovery_at_12": 10, "ho_pct": 70},
    "25% Discount Cash": {"dp_pct": 100, "disc": 25, "default_monthly": 0.0, "type": "cash"},
    "30% Discount Cash": {"dp_pct": 100, "disc": 30, "default_monthly": 0.0, "type": "cash"},
    "18% Discount Cash": {"dp_pct": 100, "disc": 18, "default_monthly": 0.0, "type": "cash"},
    "No Discount - Full within month": {"dp_pct": 100, "disc": 0, "default_monthly": 0.0, "type": "cash"},
    "Plan A (5% DP / 5% Disc)": {"dp_pct": 5, "disc": 5, "default_monthly": 1.0, "type": "standard"}
}

@st.cache_data
def load_google_sheet(url):
    try:
        df = pd.read_csv(url)
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return df
    except: return None

def calculate_ultra_flexible_plan(selling_price, plan_cfg, settings, start_date, handover_date):
    plan = []
    res_fee = 20000
    plan.append({"Milestone": "Reservation Fee", "Date": "Now", "Percent": "-", "Amount": res_fee})
    
    dp_pct = plan_cfg['dp_pct']
    # حساب إجمالي الـ DP مخصوم منه الحجز
    total_dp_val = (selling_price * (dp_pct / 100))
    remaining_dp = total_dp_val - res_fee
    dp_months = settings['dp_months']
    
    # 1. توزيع المقدم
    if dp_pct > 0:
        if dp_months > 1:
            for i in range(dp_months):
                d = start_date + relativedelta(months=i)
                plan.append({"Milestone": f"DP Installment {i+1}", "Date": d.strftime("%b-%y"), "Percent": f"{(dp_pct/dp_months):.1f}%", "Amount": max(0, remaining_dp / dp_months)})
        else:
            plan.append({"Milestone": "1st Installment (DP)", "Date": start_date.strftime("%b-%y"), "Percent": f"{dp_pct}%", "Amount": max(0, remaining_dp)})

    # 2. الأقساط الشهرية أو دفعات خاصة
    if plan_cfg.get("type") == "special":
        # دفعة الـ 10% بعد 12 شهر
        rec_date = start_date + relativedelta(months=12)
        plan.append({"Milestone": "Payment after 12 Months", "Date": rec_date.strftime("%b-%y"), "Percent": "10%", "Amount": selling_price * 0.10})
    
    elif plan_cfg.get("type") == "standard":
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

    # 3. حساب إجمالي ما تم دفعه قبل الاستلام
    total_installments = sum(item['Amount'] for item in plan)
    plan.append({"Milestone": "--------------------------", "Date": "----------", "Percent": "----------", "Amount": 0.0})
    plan.append({"Milestone": "TOTAL INSTALLMENT", "Date": "Pre-Handover", "Percent": "-", "Amount": total_installments})
    plan.append({"Milestone": "--------------------------", "Date": "----------", "Percent": "----------", "Amount": 0.0})

    # 4. دفعة الاستلام (Balance)
    handover_amt = selling_price - total_installments
    if plan_cfg.get("type") == "special":
        handover_amt = selling_price * (plan_cfg['ho_pct'] / 100)
        
    if handover_amt > 1:
        plan.append({"Milestone": "Final Handover / Balance", "Date": handover_date.strftime("%b-%y"), "Percent": "Balance", "Amount": handover_amt})
    
    return plan

def create_sales_offer_pdf(unit_data, financials, schedule, layout_url, plan_name, project_name):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image(LOGO_URL, x=10, y=8, w=35)
    except: pass
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 15, f"SALES OFFER - {project_name}", ln=True, align='C')
    
    # تفاصيل الوحدة والملخص المالي (مختصر للـ PDF)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, f"Unit: {unit_data.get('Plot + Unit No.', 'N/A')} | Price: {financials['selling_price']:,.2f} AED", ln=True)
    
    # الجدول
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(60, 8, " Milestone", 1); pdf.cell(35, 8, " Date", 1); pdf.cell(25, 8, " %", 1); pdf.cell(45, 8, " Amount", 1, 1)
    
    pdf.set_font("Arial", size=8)
    for row in schedule:
        # تمييز صف الإجمالي في الـ PDF
        if row['Milestone'] == "TOTAL INSTALLMENT":
            pdf.set_font("Arial", 'B', 8)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(60, 7, row['Milestone'], 1, 0, 'L', True)
            pdf.cell(35, 7, row['Date'], 1, 0, 'C', True)
            pdf.cell(25, 7, row['Percent'], 1, 0, 'C', True)
            pdf.cell(45, 7, f"{row['Amount']:,.2f}", 1, 1, 'R', True)
            pdf.set_font("Arial", size=8)
        elif "---" in row['Milestone']:
            continue # تخطي الخطوط الفاصلة في الـ PDF
        else:
            pdf.cell(60, 7, row['Milestone'], 1)
            pdf.cell(35, 7, row['Date'], 1, 0, 'C')
            pdf.cell(25, 7, row['Percent'], 1, 0, 'C')
            pdf.cell(45, 7, f"{row['Amount']:,.2f}", 1, 1, 'R')
            
    return pdf.output(dest='S')

# --- واجهة التطبيق ---
st.set_page_config(page_title="Reportage Smart Agent", layout="wide")
st.title("🏗️ Reportage Sales Agent (Updated Version)")

with st.sidebar:
    st.header("🏢 Project & Settings")
    selected_project = st.selectbox("Select Project:", list(PROJECTS_DATABASE.keys()))
    df_inventory = load_google_sheet(PROJECTS_DATABASE[selected_project])
    df_photos = load_google_sheet(PHOTO_BANK_URL)
    
    st.divider()
    selected_plan = st.selectbox("Payment Plan:", list(ALL_PLANS.keys()))
    default_m_pct = ALL_PLANS[selected_plan].get("default_monthly", 1.0)
    
    extra_disc = st.number_input("Extra Discount %", 0.0, 15.0, 0.0)
    m_pct = st.number_input("Monthly %", 0.0, 5.0, float(default_m_pct))
    dp_m = st.number_input("DP Split (Months):", 1, 24, 1)
    r_freq = st.selectbox("Recovery (Months):", [0, 6, 12])
    r_pct = st.number_input("Recovery %", 0.0, 20.0, 0.0)

if df_inventory is not None:
    unit_id = st.selectbox("Select Unit:", df_inventory['Plot + Unit No.'].unique())
    unit_data = df_inventory[df_inventory['Plot + Unit No.'] == unit_id].iloc[0]

    # الحسابات
    parking = float(str(unit_data.get('parking', '0')).replace(',', ''))
    u_price = float(str(unit_data.get('Original Price (AED)', '0')).replace(',', ''))
    total_disc = ALL_PLANS[selected_plan]['disc'] + extra_disc
    selling_price = (u_price * (1 - total_disc/100)) + parking
    
    h_date_str = str(unit_data.get('Handover Date', '2029-09-01'))
    try: h_date = pd.to_datetime(h_date_str).date()
    except: h_date = date(2029, 9, 1)

    financials = {'u_price': u_price, 'disc_pct': total_disc, 'selling_price': selling_price, 'parking': parking}
    settings = {'dp_months': dp_m, 'monthly_pct': m_pct, 'recovery_freq': r_freq, 'recovery_pct': r_pct}
    
    schedule = calculate_ultra_flexible_plan(selling_price, ALL_PLANS[selected_plan], settings, date.today(), h_date)

    # العرض
    st.divider()
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(f"Payment Schedule: Unit {unit_id}")
        st.dataframe(pd.DataFrame(schedule).style.format({"Amount": "{:,.2f}"}), use_container_width=True)
        
    with col2:
        st.metric("Total Selling Price", f"{selling_price:,.2f} AED")
        st.metric("Discount Applied", f"{total_disc}%")
        
        pdf_bytes = create_sales_offer_pdf(unit_data, financials, schedule, None, selected_plan, selected_project)
        st.download_button("Download PDF", data=bytes(pdf_bytes), file_name=f"Offer_{unit_id}.pdf", use_container_width=True)

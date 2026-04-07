import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- دالة حساب خطة الدفع ---
def calculate_ultra_flexible_plan(selling_price, plan_cfg, settings, start_date, handover_date):
    plan = []
    res_fee = 20000
    plan.append({"Milestone": "Reservation Fee", "Date": "Now", "Percent": "-", "Amount": res_fee})
    
    dp_pct = plan_cfg['dp_pct']
    dp_val = (selling_price * (dp_pct / 100)) - res_fee
    dp_months = settings['dp_months']
    
    if dp_months > 1:
        for i in range(dp_months):
            d = start_date + relativedelta(months=i)
            plan.append({"Milestone": f"DP Installment {i+1}", "Date": d.strftime("%b-%y"), "Percent": f"{(dp_pct/dp_months):.1f}%", "Amount": dp_val / dp_months})
    else:
        plan.append({"Milestone": "1st Installment (DP)", "Date": start_date.strftime("%b-%y"), "Percent": f"{dp_pct}%", "Amount": dp_val})

    monthly_pct = settings['monthly_pct'] / 100
    curr_d = start_date + relativedelta(months=max(1, dp_months))
    
    while curr_d < handover_date:
        if settings['recovery_freq'] > 0:
            months_diff = (curr_d.year - start_date.year) * 12 + curr_d.month - start_date.month
            if months_diff > 0 and months_diff % settings['recovery_freq'] == 0:
                recovery_amt = selling_price * (settings['recovery_pct'] / 100)
                plan.append({"Milestone": f"Recovery Payment", "Date": curr_d.strftime("%b-%y"), "Percent": f"{settings['recovery_pct']}%", "Amount": recovery_amt})

        amt = selling_price * monthly_pct
        if amt > 0:
            plan.append({"Milestone": "Monthly Installment", "Date": curr_d.strftime("%b-%y"), "Percent": f"{settings['monthly_pct']}%", "Amount": amt})
        curr_d += relativedelta(months=1)

    total_paid = sum(item['Amount'] for item in plan)
    handover_amt = selling_price - total_paid
    if handover_amt > 1:
        plan.append({"Milestone": "Final Handover", "Date": handover_date.strftime("%b-%y"), "Percent": "Balance", "Amount": handover_amt})
            
    return plan

# --- دالة إنشاء PDF احترافي ---
def generate_pro_pdf(unit_data, financials, schedule, plan_name):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 15, "SALES OFFER - REPORTAGE PROPERTIES", ln=True, align='C')
    pdf.ln(5)
    
    # Unit Details Section
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, " UNIT SPECIFICATIONS", 0, 1, 'L', True)
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(0)
    
    # طباعة بيانات الوحدة
    info = [
        f"Unit No: {unit_data.get('Plot + Unit No.', 'N/A')}",
        f"Type: {unit_data.get('UNIT TYPE', 'N/A')}",
        f"Bedrooms: {unit_data.get('Bedrooms', 'N/A')}",
        f"View: {unit_data.get('View', 'N/A')}",
        f"Total Area: {unit_data.get('Total Area (Sq.ft)', '0')} SQFT"
    ]
    for item in info:
        pdf.cell(0, 7, item, ln=True)
    pdf.ln(5)

    # Financial Summary
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, " FINANCIAL SUMMARY", 0, 1, 'L', True)
    pdf.set_font("Arial", size=10)
    pdf.cell(100, 8, "Original Price:", 0)
    pdf.cell(0, 8, f"{financials['u_price']:,.2f} AED", 0, 1, 'R')
    pdf.cell(100, 8, f"Discount ({financials['disc_pct']}%):", 0)
    pdf.cell(0, 8, f"- {financials['disc_val']:,.2f} AED", 0, 1, 'R')
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 8, "Selling Price (Incl. Parking):", 0)
    pdf.cell(0, 8, f"{financials['selling_price']:,.2f} AED", 0, 1, 'R')
    pdf.ln(10)

    # Payment Schedule Table Header
    pdf.set_fill_color(44, 62, 80)
    pdf.set_text_color(255)
    pdf.cell(60, 10, " Milestone", 1, 0, 'L', True)
    pdf.cell(40, 10, " Date", 1, 0, 'C', True)
    pdf.cell(30, 10, " %", 1, 0, 'C', True)
    pdf.cell(60, 10, " Amount (AED)", 1, 1, 'R', True)

    # Table Rows (الحلقة التي كانت ناقصة)
    pdf.set_text_color(0)
    pdf.set_font("Arial", size=9)
    for row in schedule:
        pdf.cell(60, 8, f" {row['Milestone']}", 1)
        pdf.cell(40, 8, f" {row['Date']}", 1, 0, 'C')
        pdf.cell(30, 8, f" {row['Percent']}", 1, 0, 'C')
        pdf.cell(60, 8, f"{row['Amount']:,.2f} ", 1, 1, 'R')
        
    return pdf.output(dest='S')

# --- واجهة Streamlit ---
st.set_page_config(page_title="Reportage Agent", layout="wide")
st.title("🏗️ Reportage Sales AI Agent")

# الخطط المتاحة
ALL_PLANS = {
    "Plan A (5% DP / 5% Disc)": {"dp_pct": 5, "disc": 5},
    "Plan 2 (10% DP / 5% Disc)": {"dp_pct": 10, "disc": 5},
    "Plan 7 (20% DP / 15% Disc)": {"dp_pct": 20, "disc": 15},
    "Plan 11 (30% DP / 5% Disc)": {"dp_pct": 30, "disc": 5},
    "Plan 12 (Cash 40% Disc)": {"dp_pct": 100, "disc": 40},
    "Plan 15 (20/80)": {"dp_pct": 20, "disc": 0}
}

file = st.file_uploader("Upload Data", type=["csv", "xlsx"])

if file:
    df = pd.read_csv(file) if file.name.endswith('csv') else pd.read_excel(file)
    
    with st.sidebar:
        st.header("Plan Customization")
        selected_plan = st.selectbox("Base Plan:", list(ALL_PLANS.keys()))
        extra_disc = st.number_input("Extra Discount %", 0.0, 10.0, 0.0)
        m_pct = st.number_input("Monthly %", 0.0, 2.0, 1.0, step=0.1)
        dp_m = st.number_input("DP Split (Months):", 1, 12, 1)
        r_freq = st.selectbox("Recovery (Months):", [0, 6, 12])
        r_pct = st.number_input("Recovery %", 0.0, 20.0, 0.0)

    unit_id = st.selectbox("Select Unit:", df['Plot + Unit No.'].unique())
    unit_data = df[df['Plot + Unit No.'] == unit_id].iloc[0]

    # الحسابات
    u_price = float(unit_data['Price '])
    total_disc_pct = ALL_PLANS[selected_plan]['disc'] + extra_disc
    disc_val = u_price * (total_disc_pct / 100)
    selling_price = (u_price - disc_val) + 40000
    
    financials = {
        'u_price': u_price, 
        'disc_pct': total_disc_pct, 
        'disc_val': disc_val, 
        'selling_price': selling_price
    }
    
    settings = {'dp_months': dp_m, 'monthly_pct': m_pct, 'recovery_freq': r_freq, 'recovery_pct': r_pct}
    schedule = calculate_ultra_flexible_plan(selling_price, ALL_PLANS[selected_plan], settings, date.today(), date(2029, 9, 1))
    
    # العرض في الموقع
    st.table(pd.DataFrame(schedule))
    
    # زر التحميل مع الكود المصلح
    if st.button("🚀 Download Full PDF Offer"):
        pdf_bytes = generate_pro_pdf(unit_data, financials, schedule, selected_plan)
        st.download_button(
            label="Click to save PDF",
            data=bytes(pdf_bytes),
            file_name=f"Reportage_Offer_{unit_id}.pdf",
            mime="application/pdf"
        )

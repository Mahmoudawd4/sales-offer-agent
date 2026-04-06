import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- إعدادات الصفحة ---
st.set_page_config(page_title="Reportage Agent - SILA", layout="wide")

# --- دالة حساب التواريخ والأقساط ---
def generate_payment_plan(selling_price, dp_pct, start_date, handover_date):
    plan = []
    # 1. الحجز
    plan.append({"Milestone": "Reservation Fee", "Date": "Now", "Percent": "-", "Amount": 20000})
    
    # 2. الدفعة المقدمة (DP)
    dp_amount = (selling_price * (dp_pct / 100)) - 20000
    plan.append({"Milestone": "1st Installment (DP)", "Date": start_date.strftime("%B-%y"), "Percent": f"{dp_pct}%", "Amount": dp_amount})
    
    # 3. الأقساط الشهرية (1% شهرياً)
    current_date = start_date + relativedelta(months=1)
    monthly_amt = selling_price * 0.01
    
    # نحسب عدد الأشهر حتى الاستلام
    while current_date < handover_date:
        plan.append({"Milestone": "Monthly Installment", "Date": current_date.strftime("%B-%y"), "Percent": "1.00%", "Amount": monthly_amt})
        current_date += relativedelta(months=1)
        
    # 4. دفعة الاستلام (Handover)
    total_paid = sum(item['Amount'] for item in plan)
    handover_amt = selling_price - total_paid
    plan.append({"Milestone": "On Handover", "Date": handover_date.strftime("%B-%y"), "Percent": "Balance", "Amount": handover_amt})
    
    return plan

# --- واجهة التطبيق ---
st.title("🏗️ Reportage AI Agent - SILA MASDAR")

uploaded_file = st.file_uploader("Upload SILA Availability (CSV/XLSX)", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('csv') else pd.read_excel(uploaded_file)
    
    col1, col2 = st.columns(2)
    with col1:
        unit_no = st.selectbox("Select Unit Number:", df['Plot + Unit No.'].unique())
        unit_info = df[df['Plot + Unit No.'] == unit_no].iloc[0]
        discount = st.slider("Discount %", 0, 30, 15)
        
    with col2:
        dp_input = st.selectbox("Down Payment %", [10, 20, 30])
        handover_dt = date(2029, 9, 1) # تاريخ استلام سيلا

    # --- الحسابات المالية ---
    u_price = float(unit_info['Price '])
    disc_val = u_price * (discount / 100)
    net_price = u_price - disc_val
    parking = 0 if "Townhouse" in str(unit_info['UNIT TYPE']) else 40000
    selling_price = net_price + parking
    gov_fees = (selling_price * 0.02) + 625

    # --- عرض النتائج ---
    st.write("---")
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("Selling Price", f"{selling_price:,.0f} AED")
    res_col2.metric("Discount", f"-{disc_val:,.0f} AED")
    res_col3.metric("Gov Fees (2%+625)", f"{gov_fees:,.0f} AED")

    # --- توليد جدول الأقساط ---
    st.subheader("Payment Plan Schedule")
    installments = generate_payment_plan(selling_price, dp_input, date.today(), handover_dt)
    st.table(pd.DataFrame(installments))

    # --- زر التحميل (PDF) ---
    if st.button("Export to PDF"):
        st.info("جاري تجهيز التصميم الاحترافي للـ PDF...")

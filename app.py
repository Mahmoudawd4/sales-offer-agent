import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- إعدادات الصفحة ---
st.set_page_config(page_title="Reportage Agent - SILA", layout="wide")

# --- دالة حساب التواريخ والأقساط الذكية ---
def generate_payment_plan(selling_price, plan_choice, dp_pct, dp_months, cash_months, start_date, handover_date):
    plan = []
    
    # رسوم الحجز ثابتة
    plan.append({"Installment": 1, "Milestone": "Reservation Fee", "Date": "Now", "Percent": "-", "Amount": 20000})
    
    # حساب الدفعة المقدمة الصافية (خصم الحجز)
    total_dp_amount = (selling_price * (dp_pct / 100)) - 20000
    
    # ------------------ خطة كاش (Plan 12, 13, 14) ------------------
    if "Cash" in plan_choice:
        remaining_for_cash = selling_price - 20000
        cash_per_month = remaining_for_cash / cash_months
        current_date = start_date
        
        for i in range(cash_months):
            plan.append({
                "Installment": i + 2,
                "Milestone": f"Cash Payment {i+1}/{cash_months}",
                "Date": current_date.strftime("%B-%y"),
                "Percent": f"{round(100/cash_months, 2)}%",
                "Amount": cash_per_month
            })
            current_date += relativedelta(months=1)
            
    # ------------------ الخطط العادية (Plan 11, 15) ------------------
    elif plan_choice in ["Plan 11", "Plan 15 (20/80)", "Plan 15 (20% split)"]:
        # تقسيط الدفعة المقدمة إن وجد
        if dp_months > 1 and total_dp_amount > 0:
            dp_per_month = total_dp_amount / dp_months
            current_date = start_date
            for i in range(dp_months):
                plan.append({
                    "Installment": i + 2,
                    "Milestone": f"DP Installment {i+1}/{dp_months}",
                    "Date": current_date.strftime("%B-%y"),
                    "Percent": f"{round(dp_pct/dp_months, 2)}%",
                    "Amount": dp_per_month
                })
                current_date += relativedelta(months=1)
        else:
            plan.append({
                "Installment": 2,
                "Milestone": "1st Installment (DP)",
                "Date": start_date.strftime("%B-%y"),
                "Percent": f"{dp_pct}%",
                "Amount": total_dp_amount
            })
            
        # المبلغ المتبقي عند الاستلام
        total_paid = sum(item['Amount'] for item in plan)
        handover_amt = selling_price - total_paid
        
        plan.append({
            "Installment": len(plan) + 1,
            "Milestone": "On Handover",
            "Date": handover_date.strftime("%B-%y"),
            "Percent": "Balance",
            "Amount": handover_amt
        })
        
    return plan

# --- دالة لتوليد ملف الـ PDF بنفس التنسيق المطلوب ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'SALES OFFER - SILA MASDAR', 0, 1, 'C')
        self.ln(10)

def create_pdf(unit_no, unit_info, selling_price, net_price, parking, disc_val, gov_fees, installments):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    
    # تفاصيل الوحدة
    pdf.cell(0, 10, f"Unit: {unit_no}", 0, 1)
    pdf.cell(0, 10, f"Type: {unit_info['UNIT TYPE']} - {unit_info['Bedrooms']}", 0, 1)
    pdf.cell(0, 10, f"Total Area: {unit_info['Total Area (Sq.ft)']} SQFT", 0, 1)
    pdf.cell(0, 10, f"View: {unit_info['View']}", 0, 1)
    pdf.ln(5)
    
    # تفاصيل الأسعار
    pdf.cell(0, 10, f"Unit Price: {float(unit_info['Price ']):,.2f} AED", 0, 1)
    pdf.cell(0, 10, f"Discount: -{disc_val:,.2f} AED", 0, 1)
    pdf.cell(0, 10, f"Price After Discount: {net_price:,.2f} AED", 0, 1)
    pdf.cell(0, 10, f"Parking: {parking:,.2f} AED", 0, 1)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Total Selling Price: {selling_price:,.2f} AED", 0, 1)
    pdf.cell(0, 10, f"Government Fees (2% + 625): {gov_fees:,.2f} AED", 0, 1)
    pdf.ln(10)
    
    # جدول الأقساط
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(10, 10, "No", 1)
    pdf.cell(50, 10, "Milestone", 1)
    pdf.cell(30, 10, "Date", 1)
    pdf.cell(30, 10, "Percent", 1)
    pdf.cell(40, 10, "Amount (AED)", 1)
    pdf.ln()
    
    pdf.set_font("Arial", size=10)
    for row in installments:
        pdf.cell(10, 10, str(row['Installment']), 1)
        pdf.cell(50, 10, str(row['Milestone']), 1)
        pdf.cell(30, 10, str(row['Date']), 1)
        pdf.cell(30, 10, str(row['Percent']), 1)
        pdf.cell(40, 10, f"{row['Amount']:,.2f}", 1)
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# --- واجهة التطبيق الرئيسية ---
st.title("🤖 Reportage Smart AI Agent")

uploaded_file = st.file_uploader("Upload SILA Availability (CSV/XLSX)", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('csv') else pd.read_excel(uploaded_file)
    
    st.sidebar.header("Parameters & Plans")
    unit_no = st.sidebar.selectbox("Select Unit Number:", df['Plot + Unit No.'].unique())
    unit_info = df[df['Plot + Unit No.'] == unit_no].iloc[0]
    
    # اختيار الخطة والقواعد
    plan_choice = st.sidebar.selectbox("Select Payment Plan:", [
        "Plan 11 (30% DP - 70% HO)",
        "Plan 12 (Cash 40% Disc)",
        "Plan 13 (Cash 25% Disc)",
        "Plan 14 (Cash 30% Disc)",
        "Plan 15 (20/80)",
        "Plan 15 (20% split)"
    ])
    
    # تطبيق الخصومات والـ DP أوتوماتيكياً حسب اختيارك للـ Plan
    discount = 0
    dp_input = 0
    cash_months = 3
    dp_months = 1
    
    if plan_choice == "Plan 11 (30% DP - 70% HO)":
        discount = 5
        dp_input = 30
    elif plan_choice == "Plan 12 (Cash 40% Disc)":
        discount = 40
        cash_months = st.sidebar.number_input("How many months for Cash?", 1, 12, 3)
    elif plan_choice == "Plan 13 (Cash 25% Disc)":
        discount = 25
        cash_months = st.sidebar.number_input("How many months for Cash?", 1, 12, 3)
    elif plan_choice == "Plan 14 (Cash 30% Disc)":
        discount = 30
        cash_months = st.sidebar.number_input("How many months for Cash?", 1, 12, 3)
    elif plan_choice == "Plan 15 (20/80)":
        discount = 0
        dp_input = 20
    elif plan_choice == "Plan 15 (20% split)":
        discount = 0
        dp_input = 20
        dp_months = st.sidebar.number_input("Divide DP over how many months?", 1, 20, 20)

    # --- الحسابات المالية الدقيقة ---
    u_price = float(unit_info['Price '])
    disc_val = u_price * (discount / 100)
    net_price = u_price - disc_val
    parking = 0 if "Townhouse" in str(unit_info['UNIT TYPE']) else 40000
    selling_price = net_price + parking
    gov_fees = (selling_price * 0.02) + 625

    # --- عرض بطاقات النتائج ---
    st.write(f"### Results for Unit: {unit_no} ({unit_info['UNIT TYPE']})")
    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    res_col1.metric("Original Price", f"{u_price:,.0f} AED")
    res_col2.metric("Discount Applied", f"-{disc_val:,.0f} AED ({discount}%)")
    res_col3.metric("Final Selling Price", f"{selling_price:,.0f} AED")
    res_col4.metric("Gov Fees", f"{gov_fees:,.0f} AED")

    # توليد جدول الأقساط
    handover_dt = date(2029, 9, 1)
    installments = generate_payment_plan(selling_price, plan_choice, dp_input, dp_months, cash_months, date.today(), handover_dt)
    
    st.subheader("Payment Plan Schedule")
    st.table(pd.DataFrame(installments))

    # --- زر تفعيل توليد الـ PDF حقيقياً ---
    pdf_data = create_pdf(unit_no, unit_info, selling_price, net_price, parking, disc_val, gov_fees, installments)
    
    st.download_button(
        label="Generate and Download PDF",
        data=pdf_data,
        file_name=f"Offer_Unit_{unit_no}.pdf",
        mime="application/pdf"
    )

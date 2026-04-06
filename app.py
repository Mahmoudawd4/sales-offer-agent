import streamlit as st
import pandas as pd
from fpdf import FPDF
import io
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- دالة حساب خطة الدفع ---
def calculate_payment_plan(selling_price, plan_name, dp_split_months, start_date, handover_date):
    plan = []
    res_fee = 20000
    plan.append({"Milestone": "Reservation Fee", "Date": "Now", "Percent": "-", "Amount": res_fee})
    
    # تعريف إعدادات الخطط
    plans_config = {
        "Plan 11": {"dp": 30, "type": "ho"},
        "Plan 12": {"dp": 100, "type": "cash"},
        "Plan 13": {"dp": 100, "type": "cash"},
        "Plan 14": {"dp": 100, "type": "cash"},
        "Plan 15 (20/80)": {"dp": 20, "type": "ho"},
        "Plan 15 (20 in 20m)": {"dp": 20, "type": "monthly_dp"}
    }
    
    cfg = plans_config[plan_name]
    total_dp_val = (selling_price * (cfg['dp'] / 100)) - res_fee
    
    # توزيع الـ DP
    if dp_split_months > 1:
        monthly_dp = total_dp_val / dp_split_months
        for i in range(dp_split_months):
            d = start_date + relativedelta(months=i)
            plan.append({"Milestone": f"DP Installment {i+1}", "Date": d.strftime("%b-%y"), "Percent": f"{(cfg['dp']/dp_split_months):.1f}%", "Amount": monthly_dp})
    else:
        plan.append({"Milestone": "1st Installment (DP)", "Date": start_date.strftime("%b-%y"), "Percent": f"{cfg['dp']}%", "Amount": total_dp_val})

    # الأقساط الشهرية أو الكاش
    if cfg['type'] == "cash":
        remaining = selling_price - (total_dp_val + res_fee)
        if remaining > 0:
            cash_period = 3 # افتراضي 3 أشهر للكاش
            for i in range(1, cash_period + 1):
                d = start_date + relativedelta(months=i + dp_split_months - 1)
                plan.append({"Milestone": "Cash Payment", "Date": d.strftime("%b-%y"), "Percent": "Balance", "Amount": remaining/cash_period})
    
    elif cfg['type'] == "ho" or cfg['type'] == "monthly_dp":
        # إضافة 1% شهرياً إذا كانت الخطة تسمح
        if plan_name not in ["Plan 11", "Plan 15 (20/80)"]:
            monthly_amt = selling_price * 0.01
            curr_d = start_date + relativedelta(months=dp_split_months)
            while curr_d < handover_date:
                plan.append({"Milestone": "Monthly Installment", "Date": curr_d.strftime("%b-%y"), "Percent": "1%", "Amount": monthly_amt})
                curr_d += relativedelta(months=1)

        # دفعة الاستلام
        total_paid_so_far = sum(item['Amount'] for item in plan)
        balance = selling_price - total_paid_so_far
        if balance > 0:
            plan.append({"Milestone": "On Handover", "Date": handover_date.strftime("%b-%y"), "Percent": "Balance", "Amount": balance})
            
    return plan

# --- دالة إنشاء الـ PDF (المصححة) ---
def create_pdf_report(unit_info, financials, schedule):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "SALES OFFER - SILA MASDAR", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 10, f"Unit Number: {unit_info['Plot + Unit No.']}", ln=True)
    pdf.cell(0, 10, f"Unit Type: {unit_info['UNIT TYPE']} - {unit_info['Bedrooms']}", ln=True)
    pdf.cell(0, 10, f"Total Area: {unit_info['Total Area (Sq.ft)']} SQFT", ln=True)
    pdf.ln(5)
    
    # البيانات المالية
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(100, 10, "Description", 1, 0, 'C', True)
    pdf.cell(90, 10, "Value (AED)", 1, 1, 'C', True)
    
    pdf.cell(100, 10, "Original Price", 1)
    pdf.cell(90, 10, f"{financials['u_price']:,.0f}", 1, 1, 'R')
    pdf.cell(100, 10, "Selling Price (Incl. Parking)", 1)
    pdf.cell(90, 10, f"{financials['selling_price']:,.0f}", 1, 1, 'R')
    pdf.ln(10)
    
    # جدول الأقساط
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(60, 10, "Milestone", 1, 0, 'C', True)
    pdf.cell(40, 10, "Date", 1, 0, 'C', True)
    pdf.cell(30, 10, "Percent", 1, 0, 'C', True)
    pdf.cell(60, 10, "Amount (AED)", 1, 1, 'C', True)
    
    pdf.set_font("Arial", size=9)
    for row in schedule:
        pdf.cell(60, 8, str(row['Milestone']), 1)
        pdf.cell(40, 8, str(row['Date']), 1)
        pdf.cell(30, 8, str(row['Percent']), 1)
        pdf.cell(60, 8, f"{row['Amount']:,.0f}", 1, 1, 'R')
    
    # حفظ في ذاكرة مؤقتة بدلاً من ملف
    return pdf.output(dest='S')

# --- واجهة Streamlit ---
st.title("🏗️ Reportage Sales AI Agent")

file = st.file_uploader("Upload SILA Data", type=["csv", "xlsx"])

if file:
    df = pd.read_csv

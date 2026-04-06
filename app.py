import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- دالة حساب خطة الدفع المطورة ---
def calculate_flexible_plan(selling_price, plan_cfg, dp_split_months, extra_disc_pct, start_date, handover_date):
    plan = []
    res_fee = 20000
    plan.append({"Milestone": "Reservation Fee", "Date": "Now", "Percent": "-", "Amount": res_fee})
    
    dp_val = (selling_price * (plan_cfg['dp_pct'] / 100)) - res_fee
    
    # 1. توزيع الدفعة المقدمة (DP)
    if dp_split_months > 1:
        amt_per_month = dp_val / dp_split_months
        for i in range(dp_split_months):
            d = start_date + relativedelta(months=i)
            plan.append({"Milestone": f"DP Installment {i+1}", "Date": d.strftime("%b-%y"), "Percent": f"{(plan_cfg['dp_pct']/dp_split_months):.1f}%", "Amount": amt_per_month})
    else:
        plan.append({"Milestone": "1st Installment (DP)", "Date": start_date.strftime("%b-%y"), "Percent": f"{plan_cfg['dp_pct']}%", "Amount": dp_val})

    # 2. حساب الأقساط الشهرية (1%) بناءً على نوع الخطة
    if plan_cfg['type'] == "normal":
        monthly_amt = selling_price * 0.01
        curr_d = start_date + relativedelta(months=dp_split_months)
        while curr_d < handover_date:
            # نتوقف إذا وصلنا لمبلغ الاستلام (لو الخطة 20/80 أو ما شابه)
            total_so_far = sum(item['Amount'] for item in plan)
            if (selling_price - total_so_far) <= (selling_price * (plan_cfg['ho_pct']/100)):
                break
            plan.append({"Milestone": "Monthly Installment (1%)", "Date": curr_d.strftime("%b-%y"), "Percent": "1%", "Amount": monthly_amt})
            curr_d += relativedelta(months=1)

    elif plan_cfg['type'] == "cash":
        remaining = selling_price - sum(item['Amount'] for item in plan)
        cash_months = st.sidebar.number_input("Cash Period (Months):", 1, 12, 3)
        for i in range(1, cash_months + 1):
            d = start_date + relativedelta(months=i + dp_split_months - 1)
            plan.append({"Milestone": "Cash Payment", "Date": d.strftime("%b-%y"), "Percent": "Balance", "Amount": remaining/cash_months})

    # 3. دفعة الاستلام (Handover)
    total_paid = sum(item['Amount'] for item in plan)
    handover_amt = selling_price - total_paid
    if handover_amt > 1:
        plan.append({"Milestone": "On Handover (Balance)", "Date": handover_date.strftime("%b-%y"), "Percent": "Final", "Amount": handover_amt})
            
    return plan

# --- واجهة التطبيق ---
st.set_page_config(page_title="SILA Advanced Agent", layout="wide")
st.title("🏗️ Reportage Sales Agent - SILA Advanced")

# تعريف كافة الخطط
ALL_PLANS = {
    "Plan A (5% DP / 2.5% Disc)": {"dp_pct": 5, "disc": 2.5, "type": "normal", "ho_pct": 0},
    "Plan A (5% DP / 5% Disc)": {"dp_pct": 5, "disc": 5, "type": "normal", "ho_pct": 0},
    "Plan 2 (10% DP / 5% Disc)": {"dp_pct": 10, "disc": 5, "type": "normal", "ho_pct": 0},
    "Plan 3 (10% DP / 5% Disc)": {"dp_pct": 10, "disc": 5, "type": "normal", "ho_pct": 0},
    "Plan 5 (20% DP / 10% Disc)": {"dp_pct": 20, "disc": 10, "type": "normal", "ho_pct": 0},
    "Plan 7 (20% DP / 15% Disc)": {"dp_pct": 20, "disc": 15, "type": "normal", "ho_pct": 0},
    "Plan 9 (30% DP / 15% Disc)": {"dp_pct": 30, "disc": 15, "type": "normal", "ho_pct": 0},
    "Plan 10 (20% DP + 10% after 12M)": {"dp_pct": 20, "disc": 2, "type": "normal", "ho_pct": 70},
    "Plan 11 (30% DP / 70% HO)": {"dp_pct": 30, "disc": 5, "type": "ho_only", "ho_pct": 70},
    "Plan 15 (20/80)": {"dp_pct": 20, "disc": 0, "type": "ho_only", "ho_pct": 80},
    "Plan 15 (20 in 20m / 80 HO)": {"dp_pct": 20, "disc": 0, "type": "normal", "ho_pct": 80},
    "Plan 12 (Cash 40% Disc)": {"dp_pct": 100, "disc": 40, "type": "cash", "ho_pct": 0},
    "Plan 13 (Cash 25% Disc)": {"dp_pct": 100, "disc": 25, "type": "cash", "ho_pct": 0},
    "Plan 14 (Cash 30% Disc)": {"dp_pct": 100, "disc": 30, "type": "cash", "ho_pct": 0},
}

file = st.file_uploader("Upload SILA Data", type=["csv", "xlsx"])

if file:
    df = pd.read_csv(file) if file.name.endswith('csv') else pd.read_excel(file)
    
    with st.sidebar:
        st.header("Financial Control")
        selected_plan_name = st.selectbox("Select Payment Plan:", list(ALL_PLANS.keys()))
        extra_discount = st.number_input("Additional Discount (%)", 0.0, 10.0, 0.0)
        dp_months = st.number_input("Split DP over (Months):", 1, 24, 1)
        
    unit = st.selectbox("Select Unit Number:", df['Plot + Unit No.'].unique())
    unit_data = df[df['Plot + Unit No.'] == unit].iloc[0]
    
    # حساب السعر النهائي
    cfg = ALL_PLANS[selected_plan_name]
    total_discount_pct = cfg['disc'] + extra_discount
    u_price = float(unit_data['Price '])
    disc_val = u_price * (total_discount_pct / 100)
    selling_price = (u_price - disc_val) + 40000
    
    # توليد الجدول
    schedule = calculate_flexible_plan(selling_price, cfg, dp_months, extra_discount, date.today(), date(2029, 9, 1))
    df_schedule = pd.DataFrame(schedule)

    # حساب المجاميع للعرض
    total_monthly = df_schedule[df_schedule['Milestone'].str.contains("Monthly")]['Amount'].sum()
    total_ho = df_schedule[df_schedule['Milestone'].str.contains("Handover")]['Amount'].sum()

    # العرض المرئي
    st.write(f"### Offering: Unit {unit} | {selected_plan_name}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Selling Price", f"{selling_price:,.0f} AED")
    c2.metric("Total Discount", f"{total_discount_pct}%")
    c3.metric("Total Installments", f"{total_monthly:,.0f} AED")
    c4.metric("Handover Payment", f"{total_ho:,.0f} AED")

    st.table(df_schedule)
    
    # PDF Button
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"OFFER: UNIT {unit} - {selected_plan_name}", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"Selling Price: {selling_price:,.0f} AED | Discount: {total_discount_pct}%", ln=True)
    pdf.ln(5)
    for index, row in df_schedule.iterrows():
        pdf.cell(60, 8, str(row['Milestone']), 1)
        pdf.cell(40, 8, str(row['Date']), 1)
        pdf.cell(60, 8, f"{row['Amount']:,.0f} AED", 1, 1)
    
    st.download_button("📥 Download PDF Offer", data=bytes(pdf.output(dest='S')), file_name=f"SILA_{unit}.pdf")

import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- دالة حساب خطة الدفع فائقة المرونة ---
def calculate_ultra_flexible_plan(selling_price, plan_cfg, settings, start_date, handover_date):
    plan = []
    res_fee = 20000
    plan.append({"Milestone": "Reservation Fee", "Date": "Now", "Percent": "-", "Amount": res_fee})
    
    # 1. الدفعة المقدمة (DP)
    dp_pct = plan_cfg['dp_pct']
    dp_val = (selling_price * (dp_pct / 100)) - res_fee
    dp_months = settings['dp_months']
    
    if dp_months > 1:
        for i in range(dp_months):
            d = start_date + relativedelta(months=i)
            plan.append({"Milestone": f"DP Installment {i+1}", "Date": d.strftime("%b-%y"), "Percent": f"{(dp_pct/dp_months):.1f}%", "Amount": dp_val / dp_months})
    else:
        plan.append({"Milestone": "1st Installment (DP)", "Date": start_date.strftime("%b-%y"), "Percent": f"{dp_pct}%", "Amount": dp_val})

    # 2. الأقساط الشهرية المرنة (Custom Monthly %)
    monthly_pct = settings['monthly_pct'] / 100
    curr_d = start_date + relativedelta(months=max(1, dp_months))
    
    while curr_d < handover_date:
        # إضافة الدفعات الدورية (Recovery) إذا وُجدت
        if settings['recovery_freq'] > 0:
            months_diff = (curr_d.year - start_date.year) * 12 + curr_d.month - start_date.month
            if months_diff > 0 and months_diff % settings['recovery_freq'] == 0:
                recovery_amt = selling_price * (settings['recovery_pct'] / 100)
                plan.append({"Milestone": f"Recovery Payment ({settings['recovery_freq']}M)", "Date": curr_d.strftime("%b-%y"), "Percent": f"{settings['recovery_pct']}%", "Amount": recovery_amt})

        # القسط الشهري العادي
        amt = selling_price * monthly_pct
        if amt > 0:
            plan.append({"Milestone": "Monthly Installment", "Date": curr_d.strftime("%b-%y"), "Percent": f"{settings['monthly_pct']}%", "Amount": amt})
        
        curr_d += relativedelta(months=1)

    # 3. دفعة الاستلام (Handover)
    total_paid = sum(item['Amount'] for item in plan)
    handover_amt = selling_price - total_paid
    if handover_amt > 1:
        plan.append({"Milestone": "Final Handover Payment", "Date": handover_date.strftime("%b-%y"), "Percent": "Balance", "Amount": handover_amt})
            
    return plan

# --- واجهة التطبيق ---
st.set_page_config(page_title="Reportage Smart Agent", layout="wide")
st.title("🚀 Reportage Smart Sales Agent")

# قاعدة بيانات الخطط الأساسية
ALL_PLANS = {
    "Plan A (5% DP / 5% Disc)": {"dp_pct": 5, "disc": 5, "type": "normal"},
    "Plan 2 (10% DP / 5% Disc)": {"dp_pct": 10, "disc": 5, "type": "normal"},
    "Plan 7 (20% DP / 15% Disc)": {"dp_pct": 20, "disc": 15, "type": "normal"},
    "Plan 11 (30% DP / 5% Disc)": {"dp_pct": 30, "disc": 5, "type": "ho_only"},
    "Plan 12 (Cash 40% Disc)": {"dp_pct": 100, "disc": 40, "type": "cash"},
    "Plan 15 (20/80)": {"dp_pct": 20, "disc": 0, "type": "ho_only"}
}

file = st.file_uploader("Upload Inventory (CSV/Excel)", type=["csv", "xlsx"])

if file:
    df = pd.read_csv(file) if file.name.endswith('csv') else pd.read_excel(file)
    
    with st.sidebar:
        st.header("⚙️ التحسينات والخطط")
        selected_plan = st.selectbox("Payment Plan:", list(ALL_PLANS.keys()))
        extra_disc = st.number_input("Extra Discount %", 0.0, 10.0, 0.0, step=0.5)
        
        st.divider()
        st.subheader("Monthly & Recovery")
        m_pct = st.number_input("Monthly Installment %", 0.0, 2.0, 1.0, step=0.1)
        r_freq = st.selectbox("Recovery Every (Months):", [0, 6, 12], format_func=lambda x: "No Recovery" if x==0 else f"Every {x} Months")
        r_pct = st.number_input("Recovery Amount %", 0.0, 10.0, 0.0)
        dp_m = st.number_input("DP Split (Months):", 1, 12, 1)

    unit_id = st.selectbox("Select Unit:", df['Plot + Unit No.'].unique())
    unit_data = df[df['Plot + Unit No.'] == unit_id].iloc[0]

    # --- قسم عرض معلومات الوحدة (UI الجديد) ---
    st.subheader("🏠 Unit Specifications")
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.info(f"**Type**\n\n{unit_data.get('UNIT TYPE', 'N/A')}")
    with col_b:
        st.info(f"**Bedrooms**\n\n{unit_data.get('Bedrooms', 'N/A')}")
    with col_c:
        st.info(f"**View**\n\n{unit_data.get('View', 'N/A')}")
    with col_d:
        st.info(f"**Total Area**\n\n{unit_data.get('Total Area (Sq.ft)', '0')} SQFT")

    # الحسابات المالية
    u_price = float(unit_data['Price '])
    total_disc = ALL_PLANS[selected_plan]['disc'] + extra_disc
    selling_price = (u_price * (1 - total_disc/100)) + 4000 # Parking
    
    # إعدادات الحساب
    user_settings = {
        'monthly_pct': m_pct, 
        'recovery_freq': r_freq, 
        'recovery_pct': r_pct,
        'dp_months': dp_m
    }
    
    schedule = calculate_ultra_flexible_plan(selling_price, ALL_PLANS[selected_plan], user_settings, date.today(), date(2029, 9, 1))
    df_sched = pd.DataFrame(schedule)

    # --- عرض النتائج النهائية ---
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Final Selling Price", f"{selling_price:,.0f} AED")
    m2.metric("Total Discount Applied", f"{total_disc}%")
    m3.metric("Handover Amount", f"{df_sched.iloc[-1]['Amount']:,.0f} AED")

    st.write("### 📅 Payment Schedule")
    st.dataframe(df_sched.style.format({"Amount": "{:,.2f}"}), use_container_width=True)

    # تصدير PDF
    if st.button("Generate Official PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "OFFICIAL SALES OFFER", ln=True, align='C')
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 8, f"Unit: {unit_id} | Type: {unit_data.get('UNIT TYPE', 'N/A')} | View: {unit_data.get('View', 'N/A')}", ln=True)
        pdf.ln(5)
        # (بقية كود الـ PDF كما هو مع إضافة الأعمدة الجديدة)
        st.download_button("Click to Download", data=bytes(pdf.output(dest='S')), file_name=f"Offer_{unit_id}.pdf")

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

# --- 2. قاموس الخطط المحدث بالإضافات الجديدة ---
ALL_PLANS = {
    "10% DP / 10% Disc / 1% Monthly": {"dp_pct": 10, "disc": 10, "default_monthly": 1.0},
    "20% DP / 10% Disc / 1% Monthly": {"dp_pct": 20, "disc": 10, "default_monthly": 1.0},
    "30% DP / 15% Disc / 1% Monthly": {"dp_pct": 30, "disc": 15, "default_monthly": 1.0},
    "0% DP / 0% Disc / 1% Monthly": {"dp_pct": 0, "disc": 0, "default_monthly": 1.0},
    "20% DP / 2% Disc / 10% @12m / 70% HO": {"dp_pct": 20, "disc": 2, "default_monthly": 0.0, "special_recovery": 10},
    "18% Discount Cash": {"dp_pct": 100, "disc": 18, "default_monthly": 0.0, "is_cash": True},
    "25% Discount Cash": {"dp_pct": 100, "disc": 25, "default_monthly": 0.0, "is_cash": True},
    "30% Discount Cash": {"dp_pct": 100, "disc": 30, "default_monthly": 0.0, "is_cash": True},
    "No Discount - Full within month": {"dp_pct": 100, "disc": 0, "default_monthly": 0.0, "is_cash": True},
    "Plan A (5% DP / 5% Disc)": {"dp_pct": 5, "disc": 5, "default_monthly": 1.0},
    "Plan 2 (10% DP / 5% Disc)": {"dp_pct": 10, "disc": 5, "default_monthly": 1.0},
    "Plan 12 (Cash 40% Disc)": {"dp_pct": 100, "disc": 40, "default_monthly": 0.0, "is_cash": True},
}

@st.cache_data
def load_google_sheet(url):
    try:
        df = pd.read_csv(url)
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return df
    except Exception as e:
        return None

def calculate_ultra_flexible_plan(selling_price, plan_cfg, settings, start_date, handover_date):
    plan = []
    res_fee = 20000
    plan.append({"Milestone": "Reservation Fee", "Date": "Now", "Percent": "-", "Amount": res_fee})
    
    dp_pct = plan_cfg['dp_pct']
    # حساب قيمة الـ DP الكلية ثم طرح مبلغ الحجز منها
    total_dp_amount = (selling_price * (dp_pct / 100))
    remaining_dp_val = total_dp_amount - res_fee
    dp_months = settings['dp_months']
    
    # توزيع المتبقي من المقدم (DP)
    if dp_pct > 0:
        if dp_months > 1:
            for i in range(dp_months):
                d = start_date + relativedelta(months=i)
                plan.append({"Milestone": f"DP Installment {i+1}", "Date": d.strftime("%b-%y"), "Percent": f"{(dp_pct/dp_months):.1f}%", "Amount": max(0, remaining_dp_val / dp_months)})
        else:
            plan.append({"Milestone": "1st Installment (DP Balance)", "Date": start_date.strftime("%b-%y"), "Percent": f"{dp_pct}%", "Amount": max(0, remaining_dp_val)})

    # معالجة الخطط الخاصة (مثل 70/10/20)
    if "special_recovery" in plan_cfg:
        recovery_date = start_date + relativedelta(months=12)
        recovery_pct = plan_cfg["special_recovery"]
        plan.append({"Milestone": "Recovery Payment (12th Month)", "Date": recovery_date.strftime("%b-%y"), "Percent": f"{recovery_pct}%", "Amount": selling_price * (recovery_pct / 100)})

    # الأقساط الشهرية العادية (إذا وجدت)
    if not plan_cfg.get("is_cash", False) and settings['monthly_pct'] > 0:
        monthly_pct = settings['monthly_pct'] / 100
        curr_d = start_date + relativedelta(months=max(1, dp_months))
        
        while curr_d < handover_date:
            # معالجة دفعات التعافي (Recovery) الإضافية من الإعدادات
            if settings['recovery_freq'] > 0:
                months_diff = (curr_d.year - start_date.year) * 12 + curr_d.month - start_date.month
                if months_diff > 0 and months_diff % settings['recovery_freq'] == 0:
                    recovery_amt = selling_price * (settings['recovery_pct'] / 100)
                    plan.append({"Milestone": "Recovery Payment", "Date": curr_d.strftime("%b-%y"), "Percent": f"{settings['recovery_pct']}%", "Amount": recovery_amt})
            
            amt = selling_price * monthly_pct
            plan.append({"Milestone": "Monthly Installment", "Date": curr_d.strftime("%b-%y"), "Percent": f"{settings['monthly_pct']}%", "Amount": amt})
            curr_d += relativedelta(months=1)

    # حساب إجمالي الأقساط (Total Installment) قبل دفعة الاستلام
    total_installments_sum = sum(item['Amount'] for item in plan)
    plan.append({"Milestone": "TOTAL INSTALLMENT", "Date": "-", "Percent": "-", "Amount": total_installments_sum})

    # دفعة الاستلام النهائية
    handover_amt = selling_price - total_installments_sum
    if handover_amt > 1:
        plan.append({"Milestone": "Final Handover", "Date": handover_date.strftime("%b-%y"), "Percent": "Balance", "Amount": handover_amt})
    
    return plan

def create_sales_offer_pdf(unit_data, financials, schedule, layout_url, plan_name, project_name):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image(LOGO_URL, x=10, y=8, w=35)
    except: pass
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 15, f"SALES OFFER - {project_name}", ln=True, align='C')
    pdf.ln(5)

    # ... (نفس كود الصور والمواصفات السابق) ...
    pdf.set_xy(10, 35)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(110, 8, " UNIT SPECIFICATIONS", 0, 1, 'L', True)
    pdf.set_font("Arial", size=10); pdf.set_text_color(0)
    specs = [
        f"Unit No: {unit_data.get('Plot + Unit No.', 'N/A')}",
        f"Unit Type: {unit_data.get('UNIT TYPE', 'N/A')}",
        f"Total Area: {unit_data.get('Total Area (Sq.ft)', '0')} SQFT",
    ]
    for spec in specs: pdf.cell(110, 6, f" {spec}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11); pdf.set_fill_color(240, 240, 240)
    pdf.cell(110, 8, f" FINANCIAL SUMMARY - {plan_name}", 0, 1, 'L', True)
    pdf.set_font("Arial", size=10)
    pdf.cell(60, 6, "Total Selling Price:", 0); pdf.cell(50, 6, f"{financials['selling_price']:,.2f} AED", 0, 1, 'R')
    
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(44, 62, 80); pdf.set_text_color(255, 255, 255)
    pdf.cell(60, 10, " Milestone", 1, 0, 'L', True); pdf.cell(40, 10, " Date", 1, 0, 'C', True)
    pdf.cell(30, 10, " %", 1, 0, 'C', True); pdf.cell(60, 10, " Amount (AED)", 1, 1, 'R', True)

    pdf.set_text_color(0); pdf.set_font("Arial", size=9)
    for row in schedule:
        # تمييز سطر الإجمالي في الـ PDF
        if row['Milestone'] == "TOTAL INSTALLMENT":
            pdf.set_font("Arial", 'B', 9); pdf.set_fill_color(230, 230, 230)
            fill = True
        else:
            pdf.set_font("Arial", size=9); fill = False
            
        pdf.cell(60, 8, f" {row['Milestone']}", 1, 0, 'L', fill)
        pdf.cell(40, 8, f" {row['Date']}", 1, 0, 'C', fill)
        pdf.cell(30, 8, f" {row['Percent']}", 1, 0, 'C', fill)
        pdf.cell(60, 8, f"{row['Amount']:,.2f} ", 1, 1, 'R', fill)
    return pdf.output(dest='S')

# --- واجهة التطبيق ---
st.set_page_config(page_title="Reportage Smart Agent", layout="wide")
st.title("🏗️ Reportage AI Sales Agent")

with st.sidebar:
    st.header("🏢 Project & Settings")
    selected_project = st.selectbox("Select Project:", list(PROJECTS_DATABASE.keys()))
    df_inventory = load_google_sheet(PROJECTS_DATABASE[selected_project])
    df_photos = load_google_sheet(PHOTO_BANK_URL)
    
    st.divider()
    selected_plan = st.selectbox("Base Payment Plan:", list(ALL_PLANS.keys()))
    
    # ضبط الإعدادات تلقائياً بناءً على نوع الخطة
    plan_info = ALL_PLANS[selected_plan]
    default_m_pct = plan_info.get("default_monthly", 1.0)
    
    extra_disc = st.number_input("Extra Discount %", 0.0, 15.0, 0.0, step=0.5)
    
    st.subheader("Customizations")
    m_pct = st.number_input("Monthly Installment %", 0.0, 5.0, default_m_pct, step=0.1)
    dp_m = st.number_input("DP Split (Months):", 1, 24, 1)
    r_freq = st.selectbox("Recovery Every (Months):", [0, 6, 12])
    r_pct = st.number_input("Recovery Amount %", 0.0, 20.0, 0.0)

if df_inventory is not None:
    unit_id = st.selectbox("Select Unit Number:", df_inventory['Plot + Unit No.'].unique())
    unit_data = df_inventory[df_inventory['Plot + Unit No.'] == unit_id].iloc[0]

    # الحسابات المالية
    parking_price = float(str(unit_data.get('parking', '0')).replace(',', ''))
    u_price = float(str(unit_data.get('Original Price (AED)', '0')).replace(',', ''))
    
    total_disc_pct = plan_info['disc'] + extra_disc
    disc_val = u_price * (total_disc_pct / 100)
    selling_price = (u_price - disc_val) + parking_price
    
    h_date_str = str(unit_data.get('Handover Date', '2029-09-01'))
    try: handover_finish_date = pd.to_datetime(h_date_str).date()
    except: handover_finish_date = date(2029, 9, 1)

    financials = {'u_price': u_price, 'disc_pct': total_disc_pct, 'disc_val': disc_val, 'parking': parking_price, 'selling_price': selling_price}
    settings = {'dp_months': dp_m, 'monthly_pct': m_pct, 'recovery_freq': r_freq, 'recovery_pct': r_pct}
    
    schedule = calculate_ultra_flexible_plan(selling_price, plan_info, settings, date.today(), handover_finish_date)

    # العرض
    st.divider()
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(f"📋 Details: {selected_project} - {unit_id}")
        
        # تنسيق الجدول للعرض بتمييز صف الإجمالي
        df_display = pd.DataFrame(schedule)
        def highlight_total(s):
            return ['background-color: #f0f2f6; font-weight: bold' if s.Milestone == "TOTAL INSTALLMENT" else '' for _ in s]
        
        st.dataframe(df_display.style.format({"Amount": "{:,.2f}"}).apply(highlight_total, axis=1), use_container_width=True)
        
    with col2:
        st.metric("Total Selling Price", f"{selling_price:,.2f} AED")
        st.metric("Total Discount", f"{total_disc_pct}%")
            
        pdf_bytes = create_sales_offer_pdf(unit_data, financials, schedule, None, selected_plan, selected_project)
        st.download_button(label="Download Official PDF", data=bytes(pdf_bytes), file_name=f"Offer_{selected_project}_{unit_id}.pdf", mime="application/pdf", use_container_width=True)
else:
    st.error("Please check your Google Sheets connectivity.")

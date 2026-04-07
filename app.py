import streamlit as st
import pandas as pd
from fpdf import FPDF
import requests
from io import BytesIO
from datetime import date
from dateutil.relativedelta import relativedelta

# --- روابط جوجل شيت (استبدلها بروابطك) ---
SILA_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=0&single=true&output=csv"
PHOTO_BANK_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1714647206&single=true&output=csv"
LOGO_URL = "https://i.ibb.co/3sbsK2S/Reportage-Logo.png" # مثال للوجو ريبورتاج

# --- قاموس الخطط الأساسية ---
ALL_PLANS = {
    "Plan A (5% DP / 5% Disc)": {"dp_pct": 5, "disc": 5},
    "Plan 2 (10% DP / 5% Disc)": {"dp_pct": 10, "disc": 5},
    "Plan 7 (20% DP / 15% Disc)": {"dp_pct": 20, "disc": 15},
    "Plan 11 (30% DP / 5% Disc)": {"dp_pct": 30, "disc": 5},
    "Plan 12 (Cash 40% Disc)": {"dp_pct": 100, "disc": 40},
    "Plan 15 (20/80)": {"dp_pct": 20, "disc": 0}
}

# --- 1. دالة تحميل البيانات ---
@st.cache_data
def load_google_sheet(url):
    try:
        df = pd.read_csv(url)
        # هذا السطر الجديد يمسح المسافات الزائدة من الأسماء لضمان المطابقة
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return df
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات: {e}")
        return None

# --- 2. دالة الحسابات المالية (الذكية) ---
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
                plan.append({"Milestone": "Recovery Payment", "Date": curr_d.strftime("%b-%y"), "Percent": f"{settings['recovery_pct']}%", "Amount": recovery_amt})

        amt = selling_price * monthly_pct
        if amt > 0:
            plan.append({"Milestone": "Monthly Installment", "Date": curr_d.strftime("%b-%y"), "Percent": f"{settings['monthly_pct']}%", "Amount": amt})
        curr_d += relativedelta(months=1)

    total_paid = sum(item['Amount'] for item in plan)
    handover_amt = selling_price - total_paid
    if handover_amt > 1:
        plan.append({"Milestone": "Final Handover", "Date": handover_date.strftime("%b-%y"), "Percent": "Balance", "Amount": handover_amt})
            
    return plan

# --- 3. دالة إنشاء PDF ---
def create_sales_offer_pdf(unit_data, financials, schedule, layout_url, plan_name):
    pdf = FPDF()
    pdf.add_page()
    
    # Header & Logo
    try:
        # إضافة صورة المخطط (Layout) في الجانب الأيمن
    if layout_url and str(layout_url) != 'nan':
        try:
            response = requests.get(layout_url, timeout=10)
            img_data = BytesIO(response.content)
            # x=135 (يمين), y=40 (تحت اللوجو), w=60 (العرض)
            pdf.image(img_data, x=135, y=40, w=60)
        except Exception as e:
            st.warning(f"تعذر إضافة الصورة للـ PDF: {e}")
    except: pass
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 15, "SALES OFFER - SILA MASDAR", ln=True, align='C')
    pdf.ln(5)

    # Layout Image
    if layout_url and str(layout_url) != 'nan':
        try:
            response = requests.get(layout_url)
            img_data = BytesIO(response.content)
            pdf.image(img_data, x=135, y=35, w=60)
        except: pass

    # Unit Specs
    pdf.set_xy(10, 35)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(110, 8, " UNIT SPECIFICATIONS", 0, 1, 'L', True)
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(0)
    
    specs = [
        f"Unit No: {unit_data.get('Plot + Unit No.', '')}",
        f"Type: {unit_data.get('UNIT TYPE', '')}",
        f"Bedrooms: {unit_data.get('Bedrooms', '')}",
        f"Sub-type: {unit_data.get('Sub-type', '')}",
        f"Total Area: {unit_data.get('Total Area (Sq.ft)', '')} SQFT",
        f"View: {unit_data.get('View', '')}"
    ]
    for spec in specs:
        pdf.cell(110, 6, f" {spec}", ln=True)
    pdf.ln(5)

    # Financial Summary
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(110, 8, f" FINANCIAL SUMMARY - {plan_name}", 0, 1, 'L', True)
    pdf.set_font("Arial", size=10)
    
    pdf.cell(60, 6, "Original Price:", 0)
    pdf.cell(50, 6, f"{financials['u_price']:,.2f} AED", 0, 1, 'R')
    pdf.cell(60, 6, f"Discount ({financials['disc_pct']}%):", 0)
    pdf.cell(50, 6, f"- {financials['disc_val']:,.2f} AED", 0, 1, 'R')
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(60, 6, "Selling Price (Incl. Parking):", 0)
    pdf.cell(50, 6, f"{financials['selling_price']:,.2f} AED", 0, 1, 'R')
    pdf.ln(8)

    # Schedule Table
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(44, 62, 80)
    pdf.set_text_color(255)
    pdf.cell(60, 8, " Milestone", 1, 0, 'L', True)
    pdf.cell(40, 8, " Date", 1, 0, 'C', True)
    pdf.cell(30, 8, " %", 1, 0, 'C', True)
    pdf.cell(60, 8, " Amount (AED)", 1, 1, 'R', True)

    pdf.set_text_color(0)
    pdf.set_font("Arial", size=9)
    for row in schedule:
        pdf.cell(60, 7, f" {row['Milestone']}", 1)
        pdf.cell(40, 7, f" {row['Date']}", 1, 0, 'C')
        pdf.cell(30, 7, f" {row['Percent']}", 1, 0, 'C')
        pdf.cell(60, 7, f"{row['Amount']:,.2f} ", 1, 1, 'R')
        
    return pdf.output(dest='S')

# --- 4. واجهة التطبيق (Streamlit UI) ---
st.set_page_config(page_title="Reportage Smart Agent", layout="wide")
st.title("🏗️ Reportage AI Sales Agent")

df_inventory = load_google_sheet(SILA_SHEET_URL)
df_photos = load_google_sheet(PHOTO_BANK_URL)

if df_inventory is not None and df_photos is not None:
    # القائمة الجانبية (لوحة التحكم المالية)
    with st.sidebar:
        st.header("⚙️ Financial Settings")
        selected_plan = st.selectbox("Base Payment Plan:", list(ALL_PLANS.keys()))
        extra_disc = st.number_input("Extra Discount %", 0.0, 15.0, 0.0, step=0.5)
        
        st.divider()
        st.subheader("Customizations")
        m_pct = st.number_input("Monthly Installment %", 0.0, 5.0, 1.0, step=0.1)
        dp_m = st.number_input("DP Split (Months):", 1, 24, 1)
        r_freq = st.selectbox("Recovery Every (Months):", [0, 6, 12])
        r_pct = st.number_input("Recovery Amount %", 0.0, 20.0, 0.0)

    # اختيار الوحدة من المخزون
    unit_id = st.selectbox("Select Unit Number:", df_inventory['Plot + Unit No.'].unique())
    unit_data = df_inventory[df_inventory['Plot + Unit No.'] == unit_id].iloc[0]

    # الحسابات المالية
    # نستخدم Original Price (AED) كما هو مكتوب في ملفك
    # السطر المحدث لتجنب مشكلة الفواصل
    raw_price = str(unit_data.get('Original Price (AED)', '0'))
    u_price = float(raw_price.replace(',', ''))
    total_disc_pct = ALL_PLANS[selected_plan]['disc'] + extra_disc
    disc_val = u_price * (total_disc_pct / 100)
    selling_price = (u_price - disc_val) + 40000 # إضافة الباركينج 40 ألف
    
    financials = {
        'u_price': u_price, 
        'disc_pct': total_disc_pct, 
        'disc_val': disc_val, 
        'selling_price': selling_price
    }
    
    settings = {'dp_months': dp_m, 'monthly_pct': m_pct, 'recovery_freq': r_freq, 'recovery_pct': r_pct}
    
    # إنشاء الجدول
    schedule = calculate_ultra_flexible_plan(selling_price, ALL_PLANS[selected_plan], settings, date.today(), date(2029, 9, 1))
    df_sched = pd.DataFrame(schedule)

    # البحث عن الصورة
     # منطق البحث عن الصورة (تأكد من مطابقة أسماء الأعمدة في ملفك)
   match = df_photos[
      (df_photos['Project'] == "SILA") & 
      (df_photos['Bedrooms'] == str(unit_data['Bedrooms']).strip()) & 
      (df_photos['Sub-type'] == str(unit_data['Sub-type']).strip())
      ]

   if not match.empty:
      layout_url = match.iloc[0]['Layout_URL']
      st.image(layout_url, caption=f"Layout for {unit_data['Sub-type']}", width=500)
   else:
      # هذا السطر سيظهر لك في الموقع ليخبرك أين الخطأ بالضبط
      st.error(f"⚠️ لم يتم العثور على صورة في Photo_Bank للمشروع: SILA، الغرف: {unit_data['Bedrooms']}، النوع: {unit_data['Sub-type']}")
   layout_url = match.iloc[0]['Layout_URL'] if not match.empty else None

    # --- عرض البيانات في الموقع ---
    st.divider()
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📋 Unit Details & Financials")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Type", unit_data['UNIT TYPE'])
        m2.metric("Bedrooms", unit_data['Bedrooms'])
        m3.metric("Selling Price", f"{selling_price:,.0f} AED")
        m4.metric("Total Discount", f"{total_disc_pct}%")
        
        st.dataframe(df_sched.style.format({"Amount": "{:,.2f}"}), use_container_width=True)
        
    with col2:
        if layout_url and str(layout_url) != 'nan':
            st.image(layout_url, caption=f"Layout: {unit_data['Bedrooms']} - {unit_data['Sub-type']}", use_column_width=True)
        else:
            st.info("No Layout Image found for this unit type.")
            
        st.write("### 📥 Export Offer")
        # زر استخراج الـ PDF
        pdf_bytes = create_sales_offer_pdf(unit_data, financials, schedule, layout_url, selected_plan)
        st.download_button(
            label="Download Official PDF",
            data=bytes(pdf_bytes),
            file_name=f"Reportage_SILA_{unit_id}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
else:
    st.warning("Please configure the Google Sheets URLs at the top of the code.")

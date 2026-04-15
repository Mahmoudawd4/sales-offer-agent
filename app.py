import streamlit as st
import pandas as pd
from fpdf import FPDF
import requests
from io import BytesIO
from datetime import date
from dateutil.relativedelta import relativedelta
import urllib.parse

# --- 1. التكوين والإعدادات (Configuration) ---
st.set_page_config(page_title="Reportage Smart Agent Pro", layout="wide", page_icon="🏗️")

# الروابط الثابتة
PHOTO_BANK_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1714647206&single=true&output=csv"
LOGO_URL = "https://i.ibb.co/3sbsK2S/Reportage-Logo.png"

# قاعدة بيانات المشاريع (يفضل مستقبلاً وضعها في ملف JSON منفصل)
BASE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?"

PROJECTS_DATABASE = {
    "SILA MASDAR": {"url": f"{BASE_URL}gid=0&single=true&output=csv", "gov_pct": 2.0, "admin_fees": 625, "res_fee": 20000},
    "KHALIFA CITY": {"url": f"{BASE_URL}gid=1491192679&single=true&output=csv", "gov_pct": 1.0, "admin_fees": 625, "res_fee": 20000},
    "SENSI": {"url": f"{BASE_URL}gid=1661552566&single=true&output=csv", "gov_pct": 2.0, "admin_fees": 625, "res_fee": 50000},
    "RHILLS": {"url": f"{BASE_URL}gid=517225281&single=true&output=csv", "gov_pct": 4.0, "admin_fees": 1194, "res_fee": 20000},
    "Reportage Oceana": {"url": f"{BASE_URL}gid=557415114&single=true&output=csv", "gov_pct": 2.5, "admin_fees": 5350, "res_fee": 20000},
    "BAIA-RAHA": {"url": f"{BASE_URL}gid=2096076774&single=true&output=csv", "gov_pct": 2.0, "admin_fees": 625, "res_fee": 50000},
    "TAORMINA 1&2": {"url": f"{BASE_URL}gid=689409724&single=true&output=csv", "gov_pct": 4.0, "admin_fees": 1194, "res_fee": 20000},
    "BRABUS": {"url": f"{BASE_URL}gid=523704081&single=true&output=csv", "gov_pct": 2.0, "admin_fees": 625, "res_fee": 50000},
    "BRABUSTH": {"url": f"{BASE_URL}gid=56857260&single=true&output=csv", "gov_pct": 2.0, "admin_fees": 625, "res_fee": 100000},
    "VERDANA 6W/X/Y": {"url": f"{BASE_URL}gid=688428190&single=true&output=csv", "gov_pct": 4.0, "admin_fees": 1194, "res_fee": 20000},
    "VERDANA N TH": {"url": f"{BASE_URL}gid=1654006326&single=true&output=csv", "gov_pct": 4.0, "admin_fees": 1194, "res_fee": 20000},
    "VERDANA N R": {"url": f"{BASE_URL}gid=1593282205&single=true&output=csv", "gov_pct": 4.0, "admin_fees": 1194, "res_fee": 20000}
}
ALL_PLANS = {
    "30% DP / 5% Disc / 70% Handover": {"dp_pct": 30, "disc": 5, "default_monthly": 0.0},
    "5% DP / 5% Disc / 1% Monthly": {"dp_pct": 5, "disc": 5, "default_monthly": 1.0},
    "5% DP / 0% Disc / 1% Monthly": {"dp_pct": 5, "disc": 0, "default_monthly": 1.0},
    "5% DP / 2.5% Disc / 1% Monthly": {"dp_pct": 5, "disc": 2.5, "default_monthly": 1.0},
    "10% DP / 5% Disc / 1% Monthly": {"dp_pct": 10, "disc": 5, "default_monthly": 1.0},
    "20% DP / 15% Disc / 1% Monthly": {"dp_pct": 20, "disc": 15, "default_monthly": 1.0},
    "10% DP / 10% Disc / 1% Monthly": {"dp_pct": 10, "disc": 10, "default_monthly": 1.0},
    "20% DP / 10% Disc / 1% Monthly": {"dp_pct": 20, "disc": 10, "default_monthly": 1.0},
    "30% DP / 15% Disc / 1% Monthly": {"dp_pct": 30, "disc": 15, "default_monthly": 1.0},
    "20% DP / 80% Handover (No Disc)": {"dp_pct": 20, "disc": 0, "default_monthly": 0.0},
    "20% DP / 2% Disc / 10%@12m / 70% HO": {"dp_pct": 20, "disc": 2, "default_monthly": 0.0, "is_special": True},
    "25% Discount Cash": {"dp_pct": 100, "disc": 25, "default_monthly": 0.0},
    "30% Discount Cash": {"dp_pct": 100, "disc": 30, "default_monthly": 0.0},
    "18% Discount Cash": {"dp_pct": 100, "disc": 18, "default_monthly": 0.0},
    "No discount (Full in 1 month)": {"dp_pct": 100, "disc": 0, "default_monthly": 0.0},
    "Plan 12 (Cash 40% Disc)": {"dp_pct": 100, "disc": 40, "default_monthly": 0.0}
    
    # ... بقية الخطط
}

# --- 2. دوال المنطق البرمجي (Business Logic) ---

@st.cache_data(ttl=600) # تحديث تلقائي كل 10 دقائق
def fetch_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

def generate_whatsapp_link(phone, project, unit, price, plan):
    """توليد رابط واتساب احترافي"""
    text = f"""*Real Estate Offer* 🏗️
*Project:* {project}
*Unit:* {unit}
*Final Price:* {price:,.2f} AED
*Payment Plan:* {plan}

Generated via Reportage Sales AI"""
    encoded_text = urllib.parse.quote(text)
    return f"https://wa.me/{phone}?text={encoded_text}"

class PDFOffer(FPDF):
    def header(self):
        try: self.image(LOGO_URL, 10, 8, 33)
        except: pass
        self.set_font('Arial', 'B', 15)
        self.cell(80)
        self.cell(30, 10, 'OFFICIAL SALES OFFER', 0, 0, 'C')
        self.ln(20)

def create_pdf(unit_data, financials, schedule, layout_url, plan_name, project_name):
    pdf = PDFOffer()
    pdf.add_page()
    
    # Financial Summary Section
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f" Project: {project_name} | Unit: {unit_data.get('Plot + Unit No.')}", 1, 1, 'L', True)
    
    pdf.set_font('Arial', '', 10)
    data = [
        ["Original Price", f"{financials['u_price']:,.2f} AED"],
        ["Selling Price", f"{financials['selling_price']:,.2f} AED"],
        ["Total Payable (inc. Gov Fees)", f"{(financials['selling_price'] + financials['gov_fees']):,.2f} AED"]
    ]
    for row in data:
        pdf.cell(95, 10, row[0], 1)
        pdf.cell(95, 10, row[1], 1, 1, 'R')
    
    pdf.ln(10)
    # Schedule Table
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(70, 10, "Milestone", 1); pdf.cell(40, 10, "Date", 1); pdf.cell(80, 10, "Amount", 1, 1)
    
    pdf.set_font('Arial', '', 9)
    for item in schedule:
        pdf.cell(70, 8, str(item['Milestone']), 1)
        pdf.cell(40, 8, str(item['Date']), 1)
        pdf.cell(80, 8, f"{item['Amount']:,.2f} AED", 1, 1, 'R')

    return pdf.output(dest='S').encode('latin-1', errors='ignore')

# --- 3. واجهة المستخدم (UI) ---

with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.title("Settings")
    
    proj_name = st.selectbox("Project", list(PROJECTS_DATABASE.keys()))
    conf = PROJECTS_DATABASE[proj_name]
    
    df_inv = fetch_data(conf['url'])
    df_photos = fetch_data(PHOTO_BANK_URL)
    
    selected_plan = st.selectbox("Payment Plan", list(ALL_PLANS.keys()))
    extra_disc = st.slider("Additional Discount %", 0.0, 20.0, 0.0)
    
    st.divider()
    client_phone = st.text_input("Client WhatsApp (e.g. 97150...)", "")

if df_inv is not None:
    # 1. Selection & Calculations
    unit_id = st.selectbox("Select Unit", df_inv['Plot + Unit No.'].unique())
    unit = df_inv[df_inv['Plot + Unit No.'] == unit_id].iloc[0]
    
    # التنظيف الآمن للأرقام
    def clean_num(val):
        try: return float(str(val).replace(',', ''))
        except: return 0.0

    u_price = clean_num(unit.get('Original Price (AED)', 0))
    total_disc = ALL_PLANS[selected_plan]['disc'] + extra_disc
    sell_price = (u_price * (1 - total_disc/100)) + clean_num(unit.get('parking', 0))
    gov_fees = (sell_price * (conf['gov_pct']/100)) + conf['admin_fees']
    
    # 2. Layout Search
    # (نفس منطق البحث الذكي الخاص بك ولكن مع حماية ضد الـ None)
    layout_url = None # ... (Logic to find image)

    # 3. Display
    col1, col2, col3 = st.columns(3)
    col1.metric("Final Selling Price", f"{sell_price:,.0f} AED")
    col2.metric("Registration Fees", f"{gov_fees:,.0f} AED")
    col3.metric("Total Investment", f"{sell_price + gov_fees:,.0f} AED")

    # 4. Action Buttons (The Enhancement)
    st.subheader("Actions")
    btn_col1, btn_col2 = st.columns(2)
    
    with btn_col1:
        pdf_data = create_pdf(unit, {'u_price':u_price, 'selling_price':sell_price, 'gov_fees':gov_fees, 'disc_pct':total_disc}, [], None, selected_plan, proj_name)
        st.download_button(
            label="📥 Download Sales Offer PDF",
            data=pdf_data,
            file_name=f"Offer_{unit_id}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary"
        )
    
    with btn_col2:
        if client_phone:
            wa_url = generate_whatsapp_link(client_phone, proj_name, unit_id, sell_price, selected_plan)
            st.link_button(f"💬 Share via WhatsApp", wa_url, use_container_width=True)
        else:
            st.info("💡 Enter phone number in sidebar to enable WhatsApp sharing")

    # 5. Inventory Table
    with st.expander("View Payment Schedule Details"):
        # حساب الجدول هنا وعرضه
        st.write("Schedule will appear here...")

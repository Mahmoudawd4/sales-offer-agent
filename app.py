import streamlit as st

import pandas as pd


from fpdf import FPDF



import requests



from io import BytesIO



from datetime import date



from dateutil.relativedelta import relativedelta







# --- 1. قاعدة بيانات المشاريع ---



PROJECTS_DATABASE = {



    "SILA MASDAR": {



        "url": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=0&single=true&output=csv",



        "gov_pct": 2.0,



        "admin_fees": 625,



        "res_fee": 20000



    },



    "KHALIFA CITY": {



        "url": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1491192679&single=true&output=csv",



        "gov_pct": 1.0,



        "admin_fees": 625,



        "res_fee": 20000



    },



    "SENSI": {



        "url": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1661552566&single=true&output=csv", 



        "gov_pct": 2.0,



        "admin_fees": 625,



        "res_fee": 50000



    },



    "RHILLS": {



        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=517225281&single=true&output=csv",



        "gov_pct": 4.0,



        "admin_fees": 1194,



        "res_fee": 20000 



    }
    ,



    "Reportage Oceana": {



        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=557415114&single=true&output=csv",



        "gov_pct": 2.5,



        "admin_fees": 5350,



        "res_fee": 20000 



    }
    ,



    "BAIA-RAHA": {



        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=2096076774&single=true&output=csv",



        "gov_pct": 2,



        "admin_fees": 625,



        "res_fee": 50000 



    }
    ,



    "TAORMINA1 and TAORMINA2": {



        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=689409724&single=true&output=csv",



        "gov_pct": 4.0,



        "admin_fees": 1194,



        "res_fee": 20000 



    }
    ,



    "BRABUS": {



        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=523704081&single=true&output=csv",



        "gov_pct": 2.0,



        "admin_fees": 625,



        "res_fee": 50000 



    }
    ,
    "BRABUSTH": {



        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=56857260&single=true&output=csv",



        "gov_pct": 2.0,



        "admin_fees": 625,



        "res_fee": 100000 



    }
    ,



    "VERDANA 6W & 6X & 6Y": {



        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=688428190&single=true&output=csv",



        "gov_pct": 4.0,



        "admin_fees": 1194,



        "res_fee": 20000 



    }
,
    "VERDANA N TH": {
        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1654006326&single=true&output=csv",
        "gov_pct": 4.0,
        "admin_fees": 1194,
        "res_fee": 20000 
    }
    ,
    "VERDANA N R": {
        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1593282205&single=true&output=csv",
        "gov_pct": 4.0,
        "admin_fees": 1194,
        "res_fee": 20000 
    }
        ,
    "VERDANA 10 R": {
        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=833822872&single=true&output=csv",
        "gov_pct": 4.0,
        "admin_fees": 1194,
        "res_fee": 20000 
    }
    ,
    "VERDANA 9 R": {
        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1641737645&single=true&output=csv",
        "gov_pct": 4.0,
        "admin_fees": 1194,
        "res_fee": 20000 
    }
    ,
    "VERDANA 8 R": {
        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=2138617608&single=true&output=csv",
        "gov_pct": 4.0,
        "admin_fees": 1194,
        "res_fee": 20000 
    }
    ,
    "VERDANA 7 R": {
        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1423929833&single=true&output=csv",
        "gov_pct": 4.0,
        "admin_fees": 1194,
        "res_fee": 20000 
    }
,
    "VERDANA 6 R": {
        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=290574832&single=true&output=csv",
        "gov_pct": 4.0,
        "admin_fees": 1194,
        "res_fee": 20000 
    },
    "VERDANA 5 R": {
        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1269333085&single=true&output=csv",
        "gov_pct": 4.0,
        "admin_fees": 1194,
        "res_fee": 20000 
    }
    ,
    ,
    "MANAGEMENT UNITS": {
        "url":"https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1704395837&single=true&output=csv",
        "gov_pct": 2.0,
        "admin_fees": 5625,
        "res_fee": 20000 
    }
}







PHOTO_BANK_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSLDSBkzA1ZpD1qCRFjl4TiNWldYobalUdgwADyljTFkWMJrvVXajgFxegKWDr2SA-UcuAc8mGonW36/pub?gid=1714647206&single=true&output=csv"



LOGO_URL = "https://i.ibb.co/3sbsK2S/Reportage-Logo.png"







# --- 2. قاموس الخطط المحدث ---



ALL_PLANS = {



    "30% DP / 5% Disc / 70% Handover": {"dp_pct": 30, "disc": 5, "default_monthly": 0.0},
    "30% DP / 0% Disc / 70% Handover": {"dp_pct": 30, "disc": 0, "default_monthly": 0.0},



    "5% DP / 5% Disc / 1% Monthly": {"dp_pct": 5, "disc": 5, "default_monthly": 1.0},



    "5% DP / 0% Disc / 1% Monthly": {"dp_pct": 5, "disc": 0, "default_monthly": 1.0},



    "5% DP / 2.5% Disc / 1% Monthly": {"dp_pct": 5, "disc": 2.5, "default_monthly": 1.0},



    "10% DP / 5% Disc / 1% Monthly": {"dp_pct": 10, "disc": 5, "default_monthly": 1.0},
    "10% DP / 0% Disc / 1% Monthly": {"dp_pct": 10, "disc": 0, "default_monthly": 1.0},



    "20% DP / 15% Disc / 1% Monthly": {"dp_pct": 20, "disc": 15, "default_monthly": 1.0},
    "20% DP / 5% Disc / 1% Monthly": {"dp_pct": 20, "disc": 5, "default_monthly": 1.0},



    "10% DP / 10% Disc / 1% Monthly": {"dp_pct": 10, "disc": 10, "default_monthly": 1.0},



    "20% DP / 10% Disc / 1% Monthly": {"dp_pct": 20, "disc": 10, "default_monthly": 1.0},



    "30% DP / 15% Disc / 1% Monthly": {"dp_pct": 30, "disc": 15, "default_monthly": 1.0},
    "30% DP / 10% Disc / 1% Monthly": {"dp_pct": 30, "disc": 10, "default_monthly": 1.0},



    "20% DP / 80% Handover (No Disc)": {"dp_pct": 20, "disc": 0, "default_monthly": 0.0},



    "20% DP / 2% Disc / 10%@12m / 70% HO": {"dp_pct": 20, "disc": 2, "default_monthly": 0.0, "is_special": True},



    "25% Discount Cash": {"dp_pct": 100, "disc": 25, "default_monthly": 0.0},



    "30% Discount Cash": {"dp_pct": 100, "disc": 30, "default_monthly": 0.0},
    "35% Discount Cash": {"dp_pct": 100, "disc": 35, "default_monthly": 0.0},



    "18% Discount Cash": {"dp_pct": 100, "disc": 18, "default_monthly": 0.0},



    "No discount (Full in 1 month)": {"dp_pct": 100, "disc": 0, "default_monthly": 0.0},



    "40% DISCOUNT Plan 12 (Cash 40% Disc)": {"dp_pct": 100, "disc": 40, "default_monthly": 0.0}



}







@st.cache_data



def load_google_sheet(url):



    try:



        df = pd.read_csv(url)



        df.columns = df.columns.str.strip() 



        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)



        return df



    except:



        return None







def get_handover_date(unit_data):



    for col in ['Handover Date', 'Handover', 'Completion', 'Completion Date', 'HANDOVER DATE']:



        val = unit_data.get(col)



        if val and str(val).lower() != 'nan':



            try:



                return pd.to_datetime(val).date()



            except:



                continue



    return date(2029, 9, 1) 







def calculate_ultra_flexible_plan(selling_price, plan_cfg, settings, start_date, handover_date, res_fee):



    plan = []



    plan.append({"Milestone": "Reservation Fee (Booking)", "Date": "Now", "Percent": "-", "Amount": res_fee})



    dp_pct = plan_cfg['dp_pct']



    total_dp_val = (selling_price * (dp_pct / 100))



    dp_after_booking = max(0, total_dp_val - res_fee)



    dp_months = settings['dp_months']



    if dp_pct > 0:



        if dp_months > 1:



            for i in range(dp_months):



                d = start_date + relativedelta(months=i)



                plan.append({"Milestone": f"DP Installment {i+1}", "Date": d.strftime("%b-%y"), "Percent": f"{(dp_pct/dp_months):.1f}%", "Amount": dp_after_booking / dp_months})



        else:



            plan.append({"Milestone": "DP Balance Payment", "Date": start_date.strftime("%b-%y"), "Percent": f"{dp_pct}%", "Amount": dp_after_booking})



    if plan_cfg.get("is_special"):



        special_rec_date = start_date + relativedelta(months=12)



        plan.append({"Milestone": "Special Installment (10%)", "Date": special_rec_date.strftime("%b-%y"), "Percent": "10%", "Amount": selling_price * 0.10})



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



    total_inst = sum(item['Amount'] for item in plan)



    plan.append({"Milestone": "TOTAL INSTALLMENT", "Date": "---", "Percent": "---", "Amount": total_inst})



    handover_amt = selling_price - total_inst



    if handover_amt > 1:



        plan.append({"Milestone": "Balance Handover", "Date": handover_date.strftime("%b-%y"), "Percent": "Balance", "Amount": handover_amt})



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



    pdf.set_xy(10, 35)



    pdf.set_fill_color(240, 240, 240)



    pdf.set_font("Arial", 'B', 11)



    pdf.cell(190, 8, " UNIT SPECIFICATIONS", 0, 1, 'L', True)



    pdf.set_font("Arial", size=10); pdf.set_text_color(0)



    pdf.cell(95, 6, f" Unit No: {unit_data.get('Plot + Unit No.', 'N/A')}", 0, 0)



    pdf.cell(95, 6, f" Sub-type: {unit_data.get('Sub-type', 'N/A')}", 0, 1)



    pdf.cell(95, 6, f" Unit Type: {unit_data.get('UNIT TYPE', 'N/A')}", 0, 0)



    pdf.cell(95, 6, f" Total Area: {unit_data.get('Total Area (Sq.ft)', '0')} SQFT", 0, 1)



    pdf.cell(95, 6, f" Bedrooms: {unit_data.get('Bedrooms', 'N/A')}", 0, 0)



    pdf.cell(95, 6, f" View: {unit_data.get('View', 'N/A')}", 0, 1)



    pdf.ln(5)



    pdf.set_font("Arial", 'B', 11); pdf.set_fill_color(240, 240, 240)



    pdf.cell(190, 8, f" FINANCIAL SUMMARY - {plan_name}", 0, 1, 'L', True)



    pdf.set_font("Arial", size=10)



    pdf.cell(100, 6, "Original Price:", 0); pdf.cell(90, 6, f"{financials['u_price']:,.2f} AED", 0, 1, 'R')



    pdf.cell(100, 6, f"Discount ({financials['disc_pct']}%):", 0); pdf.cell(90, 6, f"- {financials['disc_val']:,.2f} AED", 0, 1, 'R')



    pdf.cell(100, 6, "Selling Price:", 0); pdf.cell(90, 6, f"{financials['selling_price']:,.2f} AED", 0, 1, 'R')



    pdf.set_text_color(200, 0, 0)



    pdf.cell(100, 6, "Gov. Fees (Registration):", 0); pdf.cell(90, 6, f"{financials['gov_fees']:,.2f} AED", 0, 1, 'R')



    pdf.set_text_color(0)



    pdf.set_font("Arial", 'B', 10)



    total_all = financials['selling_price'] + financials['gov_fees']



    pdf.cell(100, 8, "Total Amount Payable:", 0); pdf.cell(90, 8, f"{total_all:,.2f} AED", 0, 1, 'R')



    pdf.ln(8)



    pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(44, 62, 80); pdf.set_text_color(255, 255, 255)



    pdf.cell(70, 10, " Milestone", 1, 0, 'L', True); pdf.cell(40, 10, " Date", 1, 0, 'C', True)



    pdf.cell(20, 10, " %", 1, 0, 'C', True); pdf.cell(60, 10, " Amount (AED)", 1, 1, 'R', True)



    pdf.set_text_color(0); pdf.set_font("Arial", size=9)



    for row in schedule:



        if row['Milestone'] == "TOTAL INSTALLMENT":



            pdf.set_font("Arial", 'B', 9); pdf.set_fill_color(220, 220, 220)



            pdf.cell(70, 8, f" {row['Milestone']}", 1, 0, 'L', True)



            pdf.cell(40, 8, f" {row['Date']}", 1, 0, 'C', True)



            pdf.cell(20, 8, f" {row['Percent']}", 1, 0, 'C', True)



            pdf.cell(60, 8, f"{row['Amount']:,.2f} ", 1, 1, 'R', True)



            pdf.set_font("Arial", size=9); pdf.set_fill_color(255, 255, 255)



        else:



            pdf.cell(70, 8, f" {row['Milestone']}", 1)



            pdf.cell(40, 8, f" {row['Date']}", 1, 0, 'C')



            pdf.cell(20, 8, f" {row['Percent']}", 1, 0, 'C')



            pdf.cell(60, 8, f"{row['Amount']:,.2f} ", 1, 1, 'R')



    if layout_url and str(layout_url) != 'nan':



        try:



            res = requests.get(layout_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)



            img_data = BytesIO(res.content)



            pdf.ln(10)



            if pdf.get_y() > 180: pdf.add_page()



            pdf.set_font("Arial", 'B', 12)



            pdf.cell(0, 10, "UNIT LAYOUT", ln=True, align='C')



            pdf.image(img_data, x=30, y=pdf.get_y()+5, w=150)



        except: pass



    return pdf.output(dest='S')







st.set_page_config(page_title="Reportage Smart Agent", layout="wide")



st.title("🏗️ Reportage Sales AI")







with st.sidebar:



    st.header("🏢 Settings")



    selected_project = st.selectbox("Project:", list(PROJECTS_DATABASE.keys()))



    proj_info = PROJECTS_DATABASE[selected_project]



    df_inventory = load_google_sheet(proj_info["url"])



    df_photos = load_google_sheet(PHOTO_BANK_URL)



    selected_plan = st.selectbox("Plan:", list(ALL_PLANS.keys()))



    default_m_pct = ALL_PLANS[selected_plan].get("default_monthly", 1.0)



    extra_disc = st.number_input("Extra Discount %", 0.0, 15.0, 0.0)



    st.subheader("Structure")



    m_pct = st.number_input("Monthly %", 0.0, 5.0, float(default_m_pct))



    dp_m = st.number_input("DP Split (Months):", 1, 24, 1)



    r_freq = st.selectbox("Recovery (Months):", [0, 6, 12])



    r_pct = st.number_input("Recovery %", 0.0, 20.0, 0.0)







if df_inventory is not None:



    unit_id = st.selectbox("Unit:", df_inventory['Plot + Unit No.'].unique())



    unit_data = df_inventory[df_inventory['Plot + Unit No.'] == unit_id].iloc[0]



    



    h_date = get_handover_date(unit_data)



    



    u_price = float(str(unit_data.get('Original Price (AED)', '0')).replace(',', ''))



    total_disc_pct = ALL_PLANS[selected_plan]['disc'] + extra_disc



    selling_price = (u_price * (1 - total_disc_pct/100)) + float(str(unit_data.get('parking', '0')).replace(',', ''))



    gov_fees = (selling_price * (proj_info["gov_pct"] / 100)) + proj_info["admin_fees"]



    



    financials = {'u_price': u_price, 'disc_pct': total_disc_pct, 'disc_val': u_price * (total_disc_pct/100), 'selling_price': selling_price, 'gov_fees': gov_fees}



    settings = {'dp_months': dp_m, 'monthly_pct': m_pct, 'recovery_freq': r_freq, 'recovery_pct': r_pct}



    schedule = calculate_ultra_flexible_plan(selling_price, ALL_PLANS[selected_plan], settings, date.today(), h_date, proj_info["res_fee"])



    



    # --- البحث الذكي عن الصور (Smart Image Search) ---



    layout_url = None



    if df_photos is not None:



        try:



            # 1. نأخذ أول كلمة فقط من المشروع (SILA, KHALIFA, SENSI)



            p_key = selected_project.split()[0].upper()



            



            # 2. تنظيف البيانات من المسافات وعلامات الدوت زيرو (.0)



            df_photos['clean_proj'] = df_photos['Project'].astype(str).str.upper().str.strip()



            df_photos['clean_bed'] = df_photos['Bedrooms'].astype(str).str.replace('.0', '', regex=False).str.strip()



            df_photos['clean_sub'] = df_photos['Sub-type'].astype(str).str.upper().str.strip()



            



            unit_bed = str(unit_data.get('Bedrooms', '')).replace('.0', '').strip()



            unit_sub = str(unit_data.get('Sub-type', '')).upper().strip()







            # المحاولة الأولى: تطابق دقيق (مشروع + غرف + Sub-type)



            match = df_photos[



                (df_photos['clean_proj'].str.contains(p_key)) & 



                (df_photos['clean_bed'] == unit_bed) & 



                (df_photos['clean_sub'] == unit_sub)



            ]



            



            # المحاولة الثانية: لو مفيش تطابق دقيق، هات أي صورة لنفس المشروع ونفس عدد الغرف (تجاهل الـ Sub-type)



            if match.empty:



                match = df_photos[



                    (df_photos['clean_proj'].str.contains(p_key)) & 



                    (df_photos['clean_bed'] == unit_bed)



                ]







            if not match.empty:



                layout_url = match.iloc[0]['Layout_URL']



        except Exception as e: 



            layout_url = None







    st.divider()



    m1, m2, m3 = st.columns(3)



    m1.metric("Selling Price", f"{selling_price:,.2f} AED")



    m2.metric("Gov. Fees", f"{gov_fees:,.2f} AED", delta=f"{h_date.strftime('%b %Y')} Handover")



    m3.metric("Total Payable", f"{selling_price + gov_fees:,.2f} AED")



    



    st.subheader(f"📊 Payment Schedule - {unit_id}")



    c1, c2 = st.columns([3, 1])



    with c1: 



        st.dataframe(pd.DataFrame(schedule).style.format({"Amount": "{:,.2f}"}), use_container_width=True)



    with c2:



        pdf_bytes = create_sales_offer_pdf(unit_data, financials, schedule, layout_url, selected_plan, selected_project)



        st.download_button("Download PDF", data=bytes(pdf_bytes), file_name=f"Offer_{unit_id}.pdf", use_container_width=True, type="primary")



    



    if layout_url:



        st.divider()



        st.subheader("🖼️ Unit Layout")



        _, img_col, _ = st.columns([1, 4, 1])



        with img_col: 



            st.image(layout_url, use_container_width=True)



    else:



        st.info("No Layout found in Photo Bank for this project and bedroom type.")

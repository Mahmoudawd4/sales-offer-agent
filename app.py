import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# إعدادات الصفحة
st.set_page_config(page_title="Reportage Sales Agent", layout="centered")

# --- 1. القواعد المالية لمشروع SILA ---
def calculate_offer(unit_data, discount_pct, plan_type, dp_pct):
    unit_price = float(unit_data['Price'])
    discount_amount = unit_price * (discount_pct / 100)
    price_after_discount = unit_price - discount_amount
    
    # قاعدة الباركينج: 0 للتاونهاوس، 40 ألف للباقي في سيلا
    is_townhouse = "Townhouse" in str(unit_data['UNIT TYPE'])
    parking_fee = 0 if is_townhouse else 40000
    
    selling_price = price_after_discount + parking_fee
    
    # الرسوم الحكومية
    gov_fees = (selling_price * 0.02) + 625
    
    return {
        "unit_price": unit_price,
        "discount_amount": discount_amount,
        "price_after_discount": price_after_discount,
        "parking_fee": parking_fee,
        "selling_price": selling_price,
        "gov_fees": gov_fees
    }

# --- 2. واجهة المستخدم ---
st.title("🤖 Real Estate AI Agent")
st.subheader("Generate Sales Offer for SILA MASDAR")

# رفع ملف الإكسيل (أو الربط بجوجل شيت لاحقاً)
uploaded_file = st.file_uploader("Upload SILA Availability File", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
    
    # اختيار الوحدة
    unit_no = st.selectbox("Select Unit Number:", df['Plot + Unit No.'].unique())
    unit_info = df[df['Plot + Unit No.'] == unit_no].iloc[0]
    
    # إدخال تفاصيل الخصم وخطة الدفع
    col1, col2 = st.columns(2)
    with col1:
        discount = st.number_input("Discount %", value=15.0)
        dp = st.number_input("Down Payment %", value=30.0)
    with col2:
        plan = st.selectbox("Payment Plan", ["Plan 13 (Cash)", "Plan 1 (Installments)", "Custom"])

    # تنفيذ الحسابات
    results = calculate_offer(unit_info, discount, plan, dp)
    
    st.write("---")
    st.write(f"### Selling Price: {results['selling_price']:,.2f} AED")
    
    # زر توليد الـ PDF
    if st.button("Generate Sales Offer PDF"):
        # هنا سنضع كود تصميم الـ PDF ليظهر مثل الملف الذي أرفقته
        st.success("PDF Generated Successfully! (Logic is Ready)")
        # سأعطيك كود الـ PDF التفصيلي في الخطوة القادمة

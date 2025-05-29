#!/usr/bin/env python3
# Kalkulator ROI 5 Tahun untuk Implementasi AI Voice di Rumah Sakit
# Created by: Medical Solutions
# Versi Streamlit 2.0 (2024)

import streamlit as st
from datetime import datetime
import locale
import matplotlib.pyplot as plt
import numpy as np
from contextlib import suppress

# ====================== FUNGSI UTAMA ======================

def setup_locale():
    """Mengatur locale untuk format angka"""
    for loc in ['id_ID.UTF-8', 'en_US.UTF-8', 'C.UTF-8', '']:
        with suppress(locale.Error):
            locale.setlocale(locale.LC_ALL, loc)
            break

def format_currency(amount):
    """Format angka ke mata uang IDR dengan pemisah ribuan"""
    try:
        return locale.currency(amount, symbol=True, grouping=True, international=False)
    except:
        return f"Rp {amount:,.0f}".replace(",", ".")

def calculate_roi(investment, annual_gain, years):
    """Hitung ROI dalam persen untuk X tahun"""
    if investment == 0:
        return float('inf')
    total_gain = annual_gain * years
    return ((total_gain - investment) / investment) * 100

def generate_charts(data):
    """Generate grafik untuk visualisasi data"""
    # Grafik Proyeksi Arus Kas
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    months = 60
    cumulative = [data['monthly_savings'] * m - data['total_investment'] for m in range(1, months+1)]
    ax1.plot(range(1, months+1), cumulative, color='#2E86C1', linewidth=2)
    ax1.set_title('PROYEKSI ARUS KAS KUMULATIF 5 TAHUN')
    st.pyplot(fig1)
    
    # Grafik Perbandingan Penghematan
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    categories = ['Staff Admin', 'No-Show', 'Total']
    savings = [
        data['staff_savings'] * 12,
        data['noshow_savings'] * 12,
        data['annual_savings']
    ]
    ax2.bar(categories, savings, color=['#27AE60', '#F1C40F', '#E74C3C'])
    ax2.set_title('PENGHEMATAN TAHUNAN')
    st.pyplot(fig2)

# ====================== TAMPILAN STREAMLIT ======================

def main():
    # Konfigurasi halaman
    st.set_page_config(
        page_title="Kalkulator ROI AI Voice",
        page_icon="🏥",
        layout="wide"
    )
    
    # CSS kustom
    st.markdown("""
    <style>
    .stButton>button {
        background-color: #2E86C1;
        color: white;
        font-weight: bold;
    }
    .stMetric {
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        padding: 15px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Judul Aplikasi
    st.title("🏥 Kalkulator ROI 5 Tahun untuk AI Voice")
    st.markdown("**Alat untuk menghitung Return on Investment implementasi solusi AI Voice di rumah sakit**")
    
    # ====================== SIDEBAR (INPUT) ======================
    with st.sidebar:
        st.header("⚙️ Parameter Input")
        
        # Input Data Dasar
        st.subheader("Informasi Rumah Sakit")
        hospital_name = st.text_input("Nama Rumah Sakit", "Rumah Sakit ABC")
        hospital_location = st.text_input("Lokasi", "Jakarta")
        
        # Parameter Operasional
        st.subheader("Parameter Operasional")
        col1, col2 = st.columns(2)
        with col1:
            total_staff = st.number_input("Total Staff", min_value=1, value=200)
        with col2:
            admin_staff = st.number_input("Staff Admin", min_value=1, value=20)
        
        monthly_appointments = st.number_input("Janji Temu/Bulan", min_value=1, value=5000)
        noshow_rate = st.slider("Tingkat No-Show (%)", 0.0, 100.0, 15.0) / 100
        
        # Parameter Biaya
        st.subheader("Parameter Biaya")
        avg_salary = st.number_input("Gaji Staff Admin (IDR)", min_value=0, value=8000000)
        revenue_per_appointment = st.number_input("Pendapatan/Janji Temu (IDR)", min_value=0, value=250000)
        
        # Efisiensi
        st.subheader("Efisiensi yang Diharapkan")
        staff_reduction = st.slider("Pengurangan Staff (%)", 0.0, 100.0, 30.0) / 100
        noshow_reduction = st.slider("Pengurangan No-Show (%)", 0.0, 100.0, 40.0) / 100
        
        # Biaya Implementasi
        st.subheader("Biaya Implementasi")
        exchange_rate = st.number_input("Kurs USD-IDR", min_value=1, value=15000)
        setup_cost_usd = st.number_input("Biaya Setup (USD)", min_value=0, value=20000)
        integration_cost_usd = st.number_input("Biaya Integrasi (USD)", min_value=0, value=15000)
        training_cost_usd = st.number_input("Biaya Pelatihan (USD)", min_value=0, value=10000)
        maintenance_cost = st.number_input("Pemeliharaan/Bulan (IDR)", min_value=0, value=5000000)
        
        # Tombol Hitung
        hitung_roi = st.button("🚀 HITUNG ROI", type="primary", use_container_width=True)
    
    # ====================== HASIL PERHITUNGAN ======================
    if hitung_roi:
        # Kalkulasi Dasar
        setup_cost = setup_cost_usd * exchange_rate
        integration_cost = integration_cost_usd * exchange_rate
        training_cost = training_cost_usd * exchange_rate
        total_investment = setup_cost + integration_cost + training_cost
        
        staff_savings = (admin_staff * staff_reduction) * avg_salary
        noshow_savings = (monthly_appointments * noshow_rate * noshow_reduction) * revenue_per_appointment
        total_monthly_savings = staff_savings + noshow_savings - maintenance_cost
        annual_savings = total_monthly_savings * 12
        
        # Payback Period
        payback_period = total_investment / total_monthly_savings if total_monthly_savings > 0 else float('inf')
        
        # Siapkan Data untuk Visualisasi
        report_data = {
            'hospital_name': hospital_name,
            'total_investment': total_investment,
            'monthly_savings': total_monthly_savings,
            'annual_savings': annual_savings,
            'staff_savings': staff_savings,
            'noshow_savings': noshow_savings,
            'payback_period': payback_period
        }
        
        # ====================== TAMPILAN HASIL ======================
        st.header("📊 Hasil Analisis ROI")
        
        # Metrics Utama
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Investasi Awal", format_currency(total_investment))
        with col2:
            st.metric("Penghematan Tahunan", format_currency(annual_savings))
        with col3:
            st.metric("ROI 1 Tahun", f"{calculate_roi(total_investment, annual_savings, 1):.1f}%")
        
        # Grafik
        st.subheader("📈 Visualisasi Data")
        generate_charts(report_data)
        
        # Detail Perhitungan
        with st.expander("🔍 Detail Perhitungan"):
            st.subheader("Komponen Penghematan")
            st.write(f"- Pengurangan biaya staff: {format_currency(staff_savings * 12)}/tahun")
            st.write(f"- Pengurangan no-show: {format_currency(noshow_savings * 12)}/tahun")
            st.write(f"- Biaya pemeliharaan: {format_currency(maintenance_cost * 12)}/tahun")
            
            st.subheader("Breakdown Investasi")
            st.write(f"- Biaya setup: {format_currency(setup_cost)}")
            st.write(f"- Biaya integrasi: {format_currency(integration_cost)}")
            st.write(f"- Biaya pelatihan: {format_currency(training_cost)}")
        
        # Rekomendasi
        st.subheader("🚀 Rekomendasi Implementasi")
        st.write("""
        1. **Fase Persiapan (Bulan 1-3)**  
           - Setup infrastruktur dasar  
           - Pelatihan tim inti  
        
        2. **Fase Implementasi (Bulan 4-6)**  
           - Rollout ke unit prioritas  
           - Integrasi dengan sistem EMR  
        
        3. **Fase Optimisasi (Bulan 7-12)**  
           - Penyempurnaan model AI  
           - Expansi ke seluruh unit
        """)
        
        # Footer
        st.markdown("---")
        st.caption(f"© {datetime.now().year} Medical AI Solutions | Dibuat pada {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ====================== EKSEKUSI APLIKASI ======================
if __name__ == "__main__":
    setup_locale()
    main()
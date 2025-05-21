#!/usr/bin/env python3
# Kalkulator ROI 5 Tahun untuk Implementasi AI Voice di Rumah Sakit - Versi Streamlit
# Created by: Medical Solutions
# Versi Streamlit 1.1 (2024-05-21) - Fixed metric_card issue

import os
import locale
from contextlib import suppress  # <-- INI IMPORT YANG DIBUTUHKAN
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import streamlit as st

## Setup locale untuk format angka dengan fallback yang lebih baik
for loc in ['id_ID.UTF-8', 'en_US.UTF-8', 'en_US.utf8', 'C.UTF-8', 'C']:
    with suppress(locale.Error):  # <-- SEKARANG INI AKAN BERFUNGSI
        locale.setlocale(locale.LC_ALL, loc)
        break
else:
    st.warning("Locale setting failed, using fallback number formatting")

def format_currency(amount):
    """Format angka ke mata uang IDR dengan pemisah ribuan"""
    try:
        return locale.currency(amount, symbol=True, grouping=True, international=False)
    except:
        # Fallback manual jika locale tidak berfungsi
        return f"Rp {amount:,.0f}".replace(",", ".")

def calculate_roi(investment, annual_gain, years):
    """Hitung ROI dalam persen untuk X tahun"""
    if investment == 0:
        return float('inf')
    total_gain = annual_gain * years
    return ((total_gain - investment) / investment) * 100

def generate_charts(data):
    """Buat grafik untuk Streamlit"""
    color_palette = ['#2E86C1', '#27AE60', '#F1C40F', '#E74C3C']
    
    # ========== Grafik Arus Kas ========== #
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    
    months = 60  # 5 tahun
    cumulative = [data['monthly_savings'] * m - data['total_investment'] for m in range(1, months+1)]
    
    ax1.plot(range(1, months+1), cumulative, 
            color=color_palette[0], 
            linewidth=2.5,
            marker='o',
            markersize=6,
            markevery=12)
    
    ax1.set_title('PROYEKSI ARUS KAS KUMULATIF 5 TAHUN\n', 
                fontsize=14, pad=15, fontweight='bold', color='#2C3E50')
    ax1.set_xlabel('\nBulan Ke-', fontsize=10, color='#34495E')
    ax1.set_ylabel('Arus Kas Kumulatif (IDR)\n', fontsize=10, color='#34495E')
    ax1.grid(True, alpha=0.3)
    
    year_ticks = [i*12 for i in range(1, 6)]
    ax1.set_xticks(year_ticks)
    ax1.set_xticklabels([f'TAHUN {i}' for i in range(1, 6)], 
                       fontsize=8, color='#7F8C8D')
    
    bep_month = next((i+1 for i, v in enumerate(cumulative) if v >= 0), None)
    if bep_month:
        ax1.axvline(bep_month, color='#E74C3C', linestyle='--', alpha=0.7)
        ax1.annotate(f'Break Even Point\nBulan {bep_month}',
                    xy=(bep_month, 0),
                    xytext=(bep_month+8, data['total_investment']*0.3),
                    arrowprops=dict(facecolor='#E74C3C', shrink=0.05),
                    fontsize=8,
                    color='#E74C3C',
                    weight='bold')
    
    ax1.axhline(-data['total_investment'], color='#95A5A6', linestyle=':', alpha=0.7)
    ax1.annotate(f'Investasi Awal: {format_currency(data["total_investment"])}',
                xy=(2, -data['total_investment']),
                xytext=(10, -data['total_investment']*0.8),
                fontsize=8,
                color='#2C3E50',
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#BDC3C7", lw=1))
    
    st.pyplot(fig1)
    plt.close()

    # ========== Grafik Penghematan ========== #
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    
    categories = ['Biaya Staff Admin', 'Pendapatan dari No-Show', 'Total Penghematan']
    
    before_staff_cost = data['admin_staff'] * data['avg_salary'] * 12
    before_noshow_loss = data['monthly_appointments'] * data['noshow_rate'] * data['revenue_per_appointment'] * 12
    before_total = 0
    
    after_staff_cost = before_staff_cost * (1 - data['staff_reduction'])
    after_noshow_loss = before_noshow_loss * (1 - data['noshow_reduction'])
    after_total = data['annual_savings'] + data['maintenance_cost'] * 12
    
    savings_staff = before_staff_cost - after_staff_cost
    savings_noshow = before_noshow_loss - after_noshow_loss
    savings_total = after_total
    
    x = np.arange(len(categories))
    width = 0.25
    
    ax2.bar(x - width, [before_staff_cost, before_noshow_loss, before_total], 
           width, label='Sebelum Implementasi', color=color_palette[2])
    ax2.bar(x, [after_staff_cost, after_noshow_loss, after_total], 
           width, label='Setelah Implementasi', color=color_palette[1])
    ax2.bar(x + width, [savings_staff, savings_noshow, savings_total], 
           width, label='Penghematan', color=color_palette[0])
    
    ax2.set_title('PERBANDINGAN BIAYA & PENGHEMATAN TAHUNAN\n', 
                fontsize=14, pad=15, fontweight='bold', color='#2C3E50')
    ax2.set_ylabel('IDR (Rupiah)\n', fontsize=10, color='#34495E')
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories, fontsize=8, color='#34495E')
    
    def add_labels(bars):
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax2.annotate(f'{format_currency(height)}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha='center', va='bottom',
                            fontsize=7, rotation=0)
    
    for container in ax2.containers:
        add_labels(container)
    
    ax2.legend(loc='upper right', fontsize=8)
    
    st.pyplot(fig2)
    plt.close()

def main():
    # Konfigurasi halaman Streamlit
    st.set_page_config(
        page_title="Kalkulator ROI AI Voice untuk Rumah Sakit",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # CSS kustom
    st.markdown("""
    <style>
    .st-emotion-cache-1v0mbdj img {
        border-radius: 10px;
    }
    .st-emotion-cache-16idsys p {
        font-size: 16px;
    }
    .st-emotion-cache-1v0mbdj {
        margin: 0 auto;
    }
    .stMarkdown h1 {
        color: #2E86C1;
    }
    .stMarkdown h2 {
        color: #27AE60;
    }
    .metric-card {
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        padding: 15px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🏥 Kalkulator ROI 5 Tahun untuk Implementasi AI Voice")
    st.markdown("""
    **Alat ini membantu menghitung Return on Investment (ROI) untuk implementasi solusi AI Voice di rumah sakit.**
    """)
    
    with st.sidebar:
        st.header("⚙️ Parameter Input")
        st.image("https://img.icons8.com/color/96/hospital.png", width=80)
        
        hospital_name = st.text_input("Nama Rumah Sakit", "Rumah Sakit ABC")
        hospital_location = st.text_input("Lokasi", "Jakarta")
        
        st.subheader("Parameter Operasional")
        total_staff = st.number_input("Jumlah Seluruh Staff Rumah Sakit", min_value=1, value=200)
        admin_staff = st.number_input("Jumlah Staff Administrasi", min_value=1, value=20)
        monthly_appointments = st.number_input("Rata-rata Janji Temu/Bulan", min_value=1, value=5000)
        noshow_rate = st.slider("Tingkat No-Show (%)", 0.0, 100.0, 15.0) / 100
        
        st.subheader("Parameter Biaya")
        avg_salary = st.number_input("Gaji Rata-rata Staff Admin (IDR)", min_value=0, value=8000000)
        revenue_per_appointment = st.number_input("Pendapatan/Janji Temu (IDR)", min_value=0, value=250000)
        
        st.subheader("Efisiensi yang Diharapkan")
        staff_reduction = st.slider("Pengurangan Staff (%)", 0.0, 100.0, 30.0) / 100
        noshow_reduction = st.slider("Pengurangan No-Show (%)", 0.0, 100.0, 40.0) / 100
        
        st.subheader("Kurs USD-IDR")
        exchange_rate = st.number_input("Kurs USD ke IDR", min_value=1, value=15000)
        
        st.subheader("Biaya Implementasi")
        setup_cost_usd = st.number_input("Biaya Setup Awal (USD)", min_value=0, value=20000)
        integration_cost_usd = st.number_input("Biaya Integrasi (USD)", min_value=0, value=15000)
        training_cost_usd = st.number_input("Biaya Pelatihan (USD)", min_value=0, value=10000)
        maintenance_cost = st.number_input("Biaya Pemeliharaan/Bulan (IDR)", min_value=0, value=5000000)
    
    # Kalkulasi
    setup_cost = setup_cost_usd * exchange_rate
    integration_cost = integration_cost_usd * exchange_rate
    training_cost = training_cost_usd * exchange_rate
    total_investment = setup_cost + integration_cost + training_cost
    
    staff_savings = (admin_staff * staff_reduction) * avg_salary
    noshow_savings = (monthly_appointments * noshow_rate * noshow_reduction) * revenue_per_appointment
    total_monthly_savings = staff_savings + noshow_savings - maintenance_cost
    annual_savings = total_monthly_savings * 12
    
    # Hitung BEP
    payback_period = total_investment / total_monthly_savings if total_monthly_savings > 0 else float('inf')
    bep_month = payback_period if payback_period != float('inf') else None
    
    # Data untuk laporan
    report_data = {
        'hospital_name': hospital_name,
        'hospital_location': hospital_location,
        'total_staff': total_staff,
        'admin_staff': admin_staff,
        'monthly_appointments': monthly_appointments,
        'noshow_rate': noshow_rate,
        'avg_salary': avg_salary,
        'revenue_per_appointment': revenue_per_appointment,
        'staff_reduction': staff_reduction,
        'noshow_reduction': noshow_reduction,
        'exchange_rate': exchange_rate,
        'setup_cost_usd': setup_cost_usd,
        'integration_cost_usd': integration_cost_usd,
        'training_cost_usd': training_cost_usd,
        'maintenance_cost': maintenance_cost,
        'total_investment': total_investment,
        'monthly_savings': total_monthly_savings,
        'annual_savings': annual_savings,
        'payback_period': payback_period,
        'bep_month': bep_month
    }
    
    # Tampilkan hasil utama
    st.header("📊 Hasil Analisis ROI")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Investasi Awal", value=format_currency(total_investment), 
                 delta=None, help="Total biaya implementasi awal")
    with col2:
        st.metric(label="Penghematan Tahunan", value=format_currency(annual_savings),
                 delta=None, help="Total penghematan per tahun")
    with col3:
        roi_1year = calculate_roi(total_investment, annual_savings, 1)
        st.metric(label="ROI 1 Tahun", value=f"{roi_1year:.1f}%",
                 delta=None, help="Return on Investment tahun pertama")
    
    # Tampilkan grafik
    st.subheader("📉 Proyeksi Arus Kas 5 Tahun")
    generate_charts(report_data)
    
    # Tampilkan tabel ROI
    st.subheader("📅 Proyeksi ROI 5 Tahun")
    roi_table = []
    market_share = [5, 15, 30, 45, 60]
    for year in range(1, 6):
        roi = calculate_roi(total_investment, annual_savings, year)
        cumulative_gain = annual_savings * year
        roi_table.append({
            "Tahun": year,
            "ROI (%)": f"{roi:.1f}%",
            "Keuntungan Kumulatif": format_currency(cumulative_gain),
            "Target Pasar": f"+{market_share[year-1]}%"
        })
    
    st.table(roi_table)
    
    # Detail perhitungan
    with st.expander("🔍 Detail Perhitungan"):
        st.subheader("Komponen Penghematan")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Penghematan Staff Administrasi**")
            st.markdown(f"- Staff yang dikurangi: {admin_staff * staff_reduction:.1f} orang")
            st.markdown(f"- Penghematan bulanan: {format_currency(staff_savings)}")
            st.markdown(f"- Penghematan tahunan: {format_currency(staff_savings * 12)}")
        
        with col2:
            st.markdown("**Pengurangan Kerugian No-Show**")
            st.markdown(f"- Janji temu yang diselamatkan: {monthly_appointments * noshow_rate * noshow_reduction:.1f}/bulan")
            st.markdown(f"- Pendapatan tambahan bulanan: {format_currency(noshow_savings)}")
            st.markdown(f"- Pendapatan tambahan tahunan: {format_currency(noshow_savings * 12)}")
        
        st.subheader("Breakdown Biaya Implementasi")
        cost_table = {
            "Komponen Biaya": ["Setup Awal", "Integrasi", "Pelatihan", "Total"],
            "USD": [setup_cost_usd, integration_cost_usd, training_cost_usd, setup_cost_usd + integration_cost_usd + training_cost_usd],
            "IDR": [setup_cost, integration_cost, training_cost, total_investment]
        }
        st.table(cost_table)
    
    # Rekomendasi
    st.subheader("🚀 Rekomendasi Implementasi")
    tab1, tab2, tab3 = st.tabs(["Roadmap", "Fase Implementasi", "Kunci Sukses"])
    
    with tab1:
        st.markdown("""
        ```mermaid
        graph TD
            A[Fase 1: Persiapan] --> B[Pelatihan Tim Inti]
            A --> C[Integrasi Sistem]
            A --> D[Uji Coba Terbatas]
            B --> E[Fase 2: Rollout Nasional]
            C --> E
            D --> E
            E --> F[Fase 3: Optimisasi]
        ```
        """)
    
    with tab2:
        st.markdown("""
        1. **Fase Inisiasi (Bulan 1-3)**
           - Setup infrastruktur dasar
           - Pelatihan super user
        
        2. **Fase Implementasi (Bulan 4-9)**
           - Rollout ke unit prioritas
           - Integrasi dengan EMR
        
        3. **Fase Optimisasi (Bulan 10-12)**
           - Penyempurnaan model AI
           - Expansi ke unit tambahan
        """)
    
    with tab3:
        st.markdown("""
        - Komitmen manajemen puncak
        - Pelatihan menyeluruh untuk staf
        - Integrasi dengan sistem existing
        - Monitoring dan evaluasi berkala
        - Budaya adaptif terhadap perubahan
        """)
    
    # Footer
    st.markdown("---")
    st.markdown(f"*Dibuat oleh Medical AI Solutions pada {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

if __name__ == "__main__":
    main()
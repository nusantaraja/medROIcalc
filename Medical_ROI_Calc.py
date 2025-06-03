#!/usr/bin/env python3
# Kalkulator ROI 5 Tahun untuk Implementasi AI Voice di Rumah Sakit
# Created by: Medical Solutions
# Versi Streamlit 2.4 (2024) - Fixed Calculation, Google Sync & Timestamp Format

import streamlit as st
from datetime import datetime
import locale
import matplotlib.pyplot as plt
import numpy as np
from contextlib import suppress
import io
from fpdf import FPDF # Using FPDF for simple PDF generation
import traceback # For detailed error logging
import pytz # For timezone support (WIB)

# Import Google utilities
import google_utils

# ====================== KONSTANTA ======================
GOOGLE_SHEET_ID = "1sH_ITYk7lcBDRRX9L5j_FqdQ5M3tsdvqyvDhXNgrQOE"
GOOGLE_SHEET_NAME = "AIMedicalMarketingReport"
GOOGLE_DRIVE_FOLDER_ID = "1WbJpJYx-ilqdJ-K3KdDshJKUP4Bbravh"
WIB = pytz.timezone("Asia/Jakarta") # Define WIB timezone

# ====================== FUNGSI UTAMA ======================

def get_wib_time():
    """Returns the current time formatted for WIB."""
    now_utc = datetime.now(pytz.utc)
    now_wib = now_utc.astimezone(WIB)
    return now_wib.strftime("%Y-%m-%d %H:%M:%S WIB")

def setup_locale():
    """Mengatur locale untuk format angka"""
    for loc in ["id_ID.UTF-8", "en_US.UTF-8", "C.UTF-8", ""]:
        with suppress(locale.Error):
            locale.setlocale(locale.LC_ALL, loc)
            break

def format_currency(amount):
    """Format angka ke mata uang IDR dengan pemisah ribuan"""
    try:
        amount = float(amount)
        return locale.currency(amount, symbol="Rp ", grouping=True, international=False)
    except (ValueError, TypeError):
        return "Rp 0"
    except locale.Error:
        try:
            return f"Rp {amount:,.0f}".replace(",", ".")
        except:
             return "Rp 0"

def calculate_roi(investment, annual_gain, years):
    """Hitung ROI dalam persen untuk X tahun"""
    if investment == 0:
        return float("inf")
    total_gain = annual_gain * years
    try:
        return ((total_gain - investment) / investment) * 100
    except ZeroDivisionError:
        return float("inf")

def generate_charts(data):
    """Generate grafik untuk visualisasi data"""
    figs = []
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    months = 60
    cumulative = [data["total_monthly_savings"] * m - data["total_investment"] for m in range(1, months + 1)]
    ax1.plot(range(1, months + 1), cumulative, color="#2E86C1", linewidth=2)
    ax1.set_title("PROYEKSI ARUS KAS KUMULATIF 5 TAHUN")
    ax1.set_xlabel("Bulan")
    ax1.set_ylabel("Arus Kas Kumulatif (IDR)")
    ax1.grid(True, linestyle="--", alpha=0.6)
    figs.append(fig1)

    fig2, ax2 = plt.subplots(figsize=(10, 5))
    categories = ["Staff Admin", "No-Show", "Total Penghematan Tahunan"]
    savings = [
        data["staff_savings_monthly"] * 12,
        data["noshow_savings_monthly"] * 12,
        data["annual_savings"]
    ]
    bars = ax2.bar(categories, savings, color=["#27AE60", "#F1C40F", "#E74C3C"])
    ax2.set_title("SUMBER PENGHEMATAN TAHUNAN")
    ax2.set_ylabel("Jumlah Penghematan (IDR)")
    ax2.grid(True, axis="y", linestyle="--", alpha=0.6)
    for bar in bars:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval, format_currency(yval), va=\'bottom\', ha=\'center\')
    figs.append(fig2)

    return figs

def generate_pdf_report(report_data, consultant_info, figs):
    """Generate PDF report using FPDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    try:
        pdf.add_font("DejaVu", fname="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        pdf.set_font("DejaVu", size=10)
    except RuntimeError:
        st.warning("Font DejaVu Sans tidak ditemukan. Menggunakan font standar Arial.")
        pdf.set_font("Arial", size=10)

    pdf.set_font_size(16)
    pdf.cell(0, 10, f"Laporan Analisis ROI AI Voice - {report_data['hospital_name']}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font_size(10)
    # Use WIB time for PDF generation date as well
    pdf.cell(0, 5, f"Tanggal Dibuat: {get_wib_time()}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(10)

    pdf.set_font_size(12)
    pdf.cell(0, 8, "Informasi Konsultan", new_x="LMARGIN", new_y="NEXT", border='B')
    pdf.set_font_size(10)
    pdf.cell(0, 6, f"Nama: {consultant_info['name']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Email: {consultant_info['email']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"No. HP/WA: {consultant_info['phone']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.set_font_size(12)
    pdf.cell(0, 8, "Informasi Rumah Sakit", new_x="LMARGIN", new_y="NEXT", border='B')
    pdf.set_font_size(10)
    pdf.cell(0, 6, f"Nama: {report_data['hospital_name']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Lokasi: {report_data['hospital_location']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.set_font_size(12)
    pdf.cell(0, 8, "Hasil Utama Analisis ROI", new_x="LMARGIN", new_y="NEXT", border='B')
    pdf.set_font_size(10)
    pdf.cell(95, 7, "Investasi Awal:", border=1)
    pdf.cell(95, 7, format_currency(report_data["total_investment"]), new_x="LMARGIN", new_y="NEXT", border=1, align='R')
    pdf.cell(95, 7, "Penghematan Tahunan:", border=1)
    pdf.cell(95, 7, format_currency(report_data["annual_savings"]), new_x="LMARGIN", new_y="NEXT", border=1, align='R')
    pdf.cell(95, 7, "ROI 1 Tahun:", border=1)
    pdf.cell(95, 7, f"{calculate_roi(report_data['total_investment'], report_data['annual_savings'], 1):.1f}%", new_x="LMARGIN", new_y="NEXT", border=1, align='R')
    pdf.cell(95, 7, "ROI 5 Tahun:", border=1)
    pdf.cell(95, 7, f"{calculate_roi(report_data['total_investment'], report_data['annual_savings'], 5):.1f}%", new_x="LMARGIN", new_y="NEXT", border=1, align='R')
    pdf.cell(95, 7, "Periode Pengembalian (Bulan):", border=1)
    pdf.cell(95, 7, f"{report_data['payback_period']:.1f}" if report_data['payback_period'] != float('inf') else "N/A", new_x="LMARGIN", new_y="NEXT", border=1, align='R')
    pdf.ln(5)

    pdf.set_font_size(12)
    pdf.cell(0, 8, "Detail Perhitungan", new_x="LMARGIN", new_y="NEXT", border='B')
    pdf.set_font_size(10)
    pdf.cell(0, 6, "Komponen Penghematan Bulanan:", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"  + Pengurangan biaya staff: {format_currency(report_data['staff_savings_monthly'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"  + Pengurangan kerugian no-show: {format_currency(report_data['noshow_savings_monthly'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"  - Biaya pemeliharaan bulanan: {format_currency(report_data['maintenance_cost_idr'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"  = Total Penghematan Bulanan Bersih: {format_currency(report_data['total_monthly_savings'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.cell(0, 6, "Breakdown Investasi Awal:", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"  - Biaya setup: {format_currency(report_data['setup_cost'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"  - Biaya integrasi: {format_currency(report_data['integration_cost'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"  - Biaya pelatihan: {format_currency(report_data['training_cost'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"  = Total Investasi Awal: {format_currency(report_data['total_investment'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    pdf.set_font_size(12)
    pdf.cell(0, 8, "Visualisasi Data", new_x="LMARGIN", new_y="NEXT", border='B')
    pdf.set_font_size(10)
    pdf.ln(5)
    chart_paths = []
    for i, fig in enumerate(figs):
        chart_path = f"/tmp/chart_{i}.png"
        fig.savefig(chart_path, bbox_inches='tight')
        chart_paths.append(chart_path)
        pdf.image(chart_path, x=None, y=None, w=180)
        pdf.ln(5)
        plt.close(fig)

    return pdf.output()

# ====================== TAMPILAN STREAMLIT ======================

def main():
    st.set_page_config(
        page_title="Kalkulator ROI AI Voice",
        page_icon="🏥",
        layout="wide"
    )

    st.markdown("""
    <style>
    .stButton>button {
        background-color: #2E86C1;
        color: white;
        font-weight: bold;
    }
    .stMetric {
        background-color: #f0f2f6;
        border-left: 5px solid #2E86C1;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .stTextInput label, .stNumberInput label, .stSlider label {
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🏥 Kalkulator ROI 5 Tahun untuk AI Voice")
    st.markdown("**Alat interaktif untuk menghitung potensi Return on Investment (ROI) dari implementasi solusi AI Voice di fasilitas kesehatan Anda.**")
    st.markdown("---")

    with st.sidebar:
        st.header("👤 Informasi Konsultan")
        consultant_name = st.text_input("Nama Konsultan", key="consultant_name")
        consultant_email = st.text_input("Email Konsultan", key="consultant_email")
        consultant_phone = st.text_input("No. HP/WA Konsultan", key="consultant_phone")
        st.markdown("_Semua field informasi konsultan wajib diisi._")
        st.markdown("---")

        st.header("⚙️ Parameter Input ROI")
        st.subheader("Informasi Rumah Sakit")
        hospital_name = st.text_input("Nama Rumah Sakit", "Rumah Sakit Sehat Sentosa", key="hospital_name")
        hospital_location = st.text_input("Lokasi (Kota/Provinsi)", "Jakarta", key="hospital_location")

        st.subheader("Parameter Operasional")
        col1, col2 = st.columns(2)
        with col1:
            total_staff = st.number_input("Total Staff RS", min_value=1, value=200, key="total_staff")
        with col2:
            admin_staff = st.number_input("Jumlah Staff Admin Terkait", min_value=1, value=20, key="admin_staff")
        monthly_appointments = st.number_input("Rata-rata Janji Temu/Bulan", min_value=1, value=5000, key="monthly_appointments")
        noshow_rate = st.slider("Tingkat No-Show Saat Ini (%)", 0.0, 100.0, 15.0, key="noshow_rate") / 100

        st.subheader("Parameter Biaya")
        avg_salary = st.number_input("Rata-rata Gaji Staff Admin (IDR/Bulan)", min_value=0, value=8000000, step=100000, key="avg_salary")
        revenue_per_appointment = st.number_input("Rata-rata Pendapatan/Janji Temu (IDR)", min_value=0, value=250000, step=10000, key="revenue_per_appointment")

        st.subheader("Estimasi Efisiensi dengan AI Voice")
        staff_reduction = st.slider("Pengurangan Beban Kerja Staff Admin (%)", 0.0, 100.0, 30.0, key="staff_reduction") / 100
        noshow_reduction = st.slider("Pengurangan Tingkat No-Show (%)", 0.0, 100.0, 40.0, key="noshow_reduction") / 100

        st.subheader("Estimasi Biaya Implementasi")
        exchange_rate = st.number_input("Asumsi Kurs USD-IDR", min_value=1, value=16000, key="exchange_rate")
        setup_cost_usd = st.number_input("Biaya Setup Awal (USD)", min_value=0, value=20000, step=1000, key="setup_cost_usd")
        integration_cost_usd = st.number_input("Biaya Integrasi Sistem (USD)", min_value=0, value=15000, step=1000, key="integration_cost_usd")
        training_cost_usd = st.number_input("Biaya Pelatihan Tim (USD)", min_value=0, value=10000, step=1000, key="training_cost_usd")
        maintenance_cost = st.number_input("Biaya Pemeliharaan AI Voice (IDR/Bulan)", min_value=0, value=5000000, step=500000, key="maintenance_cost")

        st.markdown("---")
        hitung_roi = st.button("🚀 HITUNG ROI & SIMPAN LAPORAN", type="primary", use_container_width=True)

    if hitung_roi:
        if not consultant_name or not consultant_email or not consultant_phone:
            st.sidebar.error("⚠️ Harap isi semua informasi konsultan sebelum menghitung.")
            st.stop()

        with st.spinner("⏳ Menghitung ROI dan menyiapkan laporan..."):
            setup_cost = setup_cost_usd * exchange_rate
            integration_cost = integration_cost_usd * exchange_rate
            training_cost = training_cost_usd * exchange_rate
            total_investment = setup_cost + integration_cost + training_cost
            staff_savings = (admin_staff * avg_salary) * staff_reduction
            noshow_saved_appointments = monthly_appointments * noshow_rate * noshow_reduction
            noshow_savings = noshow_saved_appointments * revenue_per_appointment
            total_monthly_savings = staff_savings + noshow_savings - maintenance_cost
            annual_savings = total_monthly_savings * 12
            payback_period = total_investment / total_monthly_savings if total_monthly_savings > 0 else float("inf")

            # Use WIB time for the report data timestamp
            current_wib_time_str = get_wib_time()

            report_data = {
                "timestamp": current_wib_time_str,
                "consultant_name": consultant_name,
                "consultant_email": consultant_email,
                "consultant_phone": consultant_phone,
                "hospital_name": hospital_name,
                "hospital_location": hospital_location,
                "total_staff": total_staff,
                "admin_staff": admin_staff,
                "monthly_appointments": monthly_appointments,
                "noshow_rate_before": noshow_rate * 100,
                "avg_salary": avg_salary,
                "revenue_per_appointment": revenue_per_appointment,
                "staff_reduction_pct": staff_reduction * 100,
                "noshow_reduction_pct": noshow_reduction * 100,
                "exchange_rate": exchange_rate,
                "setup_cost_usd": setup_cost_usd,
                "integration_cost_usd": integration_cost_usd,
                "training_cost_usd": training_cost_usd,
                "maintenance_cost_idr": maintenance_cost,
                "setup_cost": setup_cost,
                "integration_cost": integration_cost,
                "training_cost": training_cost,
                "total_investment": total_investment,
                "staff_savings_monthly": staff_savings,
                "noshow_savings_monthly": noshow_savings,
                "total_monthly_savings": total_monthly_savings,
                "annual_savings": annual_savings,
                "payback_period": payback_period,
                "roi_1_year": calculate_roi(total_investment, annual_savings, 1),
                "roi_5_year": calculate_roi(total_investment, annual_savings, 5),
                "pdf_link": ""
            }

            consultant_info_dict = {
                "name": consultant_name,
                "email": consultant_email,
                "phone": consultant_phone
            }

            st.header("📊 Hasil Analisis ROI")
            st.success("Perhitungan ROI berhasil dilakukan!")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Investasi Awal", format_currency(total_investment))
            with col2:
                st.metric("Penghematan Tahunan", format_currency(annual_savings))
            with col3:
                st.metric("ROI 5 Tahun", f"{report_data['roi_5_year']:.1f}%" if report_data['roi_5_year'] != float('inf') else "N/A")
            with col4:
                 st.metric("Payback Period (Bulan)", f"{payback_period:.1f}" if payback_period != float('inf') else "N/A")

            st.subheader("📈 Visualisasi Data")
            figs = generate_charts(report_data)
            for fig in figs:
                st.pyplot(fig)

            with st.expander("🔍 Lihat Detail Perhitungan"):
                st.subheader("Komponen Penghematan Bulanan")
                st.write(f"- Penghematan dari efisiensi staff admin: {format_currency(staff_savings)}")
                st.write(f"- Penghematan dari pengurangan no-show: {format_currency(noshow_savings)}")
                st.write(f"- Biaya pemeliharaan bulanan: -{format_currency(maintenance_cost)}")
                st.write(f"**Total Penghematan Bulanan Bersih: {format_currency(total_monthly_savings)}**")
                st.markdown("---")
                st.subheader("Breakdown Investasi Awal")
                st.write(f"- Biaya setup ({format_currency(setup_cost_usd)} USD): {format_currency(setup_cost)}")
                st.write(f"- Biaya integrasi ({format_currency(integration_cost_usd)} USD): {format_currency(integration_cost)}")
                st.write(f"- Biaya pelatihan ({format_currency(training_cost_usd)} USD): {format_currency(training_cost)}")
                st.write(f"**Total Investasi: {format_currency(total_investment)}**")

            st.subheader("📄 Laporan PDF & Sinkronisasi Data")
            try:
                with st.spinner("Membuat laporan PDF..."):
                    pdf_content = generate_pdf_report(report_data, consultant_info_dict, figs)
                    pdf_filename = f"ROI_Report_{hospital_name.replace(' ', '_')}_{datetime.now(WIB).strftime('%Y%m%d_%H%M%S')}.pdf"

                creds = google_utils.get_google_credentials()
                drive_service = None
                gc = None
                pdf_link = None
                sheet_success = False

                if creds:
                    drive_service = google_utils.get_drive_service(creds)
                    gc = google_utils.get_gspread_client(creds)
                # else: # Error handled in get_google_credentials
                    # st.error("Gagal memuat kredensial Google. Sinkronisasi tidak dapat dilanjutkan.")

                if drive_service:
                    with st.spinner("Mengunggah PDF ke Google Drive..."):
                        pdf_link = google_utils.upload_pdf_to_drive(drive_service, pdf_content, pdf_filename, GOOGLE_DRIVE_FOLDER_ID)
                        if pdf_link:
                            st.success(f"Laporan PDF berhasil diunggah. [Lihat PDF]({pdf_link})", icon="📄")
                            report_data["pdf_link"] = pdf_link
                        # else: # Error handled within upload_pdf_to_drive
                # elif creds: # Error handled within get_drive_service
                    # st.error("Gagal menginisialisasi layanan Google Drive.")

                st.download_button(
                    label="Unduh Laporan PDF",
                    data=pdf_content,
                    file_name=pdf_filename,
                    mime="application/pdf"
                )

                if gc:
                    with st.spinner("Menyimpan data ke Google Sheet..."):
                        sheet_row = [
                            report_data["timestamp"],
                            report_data["consultant_name"],
                            report_data["consultant_email"],
                            report_data["consultant_phone"],
                            report_data["hospital_name"],
                            report_data["hospital_location"],
                            report_data["total_staff"],
                            report_data["admin_staff"],
                            report_data["monthly_appointments"],
                            report_data["noshow_rate_before"],
                            report_data["avg_salary"],
                            report_data["revenue_per_appointment"],
                            report_data["staff_reduction_pct"],
                            report_data["noshow_reduction_pct"],
                            report_data["exchange_rate"],
                            report_data["setup_cost_usd"],
                            report_data["integration_cost_usd"],
                            report_data["training_cost_usd"],
                            report_data["maintenance_cost_idr"],
                            report_data["total_investment"],
                            report_data["annual_savings"],
                            report_data["payback_period"],
                            report_data["roi_1_year"],
                            report_data["roi_5_year"],
                            report_data["pdf_link"]
                        ]
                        sheet_row = [str(item) if item is not None else "" for item in sheet_row]
                        sheet_success = google_utils.append_to_sheet(gc, GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME, sheet_row)
                        # else: # Error handled within append_to_sheet
                # elif creds: # Error handled within get_gspread_client
                    # st.error("Gagal menginisialisasi klien Google Sheets.")

                if pdf_link and sheet_success:
                    st.balloons()
                    st.success("Laporan PDF berhasil diunggah ke Drive dan data disimpan ke Sheet!")
                elif pdf_link:
                    st.warning("Laporan PDF berhasil diunggah, tetapi penyimpanan data ke Sheet gagal. Periksa log di atas.")
                elif sheet_success:
                    st.warning("Data berhasil disimpan ke Sheet, tetapi unggah PDF ke Drive gagal. Periksa log di atas.")
                elif creds: # If creds were loaded but both failed
                     st.error("Sinkronisasi ke Google Drive dan Google Sheets gagal. Periksa log di atas dan pastikan kredensial serta ID target sudah benar.")
                # If creds failed to load, error was already shown by get_google_credentials

            except Exception as e:
                st.error(f"Terjadi kesalahan tak terduga saat memproses laporan atau sinkronisasi: {e}")
                st.code(traceback.format_exc())

            st.markdown("---")
            st.caption(f"© {datetime.now().year} Medical AI Solutions | Analisis dibuat pada {get_wib_time()}")

if __name__ == "__main__":
    setup_locale()
    if "google_credentials" not in st.secrets:
        st.error("Konfigurasi Kredensial Google tidak ditemukan di Streamlit Secrets. Fitur penyimpanan ke Google Drive/Sheets tidak akan berfungsi.")
        st.info("Silakan tambahkan kredensial service account Google Anda dalam format TOML ke bagian [google_credentials] di file secrets.toml Anda.")
    main()


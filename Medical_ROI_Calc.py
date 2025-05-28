import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import logging
import os
from datetime import datetime
from io import BytesIO
from weasyprint import HTML, CSS
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Google Drive folder ID (parent folder where hospital subfolders will be created)
GDRIVE_PARENT_FOLDER_ID = "1bCG7m4T73K3RNoMvWTE4fjRdWCkwAiKR"
SERVICE_ACCOUNT_FILE = "/home/ubuntu/upload/service_account_key.json" # Use absolute path

# --- Helper Functions ---
def initialize_session_state():
    """Initialize session state variables if they don't exist."""
    if "results_calculated" not in st.session_state:
        st.session_state["results_calculated"] = False
    if "pdf_generated" not in st.session_state:
        st.session_state["pdf_generated"] = False
    if "pdf_bytes" not in st.session_state:
        st.session_state["pdf_bytes"] = None
    if "pdf_filename" not in st.session_state:
        st.session_state["pdf_filename"] = None
    if "report_data" not in st.session_state:
        st.session_state["report_data"] = {}
    if "upload_status" not in st.session_state:
        st.session_state["upload_status"] = None # Can be "success", "error", or None
    if "upload_message" not in st.session_state:
        st.session_state["upload_message"] = ""
    if "drive_link" not in st.session_state:
        st.session_state["drive_link"] = None
    if "run_calculation" not in st.session_state: # Flag to trigger calculation
        st.session_state["run_calculation"] = False

def load_css():
    """Load custom CSS for the app."""
    st.markdown("""
    <style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stButton button {
        height: 3em;
    }
    </style>
    """, unsafe_allow_html=True)

def format_currency(value):
    """Format number as IDR currency."""
    return f"Rp {value:,.0f}".replace(",", ".")

def calculate_roi(total_investment, analysis_period, cost_reduction_percent, efficiency_increase_percent,
                 avg_annual_op_cost, patient_increase_percent, avg_revenue_per_patient, annual_patient_volume,
                 annual_subscription_usd, exchange_rate):
    """Calculate ROI and related metrics."""
    # Convert annual subscription from USD to IDR
    annual_subscription_idr = annual_subscription_usd * exchange_rate

    # Calculate total cost including initial investment and subscription over analysis period
    total_cost = total_investment + (annual_subscription_idr * analysis_period)

    # Calculate annual savings from operational improvements
    annual_cost_savings = avg_annual_op_cost * (cost_reduction_percent / 100)
    annual_efficiency_savings = avg_annual_op_cost * (efficiency_increase_percent / 100)
    total_annual_savings = annual_cost_savings + annual_efficiency_savings

    # Calculate annual revenue increase
    additional_patients = annual_patient_volume * (patient_increase_percent / 100)
    annual_revenue_increase = additional_patients * avg_revenue_per_patient

    # Calculate total benefits over analysis period
    total_savings = total_annual_savings * analysis_period
    total_revenue_increase = annual_revenue_increase * analysis_period
    total_benefits = total_savings + total_revenue_increase

    # Calculate ROI
    net_benefit = total_benefits - total_cost
    roi_percent = (net_benefit / total_cost) * 100 if total_cost > 0 else 0

    # Calculate payback period (in years)
    annual_benefit = total_annual_savings + annual_revenue_increase
    annual_cost = annual_subscription_idr
    # Ensure denominator is positive before division
    denominator = annual_benefit - annual_cost
    initial_payback = total_investment / denominator if denominator > 0 else float('inf')
    payback_period = min(initial_payback, analysis_period) if initial_payback != float('inf') else float('inf') # Handle infinite payback

    # Prepare cash flow data for visualization
    cash_flow_data = []
    savings_data = []
    cumulative_cash_flow = -total_investment

    for year in range(1, analysis_period + 1):
        year_savings = total_annual_savings
        year_revenue = annual_revenue_increase
        year_subscription = annual_subscription_idr
        year_net_flow = year_savings + year_revenue - year_subscription
        cumulative_cash_flow += year_net_flow

        cash_flow_data.append({
            "year": year,
            "net_flow": year_net_flow,
            "cumulative": cumulative_cash_flow
        })

        savings_data.append({
            "year": year,
            "savings": year_savings,
            "revenue_increase": year_revenue,
            "subscription_cost": year_subscription
        })

    return {
        "roi_percent": roi_percent,
        "payback_period": payback_period,
        "total_cost": total_cost,
        "total_savings": total_savings,
        "total_revenue_increase": total_revenue_increase,
        "total_benefits": total_benefits,
        "net_benefit": net_benefit,
        "annual_subscription_idr": annual_subscription_idr,
        "cash_flow_data": cash_flow_data,
        "savings_data": savings_data
    }

def generate_charts_base64(cash_flow_data, savings_data):
    """Generate charts and return as base64 encoded strings."""
    if not cash_flow_data or not savings_data:
        return {}

    result = {}

    # Cash Flow Chart
    try:
        plt.figure(figsize=(10, 6))
        years = [cf["year"] for cf in cash_flow_data]
        cumulative = [cf["cumulative"] for cf in cash_flow_data]

        plt.plot(years, cumulative, marker='o', linewidth=2, color='#1f77b4')
        plt.axhline(y=0, color='r', linestyle='-', alpha=0.3)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.title('Arus Kas Kumulatif', fontsize=14)
        plt.xlabel('Tahun', fontsize=12)
        plt.ylabel('IDR', fontsize=12)
        plt.xticks(years)

        # Add value labels
        for i, value in enumerate(cumulative):
            plt.annotate(f"{value/1e6:.1f}M", (years[i], value),
                        textcoords="offset points", xytext=(0,10), ha='center')

        # Save to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        result["cashflow"] = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()
    except Exception as e:
        logger.error(f"Error generating cash flow chart: {e}", exc_info=True)

    # Savings vs Revenue Chart
    try:
        plt.figure(figsize=(10, 6))
        years = [s["year"] for s in savings_data]
        savings = [s["savings"] for s in savings_data]
        revenue = [s["revenue_increase"] for s in savings_data]
        subscription = [s["subscription_cost"] for s in savings_data]

        width = 0.25
        x = np.arange(len(years))

        plt.bar(x - width, savings, width, label='Penghematan Operasional', color='#2ca02c')
        plt.bar(x, revenue, width, label='Peningkatan Pendapatan', color='#1f77b4')
        plt.bar(x + width, subscription, width, label='Biaya Langganan', color='#d62728')

        plt.grid(True, linestyle='--', alpha=0.7, axis='y')
        plt.title('Penghematan vs Peningkatan Pendapatan vs Biaya Langganan', fontsize=14)
        plt.xlabel('Tahun', fontsize=12)
        plt.ylabel('IDR', fontsize=12)
        plt.xticks(x, years)
        plt.legend()

        # Save to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        result["savings"] = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()
    except Exception as e:
        logger.error(f"Error generating savings chart: {e}", exc_info=True)

    return result

def generate_pdf_report(data, charts_base64):
    """Generate PDF report from data and charts."""
    try:
        # Extract data for cleaner usage
        hosp_name = data.get("hospital_name", "N/A")
        hosp_loc = data.get("hospital_location", "N/A")
        consult_name = data.get("consultant_name", "N/A")
        consult_email = data.get("consultant_email", "N/A")
        consult_phone = data.get("consultant_phone", "N/A")
        calc_time = data.get("calculation_timestamp", datetime.now()).strftime("%d %B %Y, %H:%M:%S")

        # Financial data
        exchange_rate = data.get("exchange_rate", 0)
        annual_subscription_usd = data.get("annual_subscription_usd", 0)
        annual_subscription_idr = data.get("annual_subscription_idr", 0)
        total_investment = data.get("total_investment", 0)
        analysis_period = data.get("analysis_period", 0)

        # Results
        roi_percent = data.get("roi_percent", 0)
        payback_period = data.get("payback_period", 0)
        total_cost = data.get("total_cost", 0)
        total_savings = data.get("total_savings", 0)
        total_revenue_increase = data.get("total_revenue_increase", 0)
        total_benefits = data.get("total_benefits", 0)
        net_benefit = data.get("net_benefit", 0)

        # Handle infinite payback period for display
        payback_display = f"{payback_period:.2f} Tahun" if payback_period != float('inf') else "Tidak Tercapai"

        # Create HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Laporan ROI - {hosp_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #2c3e50; margin-bottom: 5px; }}
                .header p {{ color: #7f8c8d; }}
                .section {{ margin-bottom: 30px; }}
                .section h2 {{ color: #2980b9; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                table, th, td {{ border: 1px solid #ddd; }}
                th, td {{ padding: 12px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .metric-container {{ display: flex; justify-content: space-around; flex-wrap: wrap; margin-bottom: 20px; }}
                .metric {{ width: 30%; margin: 10px 1%; padding: 15px;
                          box-shadow: 0 0 10px rgba(0,0,0,0.1); border-radius: 5px; text-align: center; box-sizing: border-box; }}
                .metric h3 {{ margin: 0 0 10px 0; color: #7f8c8d; font-size: 14px; }}
                .metric p {{ margin: 0; font-size: 18px; font-weight: bold; color: #2c3e50; }}
                .chart {{ margin: 20px 0; text-align: center; }}
                .chart img {{ max-width: 100%; height: auto; }}
                .footer {{ margin-top: 50px; text-align: center; font-size: 12px; color: #7f8c8d; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Laporan Analisis ROI Investasi Medis</h1>
                <p>{calc_time}</p>
            </div>

            <div class="section">
                <h2>Informasi Umum</h2>
                <table>
                    <tr>
                        <th>Rumah Sakit</th>
                        <td>{hosp_name}</td>
                    </tr>
                    <tr>
                        <th>Lokasi</th>
                        <td>{hosp_loc}</td>
                    </tr>
                    <tr>
                        <th>Konsultan</th>
                        <td>{consult_name}</td>
                    </tr>
                    <tr>
                        <th>Email Konsultan</th>
                        <td>{consult_email}</td>
                    </tr>
                    <tr>
                        <th>No. HP/WA Konsultan</th>
                        <td>{consult_phone}</td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <h2>Parameter Input</h2>
                <table>
                    <tr>
                        <th>Total Investasi Awal</th>
                        <td>{format_currency(total_investment)}</td>
                    </tr>
                    <tr>
                        <th>Biaya Langganan per Tahun (USD)</th>
                        <td>${annual_subscription_usd:,.2f}</td>
                    </tr>
                    <tr>
                        <th>Biaya Langganan per Tahun (IDR)</th>
                        <td>{format_currency(annual_subscription_idr)}</td>
                    </tr>
                    <tr>
                        <th>Kurs Tukar USD ke IDR</th>
                        <td>{format_currency(exchange_rate)}</td>
                    </tr>
                    <tr>
                        <th>Periode Analisis</th>
                        <td>{analysis_period} Tahun</td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <h2>Hasil Analisis</h2>
                <div class="metric-container">
                    <div class="metric">
                        <h3>Estimasi ROI</h3>
                        <p>{roi_percent:.2f}%</p>
                    </div>
                    <div class="metric">
                        <h3>Payback Period</h3>
                        <p>{payback_display}</p>
                    </div>
                    <div class="metric">
                        <h3>Total Biaya</h3>
                        <p>{format_currency(total_cost)}</p>
                    </div>
                </div>

                <table>
                    <tr>
                        <th>Total Penghematan Operasional</th>
                        <td>{format_currency(total_savings)}</td>
                    </tr>
                    <tr>
                        <th>Total Peningkatan Pendapatan</th>
                        <td>{format_currency(total_revenue_increase)}</td>
                    </tr>
                    <tr>
                        <th>Total Manfaat</th>
                        <td>{format_currency(total_benefits)}</td>
                    </tr>
                    <tr>
                        <th>Manfaat Bersih</th>
                        <td>{format_currency(net_benefit)}</td>
                    </tr>
                </table>
            </div>
        """

        # Add charts if available
        if charts_base64:
            html_content += """
            <div class="section">
                <h2>Visualisasi Data</h2>
            """

            if charts_base64.get("cashflow"):
                html_content += f"""
                <div class="chart">
                    <h3>Arus Kas Kumulatif</h3>
                    <img src="data:image/png;base64,{charts_base64['cashflow']}" alt="Grafik Arus Kas Kumulatif">
                </div>
                """

            if charts_base64.get("savings"):
                html_content += f"""
                <div class="chart">
                    <h3>Penghematan vs Peningkatan Pendapatan vs Biaya Langganan</h3>
                    <img src="data:image/png;base64,{charts_base64['savings']}" alt="Grafik Penghematan vs Peningkatan Pendapatan">
                </div>
                """

            html_content += "</div>"

        # Close HTML
        html_content += """
            <div class="footer">
                <p>Dokumen ini dibuat secara otomatis oleh Kalkulator ROI Medis.</p>
            </div>
        </body>
        </html>
        """

        # Generate PDF using WeasyPrint
        html = HTML(string=html_content)
        css = CSS(string="""
            @page { margin: 1cm; }
        """)
        pdf_bytes = html.write_pdf(stylesheets=[css])
        return pdf_bytes

    except Exception as e:
        logger.error(f"Error generating PDF report: {e}", exc_info=True)
        return None

def get_credentials():
    """Get Google Drive API credentials from service account file."""
    try:
        # Check if service account file exists
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            logger.error(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")
            st.session_state["upload_status"] = "error"
            st.session_state["upload_message"] = f"File Kredensial Google ({SERVICE_ACCOUNT_FILE}) tidak ditemukan."
            return None

        # Create credentials
        scopes = ['https://www.googleapis.com/auth/drive']
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=scopes)
        return credentials
    except Exception as e:
        logger.error(f"Error getting credentials: {e}", exc_info=True)
        st.session_state["upload_status"] = "error"
        st.session_state["upload_message"] = f"Gagal memuat kredensial: {e}"
        return None

def create_folder(service, folder_name, parent_folder_id):
    """Create or find a folder in Google Drive."""
    try:
        # Check if folder already exists
        # Use double quotes for query parts, single quotes for values inside
        query = f"name='{folder_name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])

        if items:
            logger.info(f"Folder '{folder_name}' already exists with ID: {items[0]['id']}")
            return items[0]['id']

        # Create folder if it doesn't exist
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        folder_id = folder.get('id')
        logger.info(f"Created folder '{folder_name}' with ID: {folder_id}")
        return folder_id
    except HttpError as error:
        logger.error(f"Error checking/creating folder '{folder_name}': {error}", exc_info=True)
        st.session_state["upload_status"] = "error"
        st.session_state["upload_message"] = f"Gagal membuat folder di Google Drive: {error}"
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating folder '{folder_name}': {e}", exc_info=True)
        st.session_state["upload_status"] = "error"
        st.session_state["upload_message"] = f"Kesalahan tak terduga saat membuat folder: {e}"
        return None

def upload_to_drive(service, pdf_bytes, filename, hospital_folder_id):
    """Uploads PDF bytes to the specified Google Drive folder."""
    if not service or not pdf_bytes or not hospital_folder_id:
        logger.warning("Upload prerequisites not met (service, pdf_bytes, or hospital_folder_id missing).")
        st.session_state["upload_status"] = "error"
        st.session_state["upload_message"] = "Prasyarat unggah tidak terpenuhi (layanan, data PDF, atau ID folder)."
        return None
    try:
        file_metadata = {
            "name": filename,
            "parents": [hospital_folder_id]
        }
        media = MediaIoBaseUpload(BytesIO(pdf_bytes), mimetype="application/pdf", resumable=True)
        file = service.files().create(body=file_metadata,
                                    media_body=media,
                                    fields="id, webViewLink").execute()

        file_id = file.get("id")
        file_link = file.get("webViewLink")
        logger.info(f'File "{filename}" uploaded successfully. ID: {file_id}')
        st.session_state["upload_status"] = "success"
        st.session_state["upload_message"] = f'Laporan PDF "{filename}" berhasil diunggah ke Google Drive!'
        st.session_state["drive_link"] = file_link
        return file_id
    except HttpError as error:
        logger.error(f"An error occurred during upload: {error}", exc_info=True)
        st.session_state["upload_status"] = "error"
        st.session_state["upload_message"] = f"Gagal mengunggah file ke Google Drive: {error}"
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during upload: {e}", exc_info=True)
        st.session_state["upload_status"] = "error"
        st.session_state["upload_message"] = f"Terjadi kesalahan tak terduga saat mengunggah file: {e}"
        return None

def trigger_calculation():
    """Sets the flag to run the calculation."""
    st.session_state.run_calculation = True

# --- Main App Logic ---
def main():
    # --- Initial Setup ---
    st.set_page_config(page_title="Kalkulator ROI Medis", layout="wide", page_icon="🏥")
    initialize_session_state()
    load_css()
    # Placeholder for dynamic results display
    results_placeholder = st.empty()

    # --- Sidebar Inputs ---
    with st.sidebar:
        st.image("https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.png", width=200) # Placeholder logo
        st.header("⚙️ Parameter Input")
        st.markdown("Masukkan detail untuk menghitung ROI.")

        # Consultant Info (Mandatory)
        st.subheader("👤 Informasi Konsultan")
        consultant_name = st.text_input("Nama Konsultan*", key="consultant_name", help="Nama lengkap konsultan.")
        consultant_email = st.text_input("Email Konsultan*", key="consultant_email", help="Alamat email aktif.")
        consultant_phone = st.text_input("No. HP/WA Konsultan*", key="consultant_phone", help="Nomor telepon/WhatsApp aktif (contoh: +6281234567890).")

        # Hospital Info
        st.subheader("🏥 Informasi Rumah Sakit")
        hospital_name = st.text_input("Nama Rumah Sakit*", key="hospital_name", help="Nama rumah sakit klien.")
        hospital_location = st.text_input("Lokasi Rumah Sakit*", key="hospital_location", help="Kota/Kabupaten lokasi rumah sakit.")

        # Financial Inputs
        st.subheader("💲 Input Finansial")
        exchange_rate = st.number_input("Kurs Tukar USD ke IDR", min_value=1.0, value=st.session_state.get("exchange_rate", 15000.0), step=100.0, key="exchange_rate", help="Kurs USD ke IDR saat ini.")
        annual_subscription_usd = st.number_input("Biaya Langganan per Tahun (USD)*", min_value=0.0, value=st.session_state.get("annual_subscription_usd", 1000.0), step=50.0, key="annual_subscription_usd", help="Biaya langganan tahunan dalam USD.")
        total_investment = st.number_input("Total Investasi Awal (IDR)*", min_value=0.0, value=st.session_state.get("total_investment", 50000000.0), step=1000000.0, key="total_investment", help="Total biaya implementasi awal dalam IDR.")
        analysis_period = st.slider("Periode Analisis (Tahun)", min_value=1, max_value=10, value=st.session_state.get("analysis_period", 5), key="analysis_period", help="Jangka waktu analisis ROI.")

        # Operational Savings Inputs
        st.subheader("📈 Estimasi Penghematan Operasional (per Tahun)")
        cost_reduction_percent = st.slider("Pengurangan Biaya Operasional (%) ", 0.0, 50.0, st.session_state.get("cost_reduction_percent", 10.0), 0.5, key="cost_reduction_percent", help="Persentase estimasi pengurangan biaya operasional tahunan.")
        efficiency_increase_percent = st.slider("Peningkatan Efisiensi (%) ", 0.0, 50.0, st.session_state.get("efficiency_increase_percent", 15.0), 0.5, key="efficiency_increase_percent", help="Persentase estimasi peningkatan efisiensi operasional tahunan.")
        avg_annual_op_cost = st.number_input("Biaya Operasional Tahunan Rata-rata (IDR)", min_value=0.0, value=st.session_state.get("avg_annual_op_cost", 1000000000.0), step=50000000.0, key="avg_annual_op_cost", help="Biaya operasional tahunan rata-rata sebelum implementasi.")

        # Revenue Increase Inputs
        st.subheader("💰 Estimasi Peningkatan Pendapatan (per Tahun)")
        patient_increase_percent = st.slider("Peningkatan Jumlah Pasien (%) ", 0.0, 50.0, st.session_state.get("patient_increase_percent", 5.0), 0.5, key="patient_increase_percent", help="Persentase estimasi peningkatan jumlah pasien tahunan.")
        avg_revenue_per_patient = st.number_input("Pendapatan Rata-rata per Pasien (IDR)", min_value=0.0, value=st.session_state.get("avg_revenue_per_patient", 5000000.0), step=100000.0, key="avg_revenue_per_patient", help="Pendapatan rata-rata per pasien sebelum implementasi.")
        annual_patient_volume = st.number_input("Volume Pasien Tahunan Awal", min_value=0, value=st.session_state.get("annual_patient_volume", 10000), step=100, key="annual_patient_volume", help="Jumlah pasien tahunan sebelum implementasi.")

        # --- Calculation Trigger --- 
        st.markdown("---")
        # Use on_click callback to set the flag
        st.button("Hitung ROI & Buat Laporan", 
                  type="primary", 
                  use_container_width=True, 
                  on_click=trigger_calculation, 
                  key="calculate_button")

    # --- Main Panel Display --- 
    st.title("🏥 Kalkulator Estimasi ROI Investasi Medis")
    st.markdown("Alat bantu untuk mengestimasi Return on Investment (ROI) dari implementasi solusi medis baru.")
    st.markdown("Gunakan panel di sebelah kiri untuk memasukkan parameter yang relevan.")
    st.info("Field dengan tanda (*) wajib diisi.", icon="ℹ️")

    # --- Calculation Logic (Triggered by flag) --- 
    if st.session_state.get("run_calculation", False):
        # Reset the flag immediately to prevent re-calculation on next rerun unless button is clicked again
        st.session_state.run_calculation = False 
        
        # Reset previous upload status
        st.session_state["upload_status"] = None
        st.session_state["upload_message"] = ""
        st.session_state["drive_link"] = None
        
        # Basic Validation (Retrieve values from session state or widgets)
        # Note: Accessing widget values directly might be needed if session state isn't updated before rerun
        consultant_name_val = st.session_state.get("consultant_name", "")
        consultant_email_val = st.session_state.get("consultant_email", "")
        consultant_phone_val = st.session_state.get("consultant_phone", "")
        hospital_name_val = st.session_state.get("hospital_name", "")
        hospital_location_val = st.session_state.get("hospital_location", "")
        annual_subscription_usd_val = st.session_state.get("annual_subscription_usd", 0.0)
        total_investment_val = st.session_state.get("total_investment", 0.0)
        exchange_rate_val = st.session_state.get("exchange_rate", 15000.0)
        analysis_period_val = st.session_state.get("analysis_period", 5)
        cost_reduction_percent_val = st.session_state.get("cost_reduction_percent", 10.0)
        efficiency_increase_percent_val = st.session_state.get("efficiency_increase_percent", 15.0)
        avg_annual_op_cost_val = st.session_state.get("avg_annual_op_cost", 1000000000.0)
        patient_increase_percent_val = st.session_state.get("patient_increase_percent", 5.0)
        avg_revenue_per_patient_val = st.session_state.get("avg_revenue_per_patient", 5000000.0)
        annual_patient_volume_val = st.session_state.get("annual_patient_volume", 10000)

        required_fields = {
            "Nama Konsultan": consultant_name_val,
            "Email Konsultan": consultant_email_val,
            "No. HP/WA Konsultan": consultant_phone_val,
            "Nama Rumah Sakit": hospital_name_val,
            "Lokasi Rumah Sakit": hospital_location_val,
            "Biaya Langganan per Tahun (USD)": annual_subscription_usd_val,
            "Total Investasi Awal (IDR)": total_investment_val
        }
        missing_fields = [name for name, value in required_fields.items() if not value and value != 0] # Allow 0 for numeric

        # Email Validation (Simple)
        email_valid = "@" in consultant_email_val and "." in consultant_email_val.split("@")[-1] if consultant_email_val else False
        # Phone Validation (Simple - starts with + or 0, mostly digits)
        phone_valid = (consultant_phone_val.startswith("+") or consultant_phone_val.startswith("0")) and consultant_phone_val.replace("+", "").isdigit() if consultant_phone_val else False

        if missing_fields:
            st.error(f"Harap isi field wajib berikut: {', '.join(missing_fields)}")
            st.session_state["results_calculated"] = False # Prevent showing results section
        elif not email_valid:
            st.error("Format email konsultan tidak valid.")
            st.session_state["results_calculated"] = False
        elif not phone_valid:
            st.error("Format No. HP/WA konsultan tidak valid (harus diawali + atau 0 dan berisi angka).")
            st.session_state["results_calculated"] = False
        else:
            with st.spinner("⏳ Menghitung ROI, membuat laporan PDF, dan mengunggah ke Google Drive..."):
                # Perform Calculations
                results = calculate_roi(
                    total_investment=total_investment_val,
                    analysis_period=analysis_period_val,
                    cost_reduction_percent=cost_reduction_percent_val,
                    efficiency_increase_percent=efficiency_increase_percent_val,
                    avg_annual_op_cost=avg_annual_op_cost_val,
                    patient_increase_percent=patient_increase_percent_val,
                    avg_revenue_per_patient=avg_revenue_per_patient_val,
                    annual_patient_volume=annual_patient_volume_val,
                    annual_subscription_usd=annual_subscription_usd_val,
                    exchange_rate=exchange_rate_val
                )

                # Prepare data for report and display
                report_data = {
                    "consultant_name": consultant_name_val,
                    "consultant_email": consultant_email_val,
                    "consultant_phone": consultant_phone_val,
                    "hospital_name": hospital_name_val,
                    "hospital_location": hospital_location_val,
                    "exchange_rate": exchange_rate_val,
                    "annual_subscription_usd": annual_subscription_usd_val,
                    "total_investment": total_investment_val,
                    "analysis_period": analysis_period_val,
                    "cost_reduction_percent": cost_reduction_percent_val,
                    "efficiency_increase_percent": efficiency_increase_percent_val,
                    "avg_annual_op_cost": avg_annual_op_cost_val,
                    "patient_increase_percent": patient_increase_percent_val,
                    "avg_revenue_per_patient": avg_revenue_per_patient_val,
                    "annual_patient_volume": annual_patient_volume_val,
                    "calculation_timestamp": datetime.now(),
                    **results # Merge calculation results
                }
                st.session_state["report_data"] = report_data
                st.session_state["results_calculated"] = True

                # Automatically generate PDF after calculation
                charts_base64 = generate_charts_base64(results.get("cash_flow_data", []), results.get("savings_data", []))
                pdf_bytes = generate_pdf_report(report_data, charts_base64)
                if pdf_bytes:
                    # Generate filename based on user request
                    now_str = datetime.now().strftime("%y%m%d")
                    # Sanitize names for folder/file naming
                    safe_hosp_name = "".join(c if c.isalnum() else "_" for c in hospital_name_val)
                    safe_hosp_loc = "".join(c if c.isalnum() else "_" for c in hospital_location_val)
                    safe_consult_name = "".join(c if c.isalnum() else "_" for c in consultant_name_val)
                    pdf_filename = f"{now_str} {safe_hosp_name} {safe_hosp_loc} {safe_consult_name}.pdf"

                    st.session_state["pdf_bytes"] = pdf_bytes
                    st.session_state["pdf_filename"] = pdf_filename
                    st.session_state["pdf_generated"] = True

                    # --- Automatic Google Drive Upload --- 
                    credentials = get_credentials()
                    if credentials:
                        try:
                            service = build('drive', 'v3', credentials=credentials)
                            # Create/find hospital-specific subfolder
                            hospital_folder_name = f"{safe_hosp_name} - {safe_hosp_loc}"
                            hospital_folder_id = create_folder(service, hospital_folder_name, GDRIVE_PARENT_FOLDER_ID)
                            
                            if hospital_folder_id:
                                # Upload the PDF to the hospital's folder
                                upload_to_drive(service, pdf_bytes, pdf_filename, hospital_folder_id)
                            # else: Error message handled within create_folder
                        except Exception as e:
                            logger.error(f"Error during Google Drive operations: {e}", exc_info=True)
                            st.session_state["upload_status"] = "error"
                            st.session_state["upload_message"] = f"Kesalahan saat berinteraksi dengan Google Drive: {e}"
                    # else: Error message handled within get_credentials
                else:
                    st.session_state["pdf_generated"] = False
                    st.error("Gagal membuat laporan PDF.")

            st.rerun() # Rerun to update the display section

    # --- Display Results --- 
    if st.session_state.get("results_calculated", False):
        data = st.session_state.get("report_data", {})
        with results_placeholder.container(): # Use the placeholder
            st.header("📊 Ringkasan Hasil Analisis ROI")
            # Extract data for cleaner f-string usage
            hosp_name = data.get("hospital_name", "N/A")
            roi_percent = data.get("roi_percent", 0)
            payback_period = data.get("payback_period", 0)
            total_cost = data.get("total_cost", 0)
            total_savings = data.get("total_savings", 0)
            total_revenue_increase = data.get("total_revenue_increase", 0)
            total_benefits = data.get("total_benefits", 0)
            net_benefit = data.get("net_benefit", 0)
            annual_subscription_idr = data.get("annual_subscription_idr", 0)
            payback_display = f"{payback_period:.2f} Tahun" if payback_period != float('inf') else "Tidak Tercapai"

            st.success(f"Analisis ROI untuk **{hosp_name}** berhasil dihitung.")

            col1, col2, col3 = st.columns(3)
            col1.metric("Estimasi ROI", f"{roi_percent:.2f}%")
            col2.metric("Payback Period", payback_display)
            col3.metric("Total Biaya (Selama Periode Analisis)", format_currency(total_cost))

            st.markdown("**Detail Manfaat:**")
            col4, col5 = st.columns(2)
            col4.metric("Total Penghematan Operasional", format_currency(total_savings))
            col5.metric("Total Peningkatan Pendapatan", format_currency(total_revenue_increase))

            col6, col7 = st.columns(2)
            col6.metric("Total Manfaat", format_currency(total_benefits))
            col7.metric("Manfaat Bersih (Net Benefit)", format_currency(net_benefit))
            
            st.metric("Biaya Langganan Tahunan", format_currency(annual_subscription_idr))

            # Display Charts
            charts_base64 = generate_charts_base64(data.get("cash_flow_data", []), data.get("savings_data", []))
            if charts_base64:
                st.subheader("Visualisasi Data")
                if charts_base64.get("cashflow"):
                    st.image(f"data:image/png;base64,{charts_base64['cashflow']}", caption="Grafik Arus Kas Kumulatif")
                if charts_base64.get("savings"):
                    st.image(f"data:image/png;base64,{charts_base64['savings']}", caption="Grafik Penghematan vs Peningkatan Pendapatan vs Biaya Langganan")

            # Display PDF Download Button
            if st.session_state.get("pdf_generated", False):
                st.download_button(
                    label="📥 Unduh Laporan PDF",
                    data=st.session_state.pdf_bytes,
                    file_name=st.session_state.pdf_filename,
                    mime="application/pdf",
                    use_container_width=True
                )
            
            # Display Google Drive Upload Status
            upload_status = st.session_state.get("upload_status")
            upload_message = st.session_state.get("upload_message", "")
            drive_link = st.session_state.get("drive_link")

            if upload_status == "success":
                st.success(upload_message, icon="✅")
                if drive_link:
                    st.markdown(f"[Lihat File di Google Drive]({drive_link})", unsafe_allow_html=True)
            elif upload_status == "error":
                st.error(upload_message, icon="❌")
            elif upload_status is None and st.session_state.get("pdf_generated", False):
                 # If PDF was generated but no upload status yet (e.g., error before upload attempt)
                 st.warning("Proses unggah ke Google Drive belum selesai atau gagal.")


if __name__ == "__main__":
    main()


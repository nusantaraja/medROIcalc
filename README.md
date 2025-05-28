# Medical ROI Calculator

Aplikasi kalkulator untuk mengestimasi Return on Investment (ROI) dari implementasi solusi medis baru di rumah sakit.

## Fitur Utama

- Perhitungan ROI berdasarkan parameter finansial dan operasional
- Pembuatan laporan PDF otomatis setelah perhitungan
- Unggah otomatis laporan PDF ke Google Drive
- Visualisasi data dengan grafik arus kas dan penghematan vs pendapatan
- Perhitungan yang memperhitungkan biaya langganan tahunan

## Perubahan Terbaru

- Ditambahkan field Nama Konsultan, Email, dan Nomor HP/WA yang wajib diisi
- Ditambahkan field "Biaya Langganan per Tahun (USD)" yang digunakan dalam perhitungan
- Implementasi unggah otomatis ke Google Drive tanpa perlu tombol manual
- Penyimpanan file PDF dalam folder per rumah sakit dengan format nama file: `yymmdd namarumahsakit lokasi namakonsultan.pdf`
- Perbaikan berbagai error sintaks dan alur kerja aplikasi

## Cara Penggunaan

1. Pastikan semua dependensi terinstal:
   ```
   pip install -r requirements.txt
   ```

2. Pastikan file kredensial Google Drive (`service_account_key.json`) tersedia di folder `/upload/`

3. Jalankan aplikasi:
   ```
   streamlit run Medical_ROI_Calc.py
   ```

4. Isi semua field yang diperlukan (yang bertanda * adalah wajib)

5. Klik tombol "Hitung ROI & Buat Laporan" untuk memulai perhitungan, pembuatan PDF, dan unggah otomatis ke Google Drive

## Struktur Folder Google Drive

Aplikasi akan secara otomatis:
1. Mencari folder utama dengan ID yang dikonfigurasi
2. Membuat subfolder untuk setiap rumah sakit dengan format: `NamaRumahSakit - Lokasi`
3. Menyimpan file PDF di dalam subfolder tersebut

## Catatan Teknis

- Aplikasi menggunakan WeasyPrint untuk pembuatan PDF
- Integrasi Google Drive menggunakan Google Drive API v3
- Visualisasi data menggunakan Matplotlib
- Semua perhitungan ROI memperhitungkan biaya langganan tahunan

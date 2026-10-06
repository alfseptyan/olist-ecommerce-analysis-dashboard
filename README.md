# Proyek Analisis Data: Brazilian E-Commerce Public Dataset by Olist

Analisis data e-commerce Olist (2017-2018) beserta dashboard interaktif Streamlit.

**Pertanyaan bisnis**
1. Kategori produk apa saja yang menjadi 10 penyumbang revenue terbesar (Jan 2017 - Agu 2018) dan bagaimana pertumbuhan Jan-Agu 2018 dibanding Jan-Agu 2017?
2. Seberapa besar keterlambatan pengiriman menurunkan review score, dan di 5 state mana persentase keterlambatannya tertinggi?

Analisis lanjutan: RFM dengan binning manual.

## Struktur
```
submission
|-- dashboard
|   |-- main_data.csv        # data bersih untuk dashboard
|   |-- dashboard.py         # aplikasi Streamlit
|-- data                     # dataset mentah yang dipakai
|-- Proyek Analisis Data.ipynb
|-- README.md
|-- requirements.txt
|-- url.txt
```

## Menjalankan secara lokal
Gunakan Python 3.10+.

```bash
# (opsional) buat virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
streamlit run dashboard/dashboard.py
```
Dashboard terbuka di http://localhost:8501.

## Menjalankan notebook
Buka `Proyek Analisis Data.ipynb` di VS Code (jalankan dari folder `submission`, karena path data bersifat relatif), pilih kernel Python, lalu *Run All*. Notebook akan menghasilkan ulang `dashboard/main_data.csv`.

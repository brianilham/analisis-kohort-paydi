# Analisis Kohort Persistensi Polis & Deteksi Churn Agen (PAYDI)

Aplikasi analitik aktuaria dan sistem deteksi anomali kecurangan agen (*Hit-and-Run* & *Cherry-Picking*) untuk produk **PAYDI (Pendapatan Terkait Investasi / Unit Link)** berbasis Streamlit, Scikit-Learn, dan Plotly, selaras dengan kepatuhan **Surat Edaran Otoritas Jasa Keuangan (SEOJK PAYDI)** dan pedoman persistensi **Asosiasi Asuransi Jiwa Indonesia (AAJI)**.

---

## 🚀 Fitur Utama

1. **Synthetic Data Generator Engine (`generate_data.py`)**:
   - Simulasi 24 kohort bulanan (*Issue Date* rentang 2 tahun) dengan skala 10.000–15.000 polis dan 150–200 agen.
   - Siklus status bulanan: `Active`, `Grace Period` (M11–M12), `Lapsed`, dan `Surrendered` dengan sifat *absorbing terminal state*.
   - Injeksi ground-truth anomali terkalibrasi:
     - **Normal (92%)**: Persistensi M13 berada pada benchmark OJK/AAJI (80%–85%).
     - **Hit-and-Run (3%)**: Penurunan drastis serentak (>25% drop) di M13 setelah pencairan komisi tahun pertama (*FYC*).
     - **Cherry-Picking (5%)**: Menjaga persistensi volume tetap aman (~80%), namun membiarkan polis besar (*high-ticket*) mati sehingga nilai premi (*APE*) anjlok >50%.

2. **2D Cohort Analytics Engine (`detector.py`)**:
   - **Dual-Cohort Matrix (M1–M24)**: Matriks persistensi Volume Polis berdampingan dengan Matriks Nilai Premi (APE).
   - **Discrepancy / Premium Leakage Matrix**: Selisih persentase persistensi Volume vs APE untuk mendeteksi manipulasi premi tersembunyi.
   - **Early Warning Grace Period Extractor**: Pelacakan polis dan total nominal APE yang berada dalam masa tenggang di M11–M12 sebelum jatuh tempo M13.

3. **Two-Tier Anomaly Detection Architecture**:
   - **Tier 1 (Hard Rule-Based Screening)**: Filter kepatuhan deterministik ($\Delta \text{Persistency}_{Vol} > 25\%$ atau persistensi M13 $< 75\%$).
   - **Tier 2 (Unsupervised Isolation Forest)**: Model machine learning multivariat berbasis 4 dimensi risiko (*Lapse Shock Vol*, *Lapse Shock APE*, *APE Disparity Ratio*, dan *Cash Payment Concentration*).
   - Menghasilkan *Anomaly Score* kontinu (`0.0` hingga `1.0`), klasifikasi status risiko, serta bukti kuantitatif otomatis (*risk drivers*) untuk sidang audit.

4. **Interactive Streamlit Dashboard (`app.py`)**:
   - Filter granular: Kanal Distribusi (`Agency`, `Bancassurance`, `Worksite`) dan Kantor Cabang.
   - Banner KPI Eksekutif: Status standar AAJI, *Premium Leakage Gap*, agen terindikasi risiko, dan polis *Grace Period*.
   - *Dual-Cohort Heatmap* interaktif dan *Multivariate Scatter Map*.
   - *Agent Risk Watchlist* interaktif dengan filter skor, pencarian, dan tombol ekspor audit CSV.
   - *Evidence Drill-Down*: Kurva retensi M1–M24 spesifik per agen terpilih.

5. **PyGWalker Visual Mockup (`mockup_app.py` & `pygwalker_mockup.html`)**:
   - Eksplorasi drag-and-drop ala Tableau langsung di browser.

---

## 🛠️ Instalasi & Menjalankan Proyek

### 1. Kloning Repositori & Instal Dependensi
```bash
pip install -r requirements.txt
```

### 2. Generate Dataset Sintetis (Opsional)
Dataset bawaan sudah tersimpan di direktori `data/`. Untuk meregenerasi:
```bash
python generate_data.py
```

### 3. Jalankan Aplikasi Streamlit
```bash
streamlit run app.py
```

Aplikasi akan otomatis terbuka di browser pada alamat `http://localhost:8501`.

### 4. Menjalankan Mockup PyGWalker
- **Cara 1 (Langsung di Browser)**: Buka file `pygwalker_mockup.html` menggunakan Chrome / Edge.
- **Cara 2 (Streamlit)**:
  ```bash
  streamlit run mockup_app.py
  ```

---

## 🧪 Menjalankan Rangkaian Pengujian (Test Suite)

Pengujian unit dan invarian diatur melalui `pytest`:
```bash
pytest -v
```

Total **21 skenario pengujian** mencakup:
- Invarian generator data & proporsi anomali (`tests/test_generate_data.py`)
- Kalkulasi matriks kohort, rekayasa fitur 4D, & evaluasi recall model $\ge 85\%$ (`tests/test_detector.py`)
- Komponen visual Plotly & KPI dashboard (`tests/test_app_components.py`)

---

## 📂 Struktur Repositori

```text
├── SPEC.md                       # Dokumen spesifikasi teknis proyek
├── TICKETS.md                    # Work breakdown structure (Epic 1 s/d Epic 4)
├── requirements.txt              # Daftar dependensi Python
├── pytest.ini                    # Konfigurasi pengujian pytest
├── generate_data.py              # Engine simulator data sintetis PAYDI
├── detector.py                   # Matriks kohort 2D, fitur 4D, & Two-Tier Detector
├── visuals.py                    # Plotly chart generators & KPI calculators
├── app.py                        # Aplikasi utama Dashboard Streamlit
├── mockup_app.py                 # Mockup visual eksplorasi via PyGWalker
├── pygwalker_mockup.html         # Standalone interactive HTML visual mockup
├── data/                         # Direktori dataset CSV sintetis
│   ├── agents.csv
│   ├── policies.csv
│   └── policy_monthly_status.csv
└── tests/                        # Rangkaian unit test (21 tests)
    ├── test_generate_data.py
    ├── test_detector.py
    └── test_app_components.py
```

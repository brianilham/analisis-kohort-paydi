# Analisis Kohort Persistensi Polis & Deteksi Churn Agen (PAYDI)

Aplikasi analitik aktuaria dan sistem deteksi anomali perilaku agen asuransi untuk produk PAYDI (Produk Asuransi Yang Dikaitkan dengan Investasi / Unit Link). Proyek ini menggabungkan analisis kohort dua dimensi, rekayasa fitur multivariat, dan machine learning tanpa pengawasan (*unsupervised learning*) untuk mendeteksi kecurangan retensi polis (*Hit and Run* dan *Cherry Picking*) secara otomatis.

Desain visual dan tata letak dashboard dirancang mengikuti standar identitas visual PT MNC Life Assurance serta selaras dengan regulasi Surat Edaran Otoritas Jasa Keuangan (SEOJK No. 5/SEOJK.05/2022) dan standar persistensi Asosiasi Asuransi Jiwa Indonesia (AAJI).

---

## 📌 Latar Belakang Masalah Bisnis

Pada industri asuransi jiwa di Indonesia, komisi tahun pertama (*First Year Commission* atau FYC) dan bonus persistensi M13 bernilai sangat besar. Hal ini menciptakan celah moral hazard dan kecurangan terstruktur:

1. **Titik Buta Persistensi Volume Tradisional**:
   Banyak perusahaan asuransi hanya mengukur persistensi dari jumlah lembar polis (Volume). Praktik ini mudah diakali melalui strategi *Cherry Picking*: agen sengaja mempertahankan polis bernilai premi kecil agar rasio volume M13 tetap berada di atas target 80%, sementara polis berpremi besar (*high-ticket*) dibiarkan lapse setelah komisi cair. Akibatnya, laporan audit terlihat hijau, namun nilai premi riil (APE) mengalami kebocoran parah.

2. **Sindikat Hit and Run**:
   Agen menjual polis dengan pembayaran tunai atau talangan pribadi, menjaga polis tetap aktif selama 12 bulan pertama agar komisi FYC cair penuh, lalu membiarkan polis gugur serempak pada bulan ke-13 (M13).

Proyek ini dibangun untuk menutup kedua celah tersebut melalui pengawasan berbasis data yang objektif dan dapat dipertanggungjawabkan saat sidang komite audit.

---

## 💡 Arsitektur Solusi & Metodologi

Sistem ini dibangun atas tiga pilar utama:

### 1. Engine Analisis Kohort 2D (Volume vs APE M1 sampai M24)
- **Matriks Retensi Volume**: Mengukur rasio polis aktif terhadap total polis awal kohort dari bulan M1 sampai M24.
- **Matriks Retensi Premi (APE)**: Mengukur rasio nominal premi aktif terhadap total premi awal kohort.
- **Matriks Selisih Kebocoran Premi (Discrepancy Matrix)**: Mengurangkan retensi Volume dengan retensi APE per sel kohort. Warna biru muda menandakan kondisi selaras (sehat), sementara warna kuning emas hingga merah pekat langsung menandai kebocoran premi akibat manipulasi seleksi polis.
- **Early Warning Grace Period (M11 dan M12)**: Mengisolasi polis dan agen yang memasuki masa tenggang pembayaran tepat sebelum jatuh tempo M13, memberi waktu bagi tim retensi untuk melakukan intervensi penyelamatan premi.

### 2. Rekayasa Fitur Risiko Agen (4 Dimensi)
Setiap agen dievaluasi menggunakan empat parameter kuantitatif:
- `lapse_shock_vol`: Penurunan drastis persentase volume polis dari M12 ke M13.
- `lapse_shock_ape`: Penurunan drastis persentase premi APE dari M12 ke M13.
- `ape_disparity_ratio`: Rasio perbandingan rata-rata premi polis yang lapse dibanding polis yang tetap aktif (nilai di atas 1.5x menandakan indikasi kuat cherry-picking).
- `cash_payment_ratio`: Proporsi transaksi premi yang menggunakan metode pembayaran tunai/manual dibanding auto-debit bank.

### 3. Arsitektur Deteksi Dua Tingkat (Two-Tier Anomaly Detection)
- **Tier 1 (Penyaringan Berbasis Aturan Kepatuhan)**: Menangkap pelanggaran fatal yang jelas melanggar batas regulasi, yaitu penurunan volume M12 ke M13 lebih dari 25% atau persistensi M13 di bawah 75%. Agen yang masuk kategori ini dilabeli sebagai **Hit and Run**.
- **Tier 2 (Isolation Forest Multivariat)**: Model machine learning tanpa pengawasan yang dilatih menggunakan keempat fitur risiko di atas. Model ini bertugas mendeteksi agen yang cerdik mengakali aturan Tier 1 (volume tetap aman di 80%, namun premi besar bocor). Agen yang terdeteksi di tier ini dilabeli sebagai **Cherry Picking**.
- **Skor Anomali Kontinu (0.0 sampai 1.0)**: Menghasilkan peringkat prioritas investigasi bagi auditor, lengkap dengan ringkasan faktor pemicu risiko kuantitatif (*risk drivers*) sebagai alat bukti pemeriksaan.

---

## 🖥️ Tampilan & Fitur Dashboard

Dashboard interaktif dibangun menggunakan Streamlit dan Plotly dengan palet korporat MNC Life (Putih Bersih `#FFFFFF`, Deep Navy `#192C4D`, Warm Gold `#C89B2C`, dan Merah Peringatan `#D94B4B`):

1. **Filter Portofolio Cerdas**: Filter multi-pilih untuk Kanal Distribusi (Agency, Bancassurance, Worksite) dan Kantor Cabang dengan menu dropdown berkontras tinggi.
2. **Kartu Ringkasan Eksekutif**: Menampilkan persistensi M13 volume terhadap standar AAJI (80% - 85%), selisih kebocoran APE, jumlah agen berisiko, serta estimasi nominal premi yang berada di masa tenggang.
3. **Dual Heatmap Kohort**: Visualisasi matriks kohort berdampingan antara volume polis dan nilai premi APE, dilengkapi opsi melihat peta selisih kebocoran premi bergaris kisi rapi.
4. **Peta Sebaran Perilaku Agen**: Grafik bubble multivariat yang memetakan agen ke dalam tiga zona jelas: Agen Normal, Hit and Run, dan Cherry Picking.
5. **Daftar Pemantauan Masa Tenggang**: Rincian polis aktif di M11 dan M12 beserta rasio metode pembayaran (auto-debit vs tunai) untuk tindak lanjut cepat.
6. **Watchlist Risiko Agen & Drill-down Bukti Audit**: Tabel interaktif berfitur pencarian dan unduh laporan audit dalam format CSV. Pengguna dapat memilih kode agen tertentu untuk melihat kurva siklus hidup M1 sampai M24 agen tersebut secara spesifik.

---

## 📁 Struktur Berkas Repositori

```text
├── app.py                       # Aplikasi utama dashboard interaktif Streamlit
├── detector.py                  # Logika matriks kohort, rekayasa fitur 4D, & model deteksi 2-tier
├── visuals.py                   # Modul pembuat grafik Plotly & kalkulasi metrik visual
├── generate_data.py             # Generator data sintetis aktuaria PAYDI
├── requirements.txt             # Daftar dependensi pustaka Python
├── pytest.ini                   # Konfigurasi pengujian otomatis pytest
├── Dockerfile                   # Skrip containerization Docker untuk deployment
├── .dockerignore                # Berkas pengecualian build Docker
├── .streamlit/
│   └── config.toml              # Konfigurasi tema terang & server Streamlit
├── data/
│   ├── agents.csv               # Data profil agen dan kanal distribusi
│   ├── policies.csv             # Data master polis dan nilai APE
│   └── policy_monthly_status.csv# Data log riwayat status bulanan polis (M1-M24)
├── tests/
│   ├── test_generate_data.py    # Pengujian invarian integritas data generator
│   ├── test_detector.py         # Pengujian kalkulasi kohort & recall model
│   └── test_app_components.py   # Pengujian komponen visual dan KPI dashboard
├── mnc_life_logo.svg            # Berkas logo resmi MNC Life Assurance
├── DESIGN.md                    # Dokumentasi spesifikasi sistem desain visual
├── SPEC.md                      # Spesifikasi teknis kebutuhan proyek
└── TICKETS.md                   # Work breakdown structure pengerjaan tiket
```

---

## ⚙️ Panduan Instalasi & Menjalankan Lokal

### 1. Kloning Repositori
```bash
git clone https://github.com/username/analisis-kohort-paydi.git
cd analisis-kohort-paydi
```

### 2. Buat Virtual Environment (Disarankan)
```bash
python -m venv venv

# Di Windows:
venv\Scripts\activate

# Di macOS/Linux:
source venv/bin/activate
```

### 3. Instal Dependensi
```bash
pip install -r requirements.txt
```

### 4. Buat Dataset Sintetis (Opsional)
Dataset bawaan sudah tersedia di dalam folder `data/`. Jika ingin meregenerasi dataset dengan data acak baru:
```bash
python generate_data.py
```

### 5. Jalankan Aplikasi
```bash
streamlit run app.py
```
Aplikasi akan langsung terbuka di browser Anda pada alamat `http://localhost:8501`.

---

## 🚀 Panduan Deployment

### Opsi A: Deployment ke Streamlit Community Cloud (Paling Mudah)
Proyek ini sudah dilengkapi konfigurasi `.streamlit/config.toml` yang kompatibel langsung dengan Streamlit Cloud:
1. Unggah kode ke repositori GitHub Anda.
2. Buka [share.streamlit.io](https://share.streamlit.io/) dan login dengan akun GitHub Anda.
3. Klik **New app**, pilih repositori, branch `main` (atau `master`), dan arahkan Main file path ke `app.py`.
4. Klik **Deploy!** Aplikasi akan aktif dan dapat diakses secara publik dalam beberapa menit.

### Opsi B: Deployment Menggunakan Docker Container
Berkas `Dockerfile` dan `.dockerignore` siap pakai sudah tersedia di repositori.

1. **Build Docker Image**:
   ```bash
   docker build -t paydi-cohort-dashboard:latest .
   ```

2. **Jalankan Docker Container**:
   ```bash
   docker run -d -p 8501:8501 --name paydi-dashboard paydi-cohort-dashboard:latest
   ```
   Buka peramban di `http://localhost:8501`.

3. **Deploy ke Cloud Container (Google Cloud Run / AWS ECS / Render)**:
   - Tag image ke container registry cloud pilihan Anda:
     ```bash
     docker tag paydi-cohort-dashboard:latest gcr.io/PROJECT_ID/paydi-dashboard:latest
     docker push gcr.io/PROJECT_ID/paydi-dashboard:latest
     ```
   - Deploy sebagai layanan serverless container dengan port `8501`.

---

## 🧪 Rangkaian Pengujian Otomatis (Test Suite)

Keandalan seluruh formula aktuaria dan model deteksi diverifikasi menggunakan `pytest`. Jalankan seluruh pengujian dengan perintah:

```bash
pytest -v
```

Hasil pengujian mencakup 21 test case yang lulus 100%:
- **Invarian Generator Data** (`tests/test_generate_data.py`): Memastikan volume 12.000 polis, 200 agen, kepatuhan batas OJK populasi normal, serta validitas aturan transisi satu arah (polis yang lapse tidak hidup kembali secara ilegal).
- **Kalkulasi Kohort & Evaluasi Model** (`tests/test_detector.py`): Memverifikasi keakuratan formula persistensi volume dan APE, sifat monotonik kurva retensi, serta target recall deteksi anomali di atas 85%.
- **Komponen Visual Dashboard** (`tests/test_app_components.py`): Memastikan heatmap, scatter plot, dan kalkulator ringkasan KPI eksekutif menghasilkan visual bebas error.

---

## 📈 Nilai Tambah bagi Manajemen & Portofolio

- **Sinergi Domain Aktuaria & Data Science**: Menggabungkan pemahaman mendalam tentang siklus hidup polis asuransi unit link dengan teknik deteksi anomali modern.
- **Penyelamatan Finansial Nyata**: Membantu tim audit dan retensi mendeteksi kebocoran premi miliaran rupiah sebelum masa pembukuan tahunan ditutup.
- **Standar Rekayasa Perangkat Lunak Tinggi**: Kode terstruktur bersih (*clean code*), berorientasi fungsi, terdokumentasi rapi, dan dilindungi oleh 21 unit test otomatis.

# Analisis kohort persistensi polis dan deteksi churn agen (PAYDI)

Aplikasi analitik aktuaria dan sistem deteksi anomali perilaku agen asuransi untuk produk PAYDI (Produk Asuransi Yang Dikaitkan dengan Investasi atau Unit Link). Proyek ini menggabungkan analisis kohort dua dimensi, rekayasa fitur multivariat, dan machine learning tanpa pengawasan (Isolation Forest) untuk menemukan pola kecurangan retensi polis, khususnya Hit and Run dan Cherry Picking.

Desain dashboard mengadopsi identitas visual PT MNC Life Assurance, dengan rujukan regulasi Surat Edaran Otoritas Jasa Keuangan (SEOJK No. 5/SEOJK.05/2022) serta standar persistensi Asosiasi Asuransi Jiwa Indonesia (AAJI).

Live demo dashboard dapat diakses langsung pada tautan berikut:  
👉 [https://brianilham-analisis-kohort-paydi-app-apv1xd.streamlit.app/](https://brianilham-analisis-kohort-paydi-app-apv1xd.streamlit.app/)

> Catatan kerahasiaan data: Seluruh data yang digunakan pada proyek dan dashboard ini merupakan data sintetis (dummy) terprogram. Langkah ini diambil karena data polis dan agen riil milik perusahaan bersifat rahasia (confidential). Struktur atribut, persebaran premi, dan skenario kecurangan disimulasikan mendekati kondisi industri sebenarnya.

---

## Masalah bisnis

Pada industri asuransi jiwa, komisi tahun pertama (First Year Commission atau FYC) dan bonus persistensi bulan ke-13 (M13) memiliki porsi nominal yang besar. Struktur insentif ini kerap menimbulkan celah moral hazard:

1. Titik buta persistensi volume: Sebagian besar pemantauan hanya melihat persentase jumlah lembar polis yang aktif. Celah ini dimanfaatkan lewat modus Cherry Picking. Agen menjaga polis bernilai kecil tetap aktif agar rasio volume M13 tetap di atas batas 80%, sementara polis berpremi besar dibiarkan mati (lapse) begitu komisi cair. Hasilnya, laporan volume tampak patuh, tetapi premi tahunan riil (APE) bocor dalam jumlah besar.

2. Modus Hit and Run: Agen menjual polis dengan pembayaran tunai atau talangan premi sendiri, mempertahankan status aktif selama 12 bulan pertama agar komisi FYC cair penuh, lalu membiarkan polis gugur massal pada bulan ke-13.

Sistem ini dirancang untuk memetakan kedua risiko tersebut secara transparan melalui bukti kuantitatif yang siap dipakai dalam evaluasi audit.

---

## Metodologi dan arsitektur deteksi

Sistem analisis ini menggunakan tiga komponen utama:

### 1. Analisis kohort dua dimensi (M1 sampai M24)
- Matriks retensi volume: Mengukur rasio jumlah polis aktif terhadap basis polis awal per bulan terbit (Issue Date).
- Matriks retensi premi APE: Mengukur rasio nilai premi aktif terhadap basis premi awal kohort.
- Matriks selisih kebocoran premi: Mengurangkan persentase retensi volume dengan persentase retensi APE pada setiap sel bulan. Warna biru menandai keselarasan retensi, sedangkan warna emas hingga merah pekat menandai kebocoran premi.
- Pemantauan masa tenggang (Grace Period M11 dan M12): Menyaring polis yang menunggak tepat sebelum jatuh tempo M13, sehingga tim retensi dapat melakukan intervensi sebelum polis berstatus lapse permanen.

### 2. Rekayasa fitur risiko agen
Setiap agen diukur melalui empat metrik:
- `lapse_shock_vol`: Penurunan persentase volume polis antara M12 dan M13.
- `lapse_shock_ape`: Penurunan persentase premi APE antara M12 dan M13.
- `ape_disparity_ratio`: Rasio perbandingan rata-rata premi polis yang lapse terhadap polis yang masih aktif. Nilai di atas 1.5x menandakan indikasi cherry picking.
- `cash_payment_ratio`: Porsi polis yang menggunakan pembayaran manual atau tunai dibanding auto-debit perbankan.

### 3. Deteksi anomali dua tingkat
- Tier 1 (Penyaringan aturan): Menandai agen dengan penurunan volume M12 ke M13 melebihi 25% atau persistensi volume M13 di bawah 75%. Kategori ini dikelompokkan sebagai Hit and Run.
- Tier 2 (Isolation Forest): Model machine learning multivariat yang memproses keempat fitur risiko secara serentak. Model ini menangkap anomali halus yang lolos dari saringan volume Tier 1. Kategori ini dikelompokkan sebagai Cherry Picking.
- Skor risiko kontinu (0.0 sampai 1.0): Menghasilkan urutan prioritas pemeriksaan dan ringkasan pemicu risiko (risk drivers) otomatis untuk sidang komite kepatuhan.

---

## Tampilan dashboard

Antarmuka dibangun dengan Streamlit dan Plotly menggunakan warna korporat MNC Life:

- Filter portofolio: Pilihan kanal distribusi dan kantor cabang dengan dropdown kontras tinggi.
- Ringkasan eksekutif: Kartu KPI untuk persistensi volume M13 terhadap standar AAJI (80% sampai 85%), selisih kebocoran APE, jumlah agen berisiko, dan total premi masa tenggang.
- Heatmap kohort: Pilihan tampilan berdampingan (Volume vs APE) atau peta selisih kebocoran bergaris kisi.
- Peta sebaran agen: Grafik bubble yang memisahkan kelompok Agen Normal, Hit and Run, dan Cherry Picking.
- Daftar masa tenggang: Tabel polis rawan lapse pada M11 dan M12 beserta rasio metode pembayaran.
- Daftar pengawasan agen: Tabel interaktif dengan filter skor, pencarian nama atau kode agen, tombol unduh laporan CSV, serta kurva siklus hidup M1 sampai M24 untuk agen yang dipilih.

---

## Struktur berkas

```text
├── app.py                       # Aplikasi dashboard Streamlit
├── detector.py                  # Kalkulasi matriks kohort, fitur 4D, dan model deteksi
├── visuals.py                   # Generator visualisasi Plotly dan kalkulasi KPI
├── generate_data.py             # Generator data sintetis aktuaria PAYDI
├── requirements.txt             # Dependensi pustaka Python
├── pytest.ini                   # Konfigurasi pytest
├── Dockerfile                   # Konfigurasi container Docker
├── .dockerignore                # Pengecualian berkas Docker
├── .streamlit/
│   └── config.toml              # Pengaturan tema dan server Streamlit
├── data/
│   ├── agents.csv               # Data profil agen
│   ├── policies.csv             # Data master polis dan premi APE
│   └── policy_monthly_status.csv# Riwayat status bulanan polis (M1-M24)
├── tests/
│   ├── test_generate_data.py    # Pengujian generator data
│   ├── test_detector.py         # Pengujian logika kohort dan evaluasi model
│   └── test_app_components.py   # Pengujian visualisasi dan kartu KPI
├── mnc_life_logo.svg            # Berkas logo resmi MNC Life Assurance
├── DESIGN.md                    # Dokumentasi spesifikasi visual
├── SPEC.md                      # Dokumen spesifikasi teknis
└── TICKETS.md                   # Rincian tiket pengerjaan
```

---

## Menjalankan proyek secara lokal

### 1. Kloning repositori
```bash
git clone https://github.com/brianilham/analisis-kohort-paydi.git
cd analisis-kohort-paydi
```

### 2. Pasang environment dan dependensi
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Buat dataset sintetis (opsional)
Dataset awal sudah disertakan pada folder `data/`. Untuk memperbarui data secara acak:
```bash
python generate_data.py
```

### 4. Buka dashboard
```bash
streamlit run app.py
```
Aplikasi akan berjalan pada `http://localhost:8501`.

---

## Deployment

### Streamlit Community Cloud
Aplikasi ini sudah dipublikasikan dan dapat diakses di:  
[https://brianilham-analisis-kohort-paydi-app-apv1xd.streamlit.app/](https://brianilham-analisis-kohort-paydi-app-apv1xd.streamlit.app/)

Jika ingin memasang ulang pada akun Streamlit Cloud pribadi:
1. Masuk ke [share.streamlit.io](https://share.streamlit.io/) dengan akun GitHub.
2. Pilih repositori `brianilham/analisis-kohort-paydi`, branch `main`, dan file `app.py`.
3. Klik tombol Deploy.

### Docker container
Berkas Dockerfile sudah siap digunakan di lingkungan produksi:

```bash
# Build image
docker build -t paydi-cohort-dashboard:latest .

# Jalankan container
docker run -d -p 8501:8501 --name paydi-dashboard paydi-cohort-dashboard:latest
```

---

## Pengujian otomatis

Seluruh logika aktuaria dan model diuji melalui pytest:

```bash
pytest -v
```

Rangkaian uji mencakup 21 skenario:
- Invarian generator data: Volume 12.000 polis, 200 agen, dan transisi status satu arah tanpa pemulihan ilegal.
- Seam kalkulasi kohort dan recall model: Pengujian konsistensi formula retensi dan target recall deteksi di atas 85%.
- Komponen visual: Pengecekan stabilitas visual Plotly dan kalkulator KPI.

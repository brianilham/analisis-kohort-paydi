# SPEC.md: Analisis Kohort Persistensi Polis & Deteksi Churn Agen (PAYDI) — Edisi Power BI (.pbip)

## Problem Statement

Perusahaan asuransi jiwa menghadapi tantangan pemantauan persistensi polis untuk produk PAYDI (*Produk Asuransi Yang Dikaitkan dengan Investasi* / *Unit Link*) serta risiko kebocoran finansial akibat manipulasi agen demi mengejar komisi tahun pertama (*First Year Commission* / FYC) dan bonus persistensi bulan ke-13 (M13).

Terdapat tiga masalah utama pada pendekatan pemantauan dan prototipe awal yang harus diselesaikan:

1. **Titik Buta Persistensi Volume vs Nilai Premi (APE):** Praktik *hit-and-run* (pembiaran polis gugur massal tepat setelah komisi M12/M13 cair) dan *cherry-picking* (mempertahankan polis bernominal kecil agar rasio volume M13 tetap tampak patuh di atas 80%, sambil membiarkan polis bernilai APE besar *lapse*) tidak terdeteksi oleh laporan agregat konvensional.
2. **Tabrakan Aturan Deteksi & Kurangnya Explainability Model ML:** Aturan saringan deterministik (Tier 1) yang mencampuradukkan penurunan bertahap (*natural attrition* M1–M12 di bawah 75% dengan *lapse shock* M12→M13 sebesar 0%) menyebabkan *false positive* pada agen normal, sementara kalibrasi *cherry-picking* yang bocor ke Tier 1 mengaburkan pemisahan modus kecurangan. Selain itu, skor tunggal *Isolation Forest* (`0.0–1.0`) bersifat *black-box* dan sulit dicerna auditor tanpa dekomposisi visual per pilar risiko.
3. **Kebutuhan Standarisasi BI Korporat & Kredibilitas Kalender Aktuaria:** Penggunaan aplikasi web kustom memerlukan pemeliharaan terpisah dari ekosistem *Business Intelligence* perusahaan, sementara simulasi kohort membutuhkan kerangka waktu *Fully Seasoned Cohort Study* (24 bulan observasi penuh per kohort terbit) serta perhitungan KPI berbobot standar aktuaria/BI yang terintegrasi di **Power BI Project (`.pbip`)**.

## Solution

Sistem analitik aktuaria dan deteksi anomali agen *end-to-end* yang memadukan **pipeline Python (Data Generation, 4D Feature Engineering, Calibrated Two-Tier Detection, & Explainable Risk Pillar Decomposition)** dengan **Power BI Project (`.pbip` berbasis TMDL & PBIR)** beridentitas visual PT MNC Life Assurance:

1. **Fully Seasoned Synthetic Data Generator (`2022-01` s/d `2023-12`):** Mensimulasikan 24 kohort bulanan yang seluruhnya telah menyelesaikan jendela observasi 24 bulan polis (`M1–M24`), dengan injeksi perilaku *Normal* (92%), *Hit-and-Run* (3%), dan *Cherry-Picking* (5%) yang terkalibrasi secara aktuaria.
2. **Calibrated Two-Tier Detection Engine:**
   - **Tier 1 (*Rule-Based Hit-and-Run Screening*):** Menangkap guncangan *lapse* akut pada transisi komisi M12→M13 tanpa menjebak agen normal yang hanya mengalami penurunan bertahap alami.
   - **Tier 2 (*Unsupervised Isolation Forest for Cherry-Picking*):** Menangkap anomali multivariat di mana volume polis M13 sengaja dijaga aman (~80%), tetapi nilai premi APE mengalami kebocoran tajam disertai disparitas ukuran polis (*lapsed vs active*) yang ekstrem.
3. **Visual Explainability via 4 Normalized Risk Pillars (`0–100`):** Menguraikan skor anomali *Isolation Forest* ke dalam 4 skor pilar risiko ternormalisasi (*Volume Shock*, *APE Leakage Shock*, *Ticket-Size Disparity*, dan *Cash Funding Concentration*) beserta persentase kontribusi pemicu utamanya terhadap benchmark populasi normal.
4. **Power BI Project (`.pbip` — Semantic Model TMDL + Single-Page Executive Helicopter View PBIR):**
   - Model data *Star Schema* lengkap dengan parameter sumber data portabel (`DataFolderPath`) dan ukuran **DAX Berbobot (*Weighted Portfolio Standard*)** termasuk validasi akurasi model & dekomposisi 4 pilar risiko.
   - Antarmuka **Single-Page Executive Helicopter View (`1280 × 720`, 13 Visual)** untuk menghindari *cognitive overload*: Header & Logo MNC Life + 3 Global Slicers (`Channel`, `Cabang`, `Kategori Risiko`), 4 North Star KPI Cards dengan *accent bar* dan *tooltip* pendalaman, *Kurva Retensi Kohort M1–M24 (Volume vs APE)* beserta target AAJI 85%, *Early Warning Grace Period M11–M12 per Cabang & Metode Bayar*, *Peta Klaster Anomali Agen (Scatter Plot)*, dan *Executive Audit Watchlist* interaktif dengan *cross-filtering*.

## User Stories

1. As an Actuarial Analyst, I want to track 24-month policy persistency (`M1–M24`) across fully seasoned cohorts (`2022-01` to `2023-12`), so that I can evaluate full 2-year policy lifecycle persistency against the AAJI/OJK M13 benchmark (85%) without right-censoring distortion.
2. As an Actuarial Analyst, I want to compare persistency calculated by policy volume against persistency calculated by Annualized Premium Equivalent (APE) on the same curve and KPI tooltips (`Leakage Gap %` and `Leaked APE`), so that I can immediately spot premium leakage hidden behind healthy policy counts.
3. As an Actuarial Analyst, I want all executive M13 KPI cards in Power BI to use weighted portfolio ratios (`Total Active at M13 / Total Initial`) and distinct policy counts/APE, so that KPI summary cards always reconcile seamlessly across filters.
4. As a Compliance Auditor, I want Tier 1 screening to isolate agents experiencing acute M12-to-M13 volume lapse shocks (`> 25%`, or `< 75%` M13 volume accompanied by `>= 15%` M12-to-M13 shock), so that normal agents with gradual attrition and zero M13 shock are not falsely accused of *Hit-and-Run*.
5. As a Fraud Risk Investigator, I want Tier 2 (*Isolation Forest*) to accurately classify *Cherry-Picking* agents who keep M13 policy volume near ~80% while dropping high-ticket policies, so that subtle commission manipulation is separated cleanly from *Hit-and-Run*.
6. As a Fraud Risk Investigator, I want every agent's *Isolation Forest* anomaly score (`0.0–1.0`) accompanied by 4 normalized Risk Pillar scores (`0–100`) and plain-language `primary_risk_drivers` in the semantic model & watchlist, so that I can visually explain *why* an agent was flagged during audit hearings without relying on a black-box number.
7. As an Agency Director, I want global synchronized slicers for Distribution Channel, Branch Office, and Risk Category on the single-page executive cockpit, so that I can isolate structural and geographic persistency issues in seconds without switching tabs.
8. As a Compliance Officer, I want to inspect `Manual/Cash` versus `Auto-Debit` grace period exposure by branch office, so that I can detect potential self-funding risk and prioritize collection interventions before M13.
9. As a Retention Manager, I want a dedicated *Early Warning Grace Period (M11–M12)* KPI card (with distinct policies & cash ratio tooltips) and branch bar chart right on the main screen, so that proactive retention calls can be prioritized by largest APE at risk.
10. As an Internal Auditor, I want an interactive *Executive Audit Watchlist* sorted from Risk Rank #1 directly beside the Anomaly Scatter Plot, with one-click *cross-filtering* to isolate that agent's M1–M24 Volume vs APE lifecycle curve on the same screen.
11. As a Portfolio Reviewer / Risk Committee Member, I want ground-truth validation measures (`Top-20% Recall %`, `Overall Recall %`, `Detection Precision %`) computed inside the TMDL semantic model and surfaced in card tooltips / subtitle indicators, so that model effectiveness is verifiable without cluttering the executive dashboard.
12. As a BI Developer, I want the entire dashboard authored in Git-friendly **Power BI Project (`.pbip`)** format (TMDL Semantic Model + PBIR Report + MNC Life Theme JSON) with a configurable `DataFolderPath` Power Query parameter, so that the project can be version-controlled in GitHub and opened or exported to `.pbix` on any machine running Power BI Desktop.
13. As a Data Engineer, I want a single deterministic Python ETL command that generates/validates the synthetic dataset, runs feature engineering and two-tier detection, computes the 4 explainability pillars, and exports clean CSV tables and PNG brand assets for Power BI consumption.

## Implementation Decisions

- **Fully Seasoned Synthetic Data Generator (`2022-01` to `2023-12`)**:
  - Mensimulasikan 24 kohort bulanan (`start_cohort = "2022-01"`, `n_cohorts = 24`) dengan 200 agen dan 12.000 polis yang seluruhnya telah melewati 24 bulan polis (`M1–M24`) pada saat tanggal evaluasi audit.
  - Memodelkan 4 status siklus hidup polis satu arah (tanpa *illegal resurrection*): `Active`, `Grace Period`, `Lapsed`, dan `Surrendered`.
  - Proporsi *ground-truth* populasi agen: `92%` *Normal* (184 agen), `3%` *Hit-and-Run* (6 agen), dan `5%` *Cherry-Picking* (10 agen):
    - **Normal**: Mayoritas `Auto-Debit` (~80%), penurunan alami bertahap dengan variansi terkendali sehingga persistensi M13 berada di rentang standar AAJI/OJK **80%–85%** tanpa guncangan mendadak di M13.
    - **Hit-and-Run**: Mayoritas `Manual/Cash` (~75%), persistensi M1–M12 sangat tinggi (>92%), lalu anjlok serempak (>35%–60% drop) pada M13–M14 tepat setelah komisi tahun pertama cair.
    - **Cherry-Picking**: Memiliki distribusi premi bimodal yang dikalibrasi (~85% polis bernominal kecil Rp 4–9 Juta dengan retensi tinggi sebagai penyangga volume, dan ~15% polis *jumbo* Rp 60–150 Juta yang sengaja dibiarkan *lapse* >85% pada M13). Dengan kalibrasi ini, **Persistensi Volume M13 tetap bertahan di ~78%–83%** (lolos aturan volume Tier 1), sementara **Persistensi APE M13 anjlok drastis** dan rasio disparitas premi sangat tinggi.

- **Agent-Level 4D Feature Engineering & 4-Pillar Explainability Decomposition**:
  - Empat fitur inti per agen:
    1. `lapse_shock_vol`: $\max(0, \text{Persistency}_{Vol, M12} - \text{Persistency}_{Vol, M13})$.
    2. `lapse_shock_ape`: $\max(0, \text{Persistency}_{APE, M12} - \text{Persistency}_{APE, M13})$.
    3. `ape_disparity_ratio`: Rasio rata-rata APE polis yang tidak aktif di M13 terhadap rata-rata APE polis yang masih aktif di M13 ($\frac{\overline{\text{APE}}_{\text{Lapsed M13}}}{\overline{\text{APE}}_{\text{Active M13}}}$).
    4. `cash_payment_ratio`: Persentase polis agen yang menggunakan metode pembayaran `Manual/Cash`.
  - **Dekomposisi 4 Skor Pilar Risiko (`0–100`) & Kontribusi Fitur**:
    - Setiap fitur dikonversi menjadi skor keparahan ternormalisasi pada skala `0.0–100.0` berdasarkan ambang batas risiko aktuaria (`score_vol_shock`, `score_ape_shock`, `score_ape_disparity`, `score_cash_ratio`).
    - Menghitung persentase kontribusi relatif tiap pilar (`share_vol_shock_pct`, `share_ape_shock_pct`, `share_ape_disparity_pct`, `share_cash_ratio_pct` yang berjumlah 100%) serta `dominant_risk_pillar` untuk membuka *black-box* model secara visual di Power BI.

- **Calibrated Two-Tier Detection Architecture**:
  - **Tier 1 (*Deterministic Hit-and-Run Screening*)**:
    - Menandai agen sebagai `tier1_violation = True` jika mengalami guncangan volume akut di M13: `lapse_shock_vol > 25.0%` **ATAU** (`m13_vol_persistency < 75.0%` **DAN** `lapse_shock_vol >= 15.0%`).
    - Mencegah agen normal dengan *attrition* alami bertahap (shock M12→M13 mendekati 0%) salah diklasifikasikan sebagai *Hit and Run*.
  - **Tier 2 (*Unsupervised Isolation Forest*)**:
    - Melatih `IsolationForest(n_estimators=150, contamination=0.08, random_state=42)` pada 4 fitur yang telah distandarisasi (`StandardScaler`).
    - Menghasilkan `anomaly_score` kontinu dalam rentang `[0.0, 1.0]` dan flag `tier2_anomaly`.
  - **Aturan Klasifikasi Kategori Risiko (`risk_category`)**:
    - Agen yang melanggar Tier 1 dikategorikan sebagai **`Hit and Run`**.
    - Agen yang lolos Tier 1 namun terdeteksi oleh Tier 2 (atau menunjukkan tanda *cherry-picking* multivariat: `lapse_shock_ape >= 25%` dan `ape_disparity_ratio >= 1.8` saat `tier2_anomaly` aktif) dikategorikan sebagai **`Cherry Picking`**.
    - Agen lainnya dikategorikan sebagai **`Normal`**.

- **Batch Python ETL Pipeline untuk Power BI**:
  - Pipeline Python mengekspor 5 tabel CSV bersih ke direktori data:
    1. Master Agen (`200` baris)
    2. Master Polis (`12.000` baris)
    3. Riwayat Status Bulanan Polis M1–M24 (`288.000` baris)
    4. Tabel Skor & Fitur Risiko Agen (`200` baris: mencakup fitur 4D, skor Tier 1/2, 4 skor pilar `0–100`, kontribusi %, peringkat risiko `risk_rank`, flag `is_top20_risk_rank`, dan nilai benchmark rata-rata normal).
    5. Tabel *Unpivoted* Pilar Risiko Agen (`800` baris = `200` agen × `4` pilar: menyimpan nilai aktual agen, benchmark normal, skor `0–100`, dan % kontribusi per pilar untuk visual perbandingan di Power BI).
  - Menyediakan aset logo PNG beresolusi tinggi hasil konversi dari logo SVG resmi MNC Life.

- **Arsitektur Power BI Project (`.pbip` — TMDL & PBIR)**:
  - **Semantic Model (`TMDL`)**:
    - Menggunakan parameter Power Query `DataFolderPath` agar lokasi folder CSV dapat disesuaikan dengan mudah saat repositori dipindahkan.
    - *Star Schema*: `DimAgent` (1) → (*) `DimPolicy` (1) → (*) `FactPolicyMonthlyStatus`, serta `DimAgent` (1) → (*) `FactAgentRiskPillars`.
    - Kolom `Month Label` (`M1` s/d `M24`) pada `FactPolicyMonthlyStatus` dikonfigurasi dengan `sortByColumn: month_index` agar urutan sumbu waktu dan kolom matriks selalu terurut secara numerik (`M1, M2, ..., M24`).
    - Kolom persentase pra-skala `0–100` (`lapse_shock_vol`, `lapse_shock_ape`, `m12/m13_vol_persistency`, `cash_payment_ratio`, dan kontribusi pilar) menggunakan `formatString: 0.0"%"` agar tidak dikalikan 100 oleh Power BI.
    - Kolom `risk_category` dipertahankan sebagai kolom fisik di `DimAgent` agar dapat digunakan langsung pada *Slicer* dan *Legend Scatter Chart* Power BI, dikombinasikan dengan **DAX Measures** dinamis berstandar berbobot (*weighted portfolio ratio*) termasuk `M13 Leaked APE (Miliar IDR)` dan perhitungan *distinct* polis pada *Grace Period*.
  - **Report Layer (`PBIR` + Theme MNC Life)**:
    - Mengadopsi palet warna korporat MNC Life (`Primary Navy #192C4D`, `Warm Gold #C89B2C`, `Alert Red #D94B4B`, `Compliance Emerald #1E6B52`, `Light Surface #F5F8FC`, `Crisp Border #D9E5F2`).
    - Dikonsolidasikan menjadi **1 Halaman Utama (`Executive Helicopter View`, kanvas `1280 × 720`, 13 Visual)** untuk menghindari kelelahan navigasi (*tab fatigue*) dan memastikan informasi tersampaikan instan dalam satu layar:
      1. **Header Strip & Global Slicers**: Logo resmi MNC Life (`RegisteredResources`), judul ringkas bebas *scrollbar*, dan 3 Dropdown Slicer (`Channel`, `Cabang`, `Kategori Risiko`).
      2. **4 North Star KPI Cards (`cardVisual` dengan *Left Accent Bar* & *Tooltips*)**: `M13 Volume Persistency %` (tooltip selisih benchmark AAJI), `M13 APE Persistency %` (tooltip `M13 Leakage Gap %` & `M13 Leaked APE (Miliar IDR)`), `Grace Period APE (Miliar IDR)` (tooltip jumlah polis kritis & rasio pembayaran tunai), serta `Flagged Agents Count` (tooltip rincian Hit & Run, Cherry Picking, dan `Top-20% Recall %`).
      3. **Kurva Retensi Kohort M1–M24 (`lineChart`)**: Membandingkan tren `Persistency Volume %` (Navy) vs `Persistency APE %` (Coral Red) lengkap dengan garis konstan emas `Target AAJI (85%)` dan *cross-filtering* otomatis saat agen diklik.
      4. **Early Warning Grace Period M11–M12 per Cabang & Bayar (`clusteredBarChart`)**: Menampilkan cabang dengan premi kritis terbesar beserta pembagian `Manual/Cash` vs `Auto-Debit` dalam satu grafik terurut menurun.
      5. **Peta Klaster Anomali Agen (`scatterChart`)**: Memvisualisasikan `lapse_shock_vol` vs `lapse_shock_ape` berukuran `ape_disparity_ratio` dengan pewarnaan per klaster (`Hit and Run`, `Cherry Picking`, `Normal`).
      6. **Executive Audit Watchlist (`tableEx`)**: Menampilkan 5 kolom berdaya baca tinggi (`Rank`, `Nama Agen`, `Klaster`, `Skor`, dan `Pemicu Risiko Utama`) yang diurutkan dari risiko tertinggi (`risk_rank` Ascending).

- **Strategi Migrasi Penuh (*Expand–Contract Cleanup*)**:
  - Fase *Expand*: Membangun dan memverifikasi pipeline ETL Python serta proyek Power BI (`.pbip`) hingga seluruh tes dan validasi Power BI Desktop lulus.
  - Fase *Contract*: Menghapus seluruh artefak UI Streamlit, Docker, dan mockup lama, merampingkan dependensi Python hanya untuk kebutuhan data/ML/testing, serta memperbarui dokumentasi utama repositori.

## Testing Decisions

- **Prinsip Pengujian**: Pengujian difokuskan pada perilaku eksternal (*external behavior*) dan invarian bisnis pada batas modul tertinggi (*highest seams*), tanpa menguji detail implementasi internal.
- **Seam 1 — Data Generator Invariant Tests**:
  - Memastikan dimensi dataset (200 agen, 12.000 polis, 24 kohort bulanan dari `2022-01` s/d `2023-12`, indeks bulan `1–24`).
  - Memastikan integritas referensial dan validitas transisi status satu arah (polis `Lapsed` atau `Surrendered` tidak pernah kembali menjadi `Active` atau `Grace Period`).
  - Memastikan persistensi M13 populasi `Normal` berada di rentang **80%–85%**, serta populasi `Cherry-Picking` mempertahankan persistensi Volume M13 $\ge 75\%$ sambil mengalami penurunan APE M13 yang tajam.
- **Seam 2 — Cohort Calculation, 4D Features & 4-Pillar Explainability Tests**:
  - Memvalidasi sifat monoton menurun/konstan ($M_{t+1} \le M_t$) pada matriks kohort Volume dan APE 24×24.
  - Memastikan seluruh fitur 4D, 4 skor pilar risiko (`0–100`), dan persentase kontribusi fitur (berjumlah 100% bagi agen berisiko) bebas dari `NaN` atau `inf`.
- **Seam 3 — Calibrated Two-Tier Detection & Power BI ETL Export Tests**:
  - Memvalidasi **Top-20% Risk Ranking Recall $\ge 85\%$** terhadap label *ground-truth*.
  - Memvalidasi kemurnian pemisahan klaster: agen `Hit-and-Run` tertangkap sebagai `Hit and Run`, mayoritas agen `Cherry-Picking` tertangkap sebagai `Cherry Picking` (tidak tertelan aturan Tier 1), dan agen `Normal` tanpa *shock* M13 tidak terkena *false positive* `Hit and Run`.
  - Memvalidasi kelengkapan skema dan jumlah baris dari seluruh file CSV dan aset logo PNG yang diekspor untuk Power BI.
- **Seam 4 — Power BI Semantic Model & PBIR Verification**:
  - Memvalidasi struktur proyek `.pbip` (`definition.pbism`, `definition.pbir`, file `.tmdl`, dan JSON halaman/visual PBIR) serta mengevaluasi ukuran DAX pada model untuk memastikan angka KPI M13, *Grace Period*, dan *Model Validation* akurat dan konsisten dengan hasil perhitungan Python.

## Out of Scope

- Integrasi *real-time* (DirectQuery/streaming) ke database produksi *core-insurance*.
- Penyediaan *On-premises Data Gateway* atau lisensi *Power BI Service / Microsoft Fabric* berbayar (proyek dirancang agar berjalan mandiri di Power BI Desktop melalui format `.pbip` / `.pbix`).
- Pemodelan aktuaria untuk cadangan klaim (*actuarial reserve valuation*) atau perhitungan *clawback* komisi otomatis ke sistem *payroll*.
- Pertahanan antarmuka lama berbasis Streamlit, Docker container, atau PyGWalker setelah migrasi ke Power BI selesai diverifikasi.

## Further Notes

- Acuan regulasi kepatuhan mengacu pada Surat Edaran Otoritas Jasa Keuangan (**SEOJK No. 5/SEOJK.05/2022**) tentang PAYDI dan standar persistensi **Asosiasi Asuransi Jiwa Indonesia (AAJI)**.
- Desain antarmuka laporan Power BI mengacu penuh pada sistem desain korporat PT MNC Life Assurance (`DESIGN.md`).

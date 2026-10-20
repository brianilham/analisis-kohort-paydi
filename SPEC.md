# SPEC.md: Analisis Kohort Persistensi Polis & Deteksi Churn Agen (PAYDI)

## Problem Statement

Perusahaan asuransi jiwa menghadapi tantangan pemantauan persistensi polis (khususnya produk PAYDI / Unit Link) dan risiko kebocoran finansial akibat manipulasi agen demi komisi tahun pertama (*First Year Commission* / FYC) serta bonus persistensi M13. 

Praktik kecurangan seperti *hit-and-run* (pembiaran polis mati serempak pasca-bulan ke-12) dan *cherry-picking* (mempertahankan polis kecil demi rasio volume, tetapi membiarkan polis besar mati) sulit dideteksi dengan laporan agregat konvensional atau aturan *rule-based* kaku. Ketiadaan visibilitas granular antara persistensi volume polis versus nilai premi (*APE*) membuat tim audit dan aktuaria terlambat memitigasi agen berisiko tinggi.

## Solution

Aplikasi analitik interaktif berbasis Streamlit yang mengintegrasikan:
1. Generator data sintetis berbasis aturan aktuaria PAYDI dan regulasi OJK/AAJI.
2. Matriks analisis kohort dua dimensi (*Volume Matrix* vs *APE Matrix*) dari M1 hingga M24.
3. Mesin deteksi anomali *two-tier* (penyaringan *rule-based* ditambah model *Isolation Forest* multivariat).
4. *Agent Risk Watchlist* interaktif yang dilengkapi pembuktian visual *dual-cohort heatmap* dan interpretabilitas fitur.

## User Stories

1. As an Actuarial Analyst, I want to view a monthly cohort retention matrix from M1 to M24, so that I can evaluate whether 13-month persistency aligns with the AAJI/OJK benchmark (80%–85%).
2. As an Actuarial Analyst, I want to compare cohort persistency calculated by policy volume against persistency calculated by annualized premium equivalent (APE), so that I can detect premium leakage hidden behind healthy policy volume numbers.
3. As a Compliance Auditor, I want a rule-based screening filter, so that I can instantly isolate agents whose lapse shock between M12 and M13 exceeds compliance thresholds.
4. As a Fraud Risk Investigator, I want an unsupervised anomaly detection model using Isolation Forest, so that I can identify subtle cherry-picking behaviors where agents manipulate volume while dropping high-value policies.
5. As a Fraud Risk Investigator, I want anomaly scores accompanied by risk driver metrics for each agent, so that I can present defensible quantitative evidence during audit hearings.
6. As an Agency Director, I want to filter cohort matrices by distribution channel and branch office, so that I can isolate geographic or structural problem areas.
7. As a Compliance Officer, I want to inspect the proportion of manual/cash payments versus auto-debit per agent, so that I can spot agents potentially funding policies on behalf of dummy customers.
8. As a Retention Manager, I want visibility into policies entering the Grace Period around M11 and M12, so that proactive retention initiatives can be launched before policies lapse at M13.
9. As a Business Stakeholder, I want an interactive Streamlit dashboard with side-by-side heatmaps and scatter plots, so that I can explore agent risk profiles without running ad-hoc queries.
10. As a Data Engineer, I want a parameterized synthetic data pipeline, so that realistic insurance datasets matching OJK distribution rules can be reproduced on demand with deterministic ground-truth labels.
11. As a Data Scientist, I want agent-level feature engineering covering lapse shock, APE disparity, payment channels, and grace period volatility, so that the anomaly detection model receives balanced and non-collinear features.
12. As an Internal Auditor, I want to export the prioritized Agent Risk Watchlist into CSV format, so that it can be directly imported into audit management systems.

## Implementation Decisions

- **Synthetic Data Generator Engine**:
  - Mensimulasikan 24 kohort bulanan (*Issue Date* rentang 2 tahun) dengan skala 10.000–15.000 polis dari 150–200 agen.
  - Memodelkan 4 siklus status polis bulanan: `Active`, `Grace Period` (30–45 hari), `Lapsed`, dan `Surrendered`.
  - Menginjeksikan *ground truth* anomali sebesar 8% dari total agen:
    - 3% agen *Hit-and-Run*: Persistensi normal di M1–M12, anjlok serempak di M13–M14 setelah komisi cair.
    - 5% agen *Cherry-Picking*: Persistensi volume M13 dipertahankan di batas aman (~80%), namun APE anjlok >50% karena polis premi besar sengaja dimatikan.

- **Agent-Level Feature Engineering (4 Dimensi Multivariat)**:
  - *Lapse Shock Volume*: Selisih tingkat persistensi jumlah polis ($\Delta Persistency_{Vol} = M12 - M13$).
  - *Lapse Shock APE*: Selisih rasio retensi nilai premi ($\Delta Persistency_{APE} = APE_{M12} - APE_{M13}$).
  - *APE Disparity Ratio*: Rasio rata-rata nominal premi polis yang *lapse* terhadap premi polis yang tetap aktif.
  - *Payment Method Risk Concentration*: Persentase transaksi premi yang dibayar melalui metode manual/tunai terhadap total transaksi premi agen.

- **Two-Tier Detection Architecture**:
  - *Tier 1 (Hard Rule-Based Screening)*: Ambang batas deterministik (misal: $\Delta Persistency_{Vol} > 25\%$ atau persistensi M13 di bawah standar minimum OJK).
  - *Tier 2 (Unsupervised Isolation Forest)*: Model *Isolation Forest* dilatih pada 4 fitur agregat untuk menghasilkan *Anomaly Score* kontinu (0 hingga 1) dan mengklasifikasikan pencilan (*outliers*) yang lolos dari filter Tier 1.

- **Presentation & Dashboard Layer (Streamlit)**:
  - *Dual-Cohort Heatmap*: Matriks kohort berdampingan (*Volume Matrix* vs *APE Matrix*) dengan gradien warna retensi.
  - *Scatter Plot Anomali*: Visualisasi $\Delta Persistency_{Vol}$ vs $\Delta Persistency_{APE}$ yang memetakan posisi klaster agen normal, *hit-and-run*, dan *cherry-picking*.
  - *Agent Risk Watchlist*: Tabel interaktif dengan filter skor anomali, status investigasi, dan tombol ekspor data audit.

## Testing Decisions

- **Testing Principles**: Pengujian difokuskan pada integritas data aktual dan validitas kalkulasi analitik bisnis.
- **Data Generator Invariant Tests**:
  - Memastikan total polis unik di log transaksi tidak melebihi master polis.
  - Memastikan transisi status polis valid (status `Lapsed` tidak dapat kembali menjadi `Active` tanpa *reinstatement event*).
  - Memastikan persistensi M13 populasi normal berada pada rentang target 80%–85%.
- **Cohort Calculation Seam Tests**:
  - Memvalidasi formula persistensi volume: $\frac{\text{Polis Aktif } M_t}{\text{Total Polis Awal Kohort}}$.
  - Memvalidasi formula persistensi APE: $\frac{\text{APE Aktif } M_t}{\text{Total APE Awal Kohort}}$.
  - Memverifikasi kurva persistensi monoton menurun atau konstan ($M_{t+1} \le M_t$).
- **Detection Model Evaluation Tests**:
  - Menguji *Recall* deteksi terhadap label *ground truth* sintetis (target *Recall* $\ge 85\%$ pada top-20% *risk ranking*).
  - Menguji ketahanan model terhadap *missing values* atau agen dengan volume penjualan rendah.

## Out of Scope

- Integrasi database produksi *core-banking* / *core-insurance* secara *real-time*.
- Pelacakan identitas NIK lintas industri asuransi (fokus deteksi berada di level internal perusahaan).
- Pemodelan cadangan klaim aktuaria (*actuarial reserve modeling*).
- Otomasi pembekuan rekening komisi secara langsung ke sistem *payroll*.

## Further Notes

- Standar regulasi yang dijadikan acuan kepatuhan mengacu pada Surat Edaran Otoritas Jasa Keuangan (SEOJK) terkait PAYDI dan pedoman persistensi Asosiasi Asuransi Jiwa Indonesia (AAJI).
- File spesifikasi ini menjadi acuan utama untuk tahap implementasi modul `generate_data.py`, `detector.py`, dan `app.py`.

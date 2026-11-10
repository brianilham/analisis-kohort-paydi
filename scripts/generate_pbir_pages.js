const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

function genHex(bytes = 10) {
  return crypto.randomBytes(bytes).toString('hex');
}

const REPORT_DIR = path.resolve(__dirname, '../powerbi/MNC_Life_PAYDI.Report');
const DEFINITION_DIR = path.join(REPORT_DIR, 'definition');
const PAGES_DIR = path.join(DEFINITION_DIR, 'pages');

const SCHEMA_PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json";
const SCHEMA_PAGES_META = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json";
const SCHEMA_VISUAL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json";

function makeTextBox(title, subtitle, pos) {
  return {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, z: pos.z || 1000, tabOrder: pos.z || 1000 },
    visual: {
      visualType: "textbox",
      objects: {
        general: [{
          properties: {
            paragraphs: [{
              textRuns: [
                { value: title, textStyle: { fontWeight: "bold", fontSize: "15pt", color: "#192C4D" } },
                { value: "\n" + subtitle, textStyle: { fontSize: "9.5pt", color: "#5C768D" } }
              ]
            }]
          }
        }]
      }
    }
  };
}

function makeCard(measureTable, measureName, pos, title = null) {
  const vis = {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, z: pos.z || 2000, tabOrder: pos.z || 2000 },
    visual: {
      visualType: "cardVisual",
      query: {
        queryState: {
          Data: {
            projections: [{
              field: {
                Measure: {
                  Expression: { SourceRef: { Entity: measureTable } },
                  Property: measureName
                }
              },
              queryRef: `${measureTable}.${measureName}`,
              nativeQueryRef: measureName
            }]
          }
        }
      }
    }
  };
  if (title) {
    vis.visual.visualContainerObjects = {
      title: [{
        properties: {
          show: { expr: { Literal: { Value: "true" } } },
          text: { expr: { Literal: { Value: `'${title}'` } } }
        }
      }]
    };
  }
  return vis;
}

function makeSlicer(entity, column, displayName, pos) {
  return {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, height: Math.max(pos.height, 76), z: pos.z || 3000, tabOrder: pos.z || 3000 },
    visual: {
      visualType: "slicer",
      query: {
        queryState: {
          Values: {
            projections: [{
              field: {
                Column: {
                  Expression: { SourceRef: { Entity: entity } },
                  Property: column
                }
              },
              queryRef: `${entity}.${column}`,
              nativeQueryRef: column
            }]
          }
        }
      },
      objects: {
        data: [{ properties: { mode: { expr: { Literal: { Value: "'Dropdown'" } } } } }],
        header: [{
          properties: {
            show: { expr: { Literal: { Value: "true" } } },
            text: { expr: { Literal: { Value: `'${displayName}'` } } }
          }
        }]
      }
    }
  };
}

function makePivotTable(rows, cols, vals, pos, title) {
  const queryState = {
    Rows: {
      projections: rows.map(r => ({
        field: { Column: { Expression: { SourceRef: { Entity: r.entity } }, Property: r.property } },
        queryRef: `${r.entity}.${r.property}`,
        nativeQueryRef: r.property
      }))
    },
    Columns: {
      projections: cols.map(c => ({
        field: { Column: { Expression: { SourceRef: { Entity: c.entity } }, Property: c.property } },
        queryRef: `${c.entity}.${c.property}`,
        nativeQueryRef: c.property
      }))
    },
    Values: {
      projections: vals.map(v => ({
        field: { Measure: { Expression: { SourceRef: { Entity: v.entity } }, Property: v.property } },
        queryRef: `${v.entity}.${v.property}`,
        nativeQueryRef: v.property
      }))
    }
  };

  return {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, z: pos.z || 4000, tabOrder: pos.z || 4000 },
    visual: {
      visualType: "pivotTable",
      query: { queryState },
      visualContainerObjects: {
        title: [{
          properties: {
            show: { expr: { Literal: { Value: "true" } } },
            text: { expr: { Literal: { Value: `'${title}'` } } }
          }
        }]
      }
    }
  };
}

function makeTable(columns, pos, title) {
  const projections = columns.map(col => {
    if (col.isMeasure) {
      return {
        field: { Measure: { Expression: { SourceRef: { Entity: col.entity } }, Property: col.property } },
        queryRef: `${col.entity}.${col.property}`,
        nativeQueryRef: col.property
      };
    }
    return {
      field: { Column: { Expression: { SourceRef: { Entity: col.entity } }, Property: col.property } },
      queryRef: `${col.entity}.${col.property}`,
      nativeQueryRef: col.property
    };
  });

  return {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, z: pos.z || 5000, tabOrder: pos.z || 5000 },
    visual: {
      visualType: "tableEx",
      query: {
        queryState: {
          Values: { projections }
        }
      },
      visualContainerObjects: {
        title: [{
          properties: {
            show: { expr: { Literal: { Value: "true" } } },
            text: { expr: { Literal: { Value: `'${title}'` } } }
          }
        }]
      }
    }
  };
}

function makeLineChart(category, measures, pos, title) {
  return {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, z: pos.z || 6000, tabOrder: pos.z || 6000 },
    visual: {
      visualType: "lineChart",
      query: {
        queryState: {
          Category: {
            projections: [{
              field: { Column: { Expression: { SourceRef: { Entity: category.entity } }, Property: category.property } },
              queryRef: `${category.entity}.${category.property}`,
              nativeQueryRef: category.property
            }]
          },
          Y: {
            projections: measures.map(m => ({
              field: { Measure: { Expression: { SourceRef: { Entity: m.entity } }, Property: m.property } },
              queryRef: `${m.entity}.${m.property}`,
              nativeQueryRef: m.property
            }))
          }
        }
      },
      visualContainerObjects: {
        title: [{
          properties: {
            show: { expr: { Literal: { Value: "true" } } },
            text: { expr: { Literal: { Value: `'${title}'` } } }
          }
        }]
      }
    }
  };
}

function makeClusteredBarChart(category, measure, pos, title) {
  return {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, z: pos.z || 7000, tabOrder: pos.z || 7000 },
    visual: {
      visualType: "clusteredBarChart",
      query: {
        queryState: {
          Category: {
            projections: [{
              field: { Column: { Expression: { SourceRef: { Entity: category.entity } }, Property: category.property } },
              queryRef: `${category.entity}.${category.property}`,
              nativeQueryRef: category.property
            }]
          },
          Y: {
            projections: [{
              field: { Measure: { Expression: { SourceRef: { Entity: measure.entity } }, Property: measure.property } },
              queryRef: `${measure.entity}.${measure.property}`,
              nativeQueryRef: measure.property
            }]
          }
        }
      },
      visualContainerObjects: {
        title: [{
          properties: {
            show: { expr: { Literal: { Value: "true" } } },
            text: { expr: { Literal: { Value: `'${title}'` } } }
          }
        }]
      }
    }
  };
}

function makeDonutChart(category, measure, pos, title) {
  return {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, z: pos.z || 8000, tabOrder: pos.z || 8000 },
    visual: {
      visualType: "donutChart",
      query: {
        queryState: {
          Category: {
            projections: [{
              field: { Column: { Expression: { SourceRef: { Entity: category.entity } }, Property: category.property } },
              queryRef: `${category.entity}.${category.property}`,
              nativeQueryRef: category.property
            }]
          },
          Y: {
            projections: [{
              field: { Measure: { Expression: { SourceRef: { Entity: measure.entity } }, Property: measure.property } },
              queryRef: `${measure.entity}.${measure.property}`,
              nativeQueryRef: measure.property
            }]
          }
        }
      },
      visualContainerObjects: {
        title: [{
          properties: {
            show: { expr: { Literal: { Value: "true" } } },
            text: { expr: { Literal: { Value: `'${title}'` } } }
          }
        }]
      }
    }
  };
}

function makeScatterChart(pos, title) {
  return {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, z: pos.z || 9000, tabOrder: pos.z || 9000 },
    visual: {
      visualType: "scatterChart",
      query: {
        queryState: {
          Category: {
            projections: [{
              field: { Column: { Expression: { SourceRef: { Entity: "DimAgent" } }, Property: "agent_id" } },
              queryRef: "DimAgent.agent_id",
              nativeQueryRef: "agent_id"
            }]
          },
          Series: {
            projections: [{
              field: { Column: { Expression: { SourceRef: { Entity: "DimAgent" } }, Property: "risk_category" } },
              queryRef: "DimAgent.risk_category",
              nativeQueryRef: "risk_category"
            }]
          },
          X: {
            projections: [{
              field: { Aggregation: { Expression: { Column: { Expression: { SourceRef: { Entity: "DimAgent" } }, Property: "lapse_shock_vol" } }, Function: 1 } },
              queryRef: "Avg(DimAgent.lapse_shock_vol)",
              nativeQueryRef: "Avg of lapse_shock_vol"
            }]
          },
          Y: {
            projections: [{
              field: { Aggregation: { Expression: { Column: { Expression: { SourceRef: { Entity: "DimAgent" } }, Property: "lapse_shock_ape" } }, Function: 1 } },
              queryRef: "Avg(DimAgent.lapse_shock_ape)",
              nativeQueryRef: "Avg of lapse_shock_ape"
            }]
          },
          Size: {
            projections: [{
              field: { Aggregation: { Expression: { Column: { Expression: { SourceRef: { Entity: "DimAgent" } }, Property: "ape_disparity_ratio" } }, Function: 1 } },
              queryRef: "Avg(DimAgent.ape_disparity_ratio)",
              nativeQueryRef: "Avg of ape_disparity_ratio"
            }]
          }
        }
      },
      visualContainerObjects: {
        title: [{
          properties: {
            show: { expr: { Literal: { Value: "true" } } },
            text: { expr: { Literal: { Value: `'${title}'` } } }
          }
        }]
      }
    }
  };
}

// Ensure pages directory is clean
if (fs.existsSync(PAGES_DIR)) {
  fs.rmSync(PAGES_DIR, { recursive: true, force: true });
}
fs.mkdirSync(PAGES_DIR, { recursive: true });

const pages = [
  {
    id: "ReportSection01",
    displayName: "1. Matriks Kohort Persistensi",
    visuals: [
      makeTextBox(
        "MNC Life - Analisis Kohort Persistensi Polis PAYDI",
        "Monitoring Persistensi M1-M24 & Regulasi AAJI / SEOJK No. 5/SEOJK.05/2022",
        { x: 20, y: 15, width: 780, height: 50, z: 1000 }
      ),
      makeSlicer("DimAgent", "channel", "Distribusi Channel", { x: 820, y: 15, width: 210, height: 60, z: 2000 }),
      makeSlicer("DimAgent", "branch_office", "Kantor Cabang", { x: 1045, y: 15, width: 215, height: 60, z: 2100 }),
      makeCard("FactPolicyMonthlyStatus", "M13 Volume Persistency %", { x: 20, y: 80, width: 300, height: 85, z: 3000 }, "M13 Volume Persistency (AAJI >= 85%)"),
      makeCard("FactPolicyMonthlyStatus", "M13 APE Persistency %", { x: 335, y: 80, width: 300, height: 85, z: 3100 }, "M13 APE Persistency %"),
      makeCard("DimAgent", "Flagged Agents Count", { x: 650, y: 80, width: 300, height: 85, z: 3200 }, "Agen Terindikasi Anomali"),
      makeCard("FactPolicyMonthlyStatus", "Grace Period Policies (M11-M12)", { x: 965, y: 80, width: 295, height: 85, z: 3300 }, "Polis Grace Period M11-M12"),
      makePivotTable(
        [{ entity: "DimPolicy", property: "cohort_month" }],
        [{ entity: "FactPolicyMonthlyStatus", property: "Month Label" }],
        [{ entity: "FactPolicyMonthlyStatus", property: "Persistency Volume %" }],
        { x: 20, y: 180, width: 615, height: 250, z: 4000 },
        "Matriks Persistensi Polis Berdasarkan Volume (M1 - M24)"
      ),
      makePivotTable(
        [{ entity: "DimPolicy", property: "cohort_month" }],
        [{ entity: "FactPolicyMonthlyStatus", property: "Month Label" }],
        [{ entity: "FactPolicyMonthlyStatus", property: "Persistency APE %" }],
        { x: 650, y: 180, width: 610, height: 250, z: 4100 },
        "Matriks Persistensi Polis Berdasarkan Nilai Premi APE (M1 - M24)"
      ),
      makeLineChart(
        { entity: "FactPolicyMonthlyStatus", property: "Month Label" },
        [
          { entity: "FactPolicyMonthlyStatus", property: "Persistency Volume %" },
          { entity: "FactPolicyMonthlyStatus", property: "Persistency APE %" },
          { entity: "FactPolicyMonthlyStatus", property: "Leakage Gap %" }
        ],
        { x: 20, y: 445, width: 1240, height: 255, z: 5000 },
        "Tren Rata-Rata Persistensi Volume vs Premi APE & Deteksi Leakage Gap"
      )
    ]
  },
  {
    id: "ReportSection02",
    displayName: "2. Peta Sebaran Anomali Agen",
    visuals: [
      makeTextBox(
        "MNC Life - Deteksi Anomali & Churn Agen PAYDI",
        "Klasterisasi Dua Jalur: Tier 1 (Lapse Shock M12-M13) vs Tier 2 (Cherry-Picking & Disparitas Tiket)",
        { x: 20, y: 15, width: 780, height: 50, z: 1000 }
      ),
      makeSlicer("DimAgent", "risk_category", "Kategori Risiko", { x: 820, y: 15, width: 210, height: 60, z: 2000 }),
      makeSlicer("DimAgent", "channel", "Distribusi Channel", { x: 1045, y: 15, width: 215, height: 60, z: 2100 }),
      makeCard("DimAgent", "Hit and Run Agents Count", { x: 20, y: 80, width: 300, height: 85, z: 3000 }, "Agen Hit and Run (Tier 1)"),
      makeCard("DimAgent", "Cherry Picking Agents Count", { x: 335, y: 80, width: 300, height: 85, z: 3100 }, "Agen Cherry Picking (Tier 2)"),
      makeCard("DimAgent", "Flagged Agents Count", { x: 650, y: 80, width: 300, height: 85, z: 3200 }, "Total Agen Anomali"),
      makeCard("DimAgent", "Total Agents", { x: 965, y: 80, width: 295, height: 85, z: 3300 }, "Total Agen Terpantau"),
      makeScatterChart(
        { x: 20, y: 180, width: 680, height: 520, z: 4000 },
        "Distribusi Anomali Agen: Volume Shock vs APE Shock (Ukuran = Disparitas Premi)"
      ),
      makeTable(
        [
          { entity: "DimAgent", property: "agent_id" },
          { entity: "DimAgent", property: "agent_name" },
          { entity: "DimAgent", property: "channel" },
          { entity: "DimAgent", property: "risk_category" },
          { entity: "DimAgent", property: "anomaly_score" },
          { entity: "DimAgent", property: "primary_risk_drivers" }
        ],
        { x: 720, y: 180, width: 540, height: 520, z: 5000 },
        "Daftar Agen Terindikasi Anomali & Pelanggaran Regulasi"
      )
    ]
  },
  {
    id: "ReportSection03",
    displayName: "3. Early Warning Grace Period M11-M12",
    visuals: [
      makeTextBox(
        "MNC Life - Early Warning System (Grace Period M11-M12)",
        "Mitigasi Potensi Pembatalan Polis Menjelang Berakhirnya Komisi Akuisisi Tahun Pertama",
        { x: 20, y: 15, width: 780, height: 50, z: 1000 }
      ),
      makeSlicer("DimAgent", "branch_office", "Kantor Cabang", { x: 820, y: 15, width: 210, height: 60, z: 2000 }),
      makeSlicer("DimPolicy", "payment_method", "Metode Bayar", { x: 1045, y: 15, width: 215, height: 60, z: 2100 }),
      makeCard("FactPolicyMonthlyStatus", "Grace Period Policies (M11-M12)", { x: 20, y: 80, width: 300, height: 85, z: 3000 }, "Polis Kritis Grace Period M11-M12"),
      makeCard("FactPolicyMonthlyStatus", "Grace Period APE (Miliar IDR)", { x: 335, y: 80, width: 300, height: 85, z: 3100 }, "Total Premi Kritis Berisiko"),
      makeCard("FactPolicyMonthlyStatus", "Grace Period Cash Ratio %", { x: 650, y: 80, width: 300, height: 85, z: 3200 }, "Konsentrasi Metode Bayar Tunai"),
      makeCard("FactPolicyMonthlyStatus", "Grace Period Auto-Debit Ratio %", { x: 965, y: 80, width: 295, height: 85, z: 3300 }, "Metode Bayar Auto-Debit"),
      makeDonutChart(
        { entity: "DimPolicy", property: "payment_method" },
        { entity: "FactPolicyMonthlyStatus", property: "Grace Period APE (M11-M12)" },
        { x: 20, y: 180, width: 420, height: 250, z: 4000 },
        "Komposisi Metode Pembayaran Polis Kritis M11-M12"
      ),
      makeClusteredBarChart(
        { entity: "DimAgent", property: "branch_office" },
        { entity: "FactPolicyMonthlyStatus", property: "Grace Period APE (M11-M12)" },
        { x: 460, y: 180, width: 800, height: 250, z: 5000 },
        "Sebaran Premi Kritis (Grace Period M11-M12) per Kantor Cabang"
      ),
      makeTable(
        [
          { entity: "DimPolicy", property: "policy_id" },
          { entity: "DimPolicy", property: "agent_id" },
          { entity: "DimPolicy", property: "cohort_month" },
          { entity: "DimPolicy", property: "issue_date" },
          { entity: "DimPolicy", property: "ape" },
          { entity: "DimPolicy", property: "payment_method" }
        ],
        { x: 20, y: 445, width: 1240, height: 255, z: 6000 },
        "Daftar Polis Prioritas Penyelamatan (M11-M12) untuk Tim Customer Retention"
      )
    ]
  },
  {
    id: "ReportSection04",
    displayName: "4. Watchlist & Pemeriksaan Detail Agen",
    visuals: [
      makeTextBox(
        "MNC Life - Watchlist & Profil Risiko Agen",
        "Pemeriksaan Mendalam Perilaku Agen: Kurva Retensi 24 Bulan & Dekomposisi 4 Pilar Risiko",
        { x: 20, y: 15, width: 780, height: 50, z: 1000 }
      ),
      makeSlicer("DimAgent", "risk_category", "Kategori Risiko", { x: 820, y: 15, width: 210, height: 60, z: 2000 }),
      makeSlicer("DimAgent", "agent_name", "Pilih Nama Agen", { x: 1045, y: 15, width: 215, height: 60, z: 2100 }),
      makeTable(
        [
          { entity: "DimAgent", property: "risk_rank" },
          { entity: "DimAgent", property: "agent_id" },
          { entity: "DimAgent", property: "agent_name" },
          { entity: "DimAgent", property: "channel" },
          { entity: "DimAgent", property: "risk_category" },
          { entity: "DimAgent", property: "dominant_risk_pillar" },
          { entity: "DimAgent", property: "anomaly_score" },
          { entity: "DimAgent", property: "primary_risk_drivers" }
        ],
        { x: 20, y: 80, width: 1240, height: 250, z: 3000 },
        "Peringkat Risiko Agen (Top Risk Watchlist) & Pilar Dominan"
      ),
      makeLineChart(
        { entity: "FactPolicyMonthlyStatus", property: "Month Label" },
        [
          { entity: "FactPolicyMonthlyStatus", property: "Persistency Volume %" },
          { entity: "FactPolicyMonthlyStatus", property: "Persistency APE %" }
        ],
        { x: 20, y: 345, width: 615, height: 355, z: 4000 },
        "Kurva Retensi Polis 24 Bulan Agen Terpilih (Volume vs Premi APE)"
      ),
      makeClusteredBarChart(
        { entity: "FactAgentRiskPillars", property: "pillar_name" },
        { entity: "FactAgentRiskPillars", property: "Agent Pillar Score (0-100)" },
        { x: 650, y: 345, width: 610, height: 355, z: 5000 },
        "Dekomposisi Skor 4 Pilar Risiko Agen (Skala 0-100)"
      )
    ]
  },
  {
    id: "ReportSection05",
    displayName: "5. Validasi & Evaluasi Model",
    visuals: [
      makeTextBox(
        "MNC Life - Evaluasi Performa Model Deteksi Anomali",
        "Validasi Terhadap Ground Truth Etiket Agen & Audit Efektivitas Skoring Risiko",
        { x: 20, y: 15, width: 780, height: 50, z: 1000 }
      ),
      makeSlicer("DimAgent", "channel", "Distribusi Channel", { x: 820, y: 15, width: 210, height: 60, z: 2000 }),
      makeSlicer("DimAgent", "branch_office", "Kantor Cabang", { x: 1045, y: 15, width: 215, height: 60, z: 2100 }),
      makeCard("DimAgent", "Top-20% Recall %", { x: 20, y: 80, width: 300, height: 85, z: 3000 }, "Top-20% Recall (Target >= 85%)"),
      makeCard("DimAgent", "Overall Recall %", { x: 335, y: 80, width: 300, height: 85, z: 3100 }, "Overall Recall %"),
      makeCard("DimAgent", "Detection Precision %", { x: 650, y: 80, width: 300, height: 85, z: 3200 }, "Tingkat Presisi Deteksi"),
      makeCard("DimAgent", "Ground Truth Anomalies", { x: 965, y: 80, width: 295, height: 85, z: 3300 }, "Ground Truth Agen Anomali"),
      makePivotTable(
        [{ entity: "DimAgent", property: "true_label" }],
        [{ entity: "DimAgent", property: "risk_category" }],
        [{ entity: "DimAgent", property: "Total Agents" }],
        { x: 20, y: 180, width: 500, height: 260, z: 4000 },
        "Matriks Kebingungan (Ground Truth vs Prediksi Model)"
      ),
      makeClusteredBarChart(
        { entity: "DimAgent", property: "true_label" },
        { entity: "DimAgent", property: "Total Agents" },
        { x: 540, y: 180, width: 720, height: 260, z: 5000 },
        "Distribusi Jumlah Agen per Kategori Ground Truth"
      ),
      makeTable(
        [
          { entity: "DimAgent", property: "agent_id" },
          { entity: "DimAgent", property: "agent_name" },
          { entity: "DimAgent", property: "true_label" },
          { entity: "DimAgent", property: "risk_category" },
          { entity: "DimAgent", property: "anomaly_score" },
          { entity: "DimAgent", property: "risk_rank" },
          { entity: "DimAgent", property: "dominant_risk_pillar" }
        ],
        { x: 20, y: 455, width: 1240, height: 245, z: 6000 },
        "Daftar Lengkap Audit Agen Anomali (Ground Truth vs Model Score)"
      )
    ]
  }
];

// Write pages
for (const p of pages) {
  const pageDir = path.join(PAGES_DIR, p.id);
  const visualsDir = path.join(pageDir, 'visuals');
  fs.mkdirSync(visualsDir, { recursive: true });

  const pageJson = {
    $schema: SCHEMA_PAGE,
    name: p.id,
    displayName: p.displayName,
    displayOption: "FitToPage",
    height: 720,
    width: 1280
  };
  fs.writeFileSync(path.join(pageDir, 'page.json'), JSON.stringify(pageJson, null, 2));

  for (const v of p.visuals) {
    const vDir = path.join(visualsDir, v.name);
    fs.mkdirSync(vDir, { recursive: true });
    fs.writeFileSync(path.join(vDir, 'visual.json'), JSON.stringify(v, null, 2));
  }
}

// Write pages.json
const pagesMeta = {
  $schema: SCHEMA_PAGES_META,
  pageOrder: pages.map(p => p.id),
  activePageName: pages[0].id
};
fs.writeFileSync(path.join(PAGES_DIR, 'pages.json'), JSON.stringify(pagesMeta, null, 2));

console.log(`Generated ${pages.length} pages and ${pages.reduce((acc, p) => acc + p.visuals.length, 0)} visuals successfully.`);

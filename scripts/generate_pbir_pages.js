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

function lit(val) {
  return { expr: { Literal: { Value: val } } };
}

function solidColor(hex) {
  return { solid: { color: lit(`'${hex}'`) } };
}

function colExpr(entity, prop) {
  return { Column: { Expression: { SourceRef: { Entity: entity } }, Property: prop } };
}

function measExpr(entity, prop) {
  return { Measure: { Expression: { SourceRef: { Entity: entity } }, Property: prop } };
}

function avgExpr(entity, prop) {
  return { Aggregation: { Expression: colExpr(entity, prop), Function: 1 } };
}

function makeLogoImage(pos) {
  return {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, tabOrder: pos.z || 500 },
    visual: {
      visualType: "image",
      objects: {
        general: [{
          properties: {
            imageUrl: {
              expr: {
                ResourcePackageItem: {
                  PackageName: "RegisteredResources",
                  PackageType: 1,
                  ItemName: "mnc_life_logo_1001.png"
                }
              }
            }
          }
        }]
      },
      visualContainerObjects: {
        background: [{ properties: { show: lit("false") } }],
        border: [{ properties: { show: lit("false") } }],
        padding: [{ properties: { top: lit("2D"), bottom: lit("2D"), left: lit("2D"), right: lit("2D") } }]
      },
      drillFilterOtherVisuals: true
    }
  };
}

function makeHeaderBanner(title, subtitle, pos) {
  return {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, tabOrder: pos.z || 1000 },
    visual: {
      visualType: "textbox",
      objects: {
        general: [{
          properties: {
            paragraphs: [{
              textRuns: [
                { value: title, textStyle: { fontWeight: "bold", fontSize: "13pt", color: "#192C4D" } },
                { value: "\n" + subtitle, textStyle: { fontSize: "8.5pt", color: "#5C768D" } }
              ]
            }]
          }
        }]
      },
      visualContainerObjects: {
        background: [{ properties: { show: lit("false") } }],
        border: [{ properties: { show: lit("false") } }],
        padding: [{ properties: { top: lit("0D"), bottom: lit("0D"), left: lit("4D"), right: lit("4D") } }]
      }
    }
  };
}

function makeSlicer(entity, column, displayName, pos) {
  return {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, height: Math.max(pos.height, 76), tabOrder: pos.z || 2000 },
    visual: {
      visualType: "slicer",
      query: {
        queryState: {
          Values: {
            projections: [{
              field: colExpr(entity, column),
              queryRef: `${entity}.${column}`,
              nativeQueryRef: column
            }]
          }
        }
      },
      objects: {
        data: [{ properties: { mode: lit("'Dropdown'") } }],
        header: [{
          properties: {
            show: lit("true"),
            text: lit(`'${displayName}'`),
            fontColor: solidColor("#192C4D"),
            bold: lit("true")
          }
        }]
      },
      visualContainerObjects: {
        background: [{ properties: { show: lit("true"), color: solidColor("#FFFFFF") } }],
        border: [{ properties: { show: lit("true"), color: solidColor("#D9E5F2"), radius: lit("8D") } }],
        padding: [{ properties: { top: lit("6D"), bottom: lit("6D"), left: lit("8D"), right: lit("8D") } }]
      }
    }
  };
}

function makeCard(measureTable, measureName, labelText, accentHex, pos, tooltips = []) {
  const queryState = {
    Data: {
      projections: [{
        field: measExpr(measureTable, measureName),
        queryRef: `${measureTable}.${measureName}`,
        nativeQueryRef: measureName
      }]
    }
  };

  if (tooltips.length > 0) {
    queryState.Tooltips = {
      projections: tooltips.map(t => ({
        field: measExpr(t.entity, t.property),
        queryRef: `${t.entity}.${t.property}`,
        nativeQueryRef: t.property
      }))
    };
  }

  return {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, tabOrder: pos.z || 3000 },
    visual: {
      visualType: "cardVisual",
      query: { queryState },
      objects: {
        outline: [{ properties: { show: lit("false") }, selector: { id: "default" } }],
        accentBar: [{
          properties: {
            show: lit("true"),
            position: lit("'Left'"),
            width: lit("4D"),
            color: solidColor(accentHex)
          },
          selector: { id: "default" }
        }],
        value: [{
          properties: {
            fontSize: lit("20D"),
            fontColor: solidColor("#192C4D"),
            bold: lit("true")
          },
          selector: { id: "default" }
        }],
        label: [{
          properties: {
            show: lit("true"),
            text: lit(`'${labelText}'`),
            fontSize: lit("10D"),
            fontColor: solidColor("#4A5568")
          },
          selector: { id: "default" }
        }],
        padding: [{ properties: { paddingUniform: lit("8D") }, selector: { id: "default" } }],
        layout: [{ properties: { paddingUniform: lit("0D") }, selector: { id: "default" } }]
      },
      visualContainerObjects: {
        background: [{ properties: { show: lit("true"), color: solidColor("#FFFFFF") } }],
        border: [{ properties: { show: lit("true"), color: solidColor("#D9E5F2"), radius: lit("8D") } }],
        padding: [{ properties: { top: lit("6D"), bottom: lit("6D"), left: lit("6D"), right: lit("8D") }, selector: { id: "default" } }],
        spacing: [{ properties: { customizeSpacing: lit("true"), verticalSpacing: lit("2D") }, selector: { id: "default" } }],
        visualTooltip: [{ properties: { show: lit("true") } }]
      }
    }
  };
}

function makeLineChart(pos, title) {
  return {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, tabOrder: pos.z || 4000 },
    visual: {
      visualType: "lineChart",
      query: {
        queryState: {
          Category: {
            projections: [{
              field: colExpr("FactPolicyMonthlyStatus", "Month Label"),
              queryRef: "FactPolicyMonthlyStatus.Month Label",
              nativeQueryRef: "Month Label"
            }]
          },
          Y: {
            projections: [
              {
                field: measExpr("FactPolicyMonthlyStatus", "Persistency Volume %"),
                queryRef: "FactPolicyMonthlyStatus.Persistency Volume %",
                nativeQueryRef: "Persistency Volume %"
              },
              {
                field: measExpr("FactPolicyMonthlyStatus", "Persistency APE %"),
                queryRef: "FactPolicyMonthlyStatus.Persistency APE %",
                nativeQueryRef: "Persistency APE %"
              }
            ]
          },
          Tooltips: {
            projections: [
              {
                field: measExpr("FactPolicyMonthlyStatus", "Leakage Gap %"),
                queryRef: "FactPolicyMonthlyStatus.Leakage Gap %",
                nativeQueryRef: "Leakage Gap %"
              },
              {
                field: measExpr("FactPolicyMonthlyStatus", "Active Policies"),
                queryRef: "FactPolicyMonthlyStatus.Active Policies",
                nativeQueryRef: "Active Policies"
              }
            ]
          }
        }
      },
      objects: {
        dataPoint: [
          {
            properties: { fill: solidColor("#192C4D") },
            selector: { metadata: "FactPolicyMonthlyStatus.Persistency Volume %" }
          },
          {
            properties: { fill: solidColor("#D94B4B") },
            selector: { metadata: "FactPolicyMonthlyStatus.Persistency APE %" }
          }
        ],
        lineStyles: [
          {
            properties: {
              strokeWidth: lit("2.5D"),
              showMarker: lit("true"),
              markerSize: lit("3.5D")
            }
          }
        ],
        legend: [{
          properties: {
            show: lit("true"),
            position: lit("'Top'"),
            matchLineColor: lit("true"),
            fontSize: lit("9D")
          }
        }],
        valueAxis: [{
          properties: {
            showAxisTitle: lit("false"),
            fontSize: lit("9D"),
            gridlineStyle: lit("'dashed'"),
            gridlineColor: solidColor("#E2E8F0")
          }
        }],
        categoryAxis: [{
          properties: {
            showAxisTitle: lit("false"),
            fontSize: lit("8.5D")
          }
        }],
        y1AxisReferenceLine: [{
          properties: {
            show: lit("true"),
            value: lit("0.85D"),
            displayName: lit("'Target AAJI (85%)'"),
            style: lit("'dashed'"),
            width: lit("1.5D"),
            lineColor: solidColor("#C89B2C"),
            dataLabelShow: lit("true"),
            dataLabelText: lit("'Name'"),
            dataLabelColor: solidColor("#C89B2C"),
            dataLabelHorizontalPosition: lit("'right'"),
            dataLabelVerticalPosition: lit("'above'")
          },
          selector: { id: "1" }
        }]
      },
      visualContainerObjects: {
        title: [{
          properties: {
            show: lit("true"),
            text: lit(`'${title}'`),
            fontColor: solidColor("#192C4D"),
            bold: lit("true"),
            fontSize: lit("11D")
          }
        }],
        subTitle: [{
          properties: {
            show: lit("true"),
            text: lit("'Biru = retensi lembar polis; Merah = nilai premi APE. Klik agen di bawah untuk isolasi kurva.'"),
            fontColor: solidColor("#5C768D"),
            fontSize: lit("8.5D")
          }
        }],
        background: [{ properties: { show: lit("true"), color: solidColor("#FFFFFF") } }],
        border: [{ properties: { show: lit("true"), color: solidColor("#D9E5F2"), radius: lit("8D") } }],
        padding: [{ properties: { top: lit("8D"), bottom: lit("6D"), left: lit("10D"), right: lit("10D") }, selector: { id: "default" } }]
      }
    }
  };
}

function makeGraceBarChart(pos, title) {
  return {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, tabOrder: pos.z || 5000 },
    visual: {
      visualType: "clusteredBarChart",
      query: {
        queryState: {
          Category: {
            projections: [{
              field: colExpr("DimAgent", "branch_office"),
              queryRef: "DimAgent.branch_office",
              nativeQueryRef: "branch_office"
            }]
          },
          Series: {
            projections: [{
              field: colExpr("DimPolicy", "payment_method"),
              queryRef: "DimPolicy.payment_method",
              nativeQueryRef: "payment_method"
            }]
          },
          Y: {
            projections: [{
              field: measExpr("FactPolicyMonthlyStatus", "Grace Period APE (Miliar IDR)"),
              queryRef: "FactPolicyMonthlyStatus.Grace Period APE (Miliar IDR)",
              nativeQueryRef: "Grace Period APE (Miliar IDR)"
            }]
          },
          Tooltips: {
            projections: [{
              field: measExpr("FactPolicyMonthlyStatus", "Grace Period Policies (M11-M12)"),
              queryRef: "FactPolicyMonthlyStatus.Grace Period Policies (M11-M12)",
              nativeQueryRef: "Grace Period Policies (M11-M12)"
            }]
          }
        },
        sortDefinition: {
          sort: [{
            field: measExpr("FactPolicyMonthlyStatus", "Grace Period APE (Miliar IDR)"),
            direction: "Descending"
          }],
          isDefaultSort: false
        }
      },
      objects: {
        dataPoint: [
          {
            properties: { fill: solidColor("#D94B4B") },
            selector: {
              data: [{
                scopeId: {
                  Comparison: {
                    ComparisonKind: 0,
                    Left: colExpr("DimPolicy", "payment_method"),
                    Right: { Literal: { Value: "'Manual/Cash'" } }
                  }
                }
              }]
            }
          },
          {
            properties: { fill: solidColor("#192C4D") },
            selector: {
              data: [{
                scopeId: {
                  Comparison: {
                    ComparisonKind: 0,
                    Left: colExpr("DimPolicy", "payment_method"),
                    Right: { Literal: { Value: "'Auto-Debit'" } }
                  }
                }
              }]
            }
          }
        ],
        labels: [{
          properties: {
            show: lit("true"),
            fontSize: lit("8.5D")
          }
        }],
        legend: [{
          properties: {
            show: lit("true"),
            position: lit("'Top'"),
            fontSize: lit("9D")
          }
        }],
        categoryAxis: [{ properties: { showAxisTitle: lit("false"), fontSize: lit("9D"), maxMarginFactor: lit("35L") } }],
        valueAxis: [{ properties: { showAxisTitle: lit("false"), fontSize: lit("8.5D"), gridlineStyle: lit("'dashed'") } }]
      },
      visualContainerObjects: {
        title: [{
          properties: {
            show: lit("true"),
            text: lit(`'${title}'`),
            fontColor: solidColor("#192C4D"),
            bold: lit("true"),
            fontSize: lit("11D")
          }
        }],
        subTitle: [{
          properties: {
            show: lit("true"),
            text: lit("'Total APE polis menunggak M11–M12 (Miliar Rp). Merah = Manual/Cash (risiko tinggi).'"),
            fontColor: solidColor("#5C768D"),
            fontSize: lit("8.5D")
          }
        }],
        background: [{ properties: { show: lit("true"), color: solidColor("#FFFFFF") } }],
        border: [{ properties: { show: lit("true"), color: solidColor("#D9E5F2"), radius: lit("8D") } }],
        padding: [{ properties: { top: lit("8D"), bottom: lit("6D"), left: lit("10D"), right: lit("10D") }, selector: { id: "default" } }]
      }
    }
  };
}

function makeScatterChart(pos, title) {
  return {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, tabOrder: pos.z || 6000 },
    visual: {
      visualType: "scatterChart",
      query: {
        queryState: {
          Category: {
            projections: [{
              field: colExpr("DimAgent", "agent_id"),
              queryRef: "DimAgent.agent_id",
              nativeQueryRef: "agent_id"
            }]
          },
          Series: {
            projections: [{
              field: colExpr("DimAgent", "risk_category"),
              queryRef: "DimAgent.risk_category",
              nativeQueryRef: "risk_category"
            }]
          },
          X: {
            projections: [{
              field: avgExpr("DimAgent", "lapse_shock_vol"),
              queryRef: "Avg(DimAgent.lapse_shock_vol)",
              nativeQueryRef: "Volume Shock M12-M13 (%)"
            }]
          },
          Y: {
            projections: [{
              field: avgExpr("DimAgent", "lapse_shock_ape"),
              queryRef: "Avg(DimAgent.lapse_shock_ape)",
              nativeQueryRef: "APE Shock M12-M13 (%)"
            }]
          },
          Size: {
            projections: [{
              field: avgExpr("DimAgent", "ape_disparity_ratio"),
              queryRef: "Avg(DimAgent.ape_disparity_ratio)",
              nativeQueryRef: "Disparitas Premi (x)"
            }]
          },
          Tooltips: {
            projections: [{
              field: avgExpr("DimAgent", "anomaly_score"),
              queryRef: "Avg(DimAgent.anomaly_score)",
              nativeQueryRef: "Skor Risiko Anomali"
            }]
          }
        }
      },
      objects: {
        dataPoint: [
          {
            properties: { fill: solidColor("#D94B4B") },
            selector: {
              data: [{
                scopeId: {
                  Comparison: {
                    ComparisonKind: 0,
                    Left: colExpr("DimAgent", "risk_category"),
                    Right: { Literal: { Value: "'Hit and Run'" } }
                  }
                }
              }]
            }
          },
          {
            properties: { fill: solidColor("#C89B2C") },
            selector: {
              data: [{
                scopeId: {
                  Comparison: {
                    ComparisonKind: 0,
                    Left: colExpr("DimAgent", "risk_category"),
                    Right: { Literal: { Value: "'Cherry Picking'" } }
                  }
                }
              }]
            }
          },
          {
            properties: { fill: solidColor("#1E6B52") },
            selector: {
              data: [{
                scopeId: {
                  Comparison: {
                    ComparisonKind: 0,
                    Left: colExpr("DimAgent", "risk_category"),
                    Right: { Literal: { Value: "'Normal'" } }
                  }
                }
              }]
            }
          }
        ],
        legend: [{
          properties: {
            show: lit("true"),
            position: lit("'Top'"),
            fontSize: lit("9D")
          }
        }],
        categoryAxis: [{
          properties: {
            showAxisTitle: lit("true"),
            titleText: lit("'Lapse Shock Volume M12->M13 (%)'"),
            fontSize: lit("8.5D"),
            titleFontSize: lit("8.5D")
          }
        }],
        valueAxis: [{
          properties: {
            showAxisTitle: lit("true"),
            titleText: lit("'Lapse Shock APE (%)'"),
            fontSize: lit("8.5D"),
            titleFontSize: lit("8.5D"),
            gridlineStyle: lit("'dashed'")
          }
        }]
      },
      visualContainerObjects: {
        title: [{
          properties: {
            show: lit("true"),
            text: lit(`'${title}'`),
            fontColor: solidColor("#192C4D"),
            bold: lit("true"),
            fontSize: lit("11D")
          }
        }],
        subTitle: [{
          properties: {
            show: lit("true"),
            text: lit("'Merah = Hit & Run; Emas = Cherry Picking; Ukuran = Disparitas Premi.'"),
            fontColor: solidColor("#5C768D"),
            fontSize: lit("8.5D")
          }
        }],
        background: [{ properties: { show: lit("true"), color: solidColor("#FFFFFF") } }],
        border: [{ properties: { show: lit("true"), color: solidColor("#D9E5F2"), radius: lit("8D") } }],
        padding: [{ properties: { top: lit("8D"), bottom: lit("6D"), left: lit("10D"), right: lit("10D") }, selector: { id: "default" } }]
      }
    }
  };
}

function makeWatchlistTable(pos, title) {
  const columns = [
    { entity: "DimAgent", property: "risk_rank", alias: "Rank" },
    { entity: "DimAgent", property: "agent_name", alias: "Nama Agen" },
    { entity: "DimAgent", property: "risk_category", alias: "Klaster" },
    { entity: "DimAgent", property: "anomaly_score", alias: "Skor" },
    { entity: "DimAgent", property: "primary_risk_drivers", alias: "Pemicu Risiko Utama (Audit)" }
  ];

  return {
    $schema: SCHEMA_VISUAL,
    name: genHex(),
    position: { ...pos, tabOrder: pos.z || 7000 },
    visual: {
      visualType: "tableEx",
      query: {
        queryState: {
          Values: {
            projections: columns.map(c => ({
              field: colExpr(c.entity, c.property),
              queryRef: `${c.entity}.${c.property}`,
              nativeQueryRef: c.alias,
              displayName: c.alias
            }))
          }
        },
        sortDefinition: {
          sort: [{
            field: colExpr("DimAgent", "risk_rank"),
            direction: "Ascending"
          }],
          isDefaultSort: false
        }
      },
      objects: {
        columnHeaders: [{
          properties: {
            fontColor: solidColor("#FFFFFF"),
            backColor: solidColor("#192C4D"),
            columnAdjustment: lit("'growToFit'"),
            autoSizeColumnWidth: lit("true"),
            fontSize: lit("9D")
          }
        }],
        values: [{
          properties: {
            fontColorPrimary: solidColor("#1A202C"),
            fontColorSecondary: solidColor("#1A202C"),
            backColorPrimary: solidColor("#FFFFFF"),
            backColorSecondary: solidColor("#F5F8FC"),
            fontSize: lit("8.5D")
          }
        }]
      },
      visualContainerObjects: {
        stylePreset: [{ properties: { name: lit("'None'") } }],
        title: [{
          properties: {
            show: lit("true"),
            text: lit(`'${title}'`),
            fontColor: solidColor("#192C4D"),
            bold: lit("true"),
            fontSize: lit("11D")
          }
        }],
        subTitle: [{
          properties: {
            show: lit("true"),
            text: lit("'Urutan #1 paling berisiko. Klik baris agen untuk mengisolasi kurva retensi 24 bulannya.'"),
            fontColor: solidColor("#5C768D"),
            fontSize: lit("8.5D")
          }
        }],
        background: [{ properties: { show: lit("true"), color: solidColor("#FFFFFF") } }],
        border: [{ properties: { show: lit("true"), color: solidColor("#D9E5F2"), radius: lit("8D") } }],
        padding: [{ properties: { top: lit("8D"), bottom: lit("6D"), left: lit("10D"), right: lit("10D") }, selector: { id: "default" } }]
      }
    }
  };
}

// Clean existing pages directory and rebuild strictly 1 Executive Page (1280 x 720)
if (fs.existsSync(PAGES_DIR)) {
  fs.rmSync(PAGES_DIR, { recursive: true, force: true });
}
fs.mkdirSync(PAGES_DIR, { recursive: true });

const pageId = "ReportSection01";
const pageDir = path.join(PAGES_DIR, pageId);
const visualsDir = path.join(pageDir, 'visuals');
fs.mkdirSync(visualsDir, { recursive: true });

const pageJson = {
  $schema: SCHEMA_PAGE,
  name: pageId,
  displayName: "Executive Helicopter View",
  displayOption: "FitToPage",
  height: 720,
  width: 1280,
  objects: {
    background: [{
      properties: {
        color: solidColor("#F5F8FC"),
        transparency: lit("0D")
      }
    }],
    outspace: [{
      properties: {
        color: solidColor("#EBF1F7"),
        transparency: lit("0D")
      }
    }]
  }
};
fs.writeFileSync(path.join(pageDir, 'page.json'), JSON.stringify(pageJson, null, 2));

const visuals = [
  // Header strip (y: 8 .. 84)
  makeLogoImage({ x: 16, y: 12, width: 108, height: 50, z: 500 }),
  makeHeaderBanner(
    "MNC Life — Executive Helicopter View: PAYDI & Risiko Agen",
    "AAJI / SEOJK No. 5/SEOJK.05/2022 • Kohort 2022–2023 (12.000 Polis, 200 Agen)",
    { x: 132, y: 12, width: 575, height: 56, z: 1000 }
  ),
  makeSlicer("DimAgent", "channel", "Channel", { x: 718, y: 8, width: 168, height: 76, z: 2000 }),
  makeSlicer("DimAgent", "branch_office", "Cabang", { x: 896, y: 8, width: 178, height: 76, z: 2100 }),
  makeSlicer("DimAgent", "risk_category", "Kategori Risiko", { x: 1084, y: 8, width: 180, height: 76, z: 2200 }),

  // Tier 1: 4 North Star KPI Cards (y: 92, h: 84)
  makeCard(
    "FactPolicyMonthlyStatus",
    "M13 Volume Persistency %",
    "Persistensi Vol M13 (AAJI >= 85%)",
    "#192C4D",
    { x: 16, y: 92, width: 301, height: 84, z: 3000 },
    [{ entity: "FactPolicyMonthlyStatus", property: "M13 Volume vs AAJI Benchmark" }]
  ),
  makeCard(
    "FactPolicyMonthlyStatus",
    "M13 APE Persistency %",
    "Persistensi Premi APE M13",
    "#D94B4B",
    { x: 331, y: 92, width: 301, height: 84, z: 3100 },
    [
      { entity: "FactPolicyMonthlyStatus", property: "M13 Leakage Gap %" },
      { entity: "FactPolicyMonthlyStatus", property: "M13 Leaked APE (Miliar IDR)" }
    ]
  ),
  makeCard(
    "FactPolicyMonthlyStatus",
    "Grace Period APE (Miliar IDR)",
    "Premi Kritis Grace Period M11–M12",
    "#C89B2C",
    { x: 646, y: 92, width: 301, height: 84, z: 3200 },
    [
      { entity: "FactPolicyMonthlyStatus", property: "Grace Period Policies (M11-M12)" },
      { entity: "FactPolicyMonthlyStatus", property: "Grace Period Cash Ratio %" }
    ]
  ),
  makeCard(
    "DimAgent",
    "Flagged Agents Count",
    "Agen Anomali (Tier 1 & Tier 2)",
    "#8B263E",
    { x: 961, y: 92, width: 303, height: 84, z: 3300 },
    [
      { entity: "DimAgent", property: "Hit and Run Agents Count" },
      { entity: "DimAgent", property: "Cherry Picking Agents Count" },
      { entity: "DimAgent", property: "Top-20% Recall %" }
    ]
  ),

  // Tier 2: Macro Portfolio Health & Early Warning (y: 186, h: 254)
  makeLineChart(
    { x: 16, y: 186, width: 650, height: 254, z: 4000 },
    "Kurva Retensi Kohort M1–M24: Volume vs Premi APE"
  ),
  makeGraceBarChart(
    { x: 678, y: 186, width: 586, height: 254, z: 5000 },
    "Early Warning Grace Period M11–M12 per Cabang & Bayar"
  ),

  // Tier 3: Micro Anomaly Detection & Executive Watchlist (y: 450, h: 256)
  makeScatterChart(
    { x: 16, y: 450, width: 520, height: 256, z: 6000 },
    "Peta Klaster Anomali Agen (Vol vs APE Shock)"
  ),
  makeWatchlistTable(
    { x: 548, y: 450, width: 716, height: 256, z: 7000 },
    "Executive Audit Watchlist — Prioritas Agen & Pemicu Risiko"
  )
];

for (const v of visuals) {
  const vDir = path.join(visualsDir, v.name);
  fs.mkdirSync(vDir, { recursive: true });
  fs.writeFileSync(path.join(vDir, 'visual.json'), JSON.stringify(v, null, 2));
}

const pagesMeta = {
  $schema: SCHEMA_PAGES_META,
  pageOrder: [pageId],
  activePageName: pageId
};
fs.writeFileSync(path.join(PAGES_DIR, 'pages.json'), JSON.stringify(pagesMeta, null, 2));

console.log(`Generated 1280x720 Executive Helicopter View page with ${visuals.length} visuals successfully.`);

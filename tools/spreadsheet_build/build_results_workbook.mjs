import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = process.env.EPUCK_PROJECT_ROOT
  ? path.resolve(process.env.EPUCK_PROJECT_ROOT)
  : path.resolve(scriptDirectory, "..", "..");
const csvPath = path.join(projectRoot, "results", "formal", "enriched_summary.csv");
const outputPath = path.join(projectRoot, "results", "Research_Results.xlsx");
const previewPath = path.join(projectRoot, "evidence", "formal_results_dashboard.png");
const csvText = await fs.readFile(csvPath, "utf8");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "Raw Results" });
const raw = workbook.worksheets.getItem("Raw Results");
raw.showGridLines = false;
raw.freezePanes.freezeRows(1);
raw.freezePanes.freezeColumns(2);
raw.getRange("A1:AH211").format.font = { name: "Aptos", size: 9, color: "#172033" };
raw.getRange("A1:AH1").format = {
  fill: "#17324D",
  font: { name: "Aptos Display", size: 10, bold: true, color: "#FFFFFF" },
  wrapText: true,
  rowHeight: 34,
};
raw.getRange("A1:AH211").format.borders = {
  insideHorizontal: { style: "thin", color: "#E7ECF2" },
};
raw.getRange("C2:D211").format.numberFormat = "0";
raw.getRange("J2:K211").format.numberFormat = "0.000";
raw.getRange("L2:N211").format.numberFormat = "0.000";
raw.getRange("O2:S211").format.numberFormat = "0.000000";
raw.getRange("T2:T211").format.numberFormat = "0";
raw.getRange("W2:AC211").format.numberFormat = "0";
raw.getRange("AD2:AG211").format.numberFormat = "0.000";
raw.getRange("A:AH").format.autofitColumns();
raw.getRange("A:A").format.columnWidth = 34;
raw.getRange("B:B").format.columnWidth = 28;
raw.getRange("F:F").format.columnWidth = 20;
raw.getRange("U:U").format.columnWidth = 20;

const scenarios = [
  ["lane_straight_nominal", "Lane"],
  ["lane_straight_dim", "Lane"],
  ["lane_straight_bright", "Lane"],
  ["lane_curve_nominal", "Lane"],
  ["lane_curve_dim", "Lane"],
  ["lane_curve_bright", "Lane"],
  ["static_left", "Stationary"],
  ["static_center", "Stationary"],
  ["static_right", "Stationary"],
  ["moving_010", "Moving"],
  ["moving_015", "Moving"],
  ["moving_020", "Moving"],
  ["multi_static_sequential", "Multi"],
  ["multi_moving_crossings", "Multi"],
  ["multi_mixed_obstacles", "Multi"],
];
const summary = workbook.worksheets.add("Scenario Summary");
summary.showGridLines = false;
summary.freezePanes.freezeRows(4);
summary.getRange("A1:N1").merge();
summary.getRange("A1").values = [["Formal Scenario Summary"]];
summary.getRange("A1:N1").format = {
  fill: "#17324D",
  font: { name: "Aptos Display", size: 18, bold: true, color: "#FFFFFF" },
  rowHeight: 32,
};
summary.getRange("A2:N2").merge();
summary.getRange("A2").values = [[
  "Configuration 82999888659be0c7 | 15 scenarios x 10 repetitions | Webots R2025a",
]];
summary.getRange("A2:N2").format = {
  fill: "#DCEAF4",
  font: { name: "Aptos", size: 10, italic: true, color: "#17324D" },
  rowHeight: 23,
};
summary.getRange("A4:N4").values = [[
  "Scenario", "Category", "Runs", "Completed", "Completion Rate",
  "Mean Lane Error (m)", "Max Lane Error (m)", "Collisions",
  "True Positives", "Minimum Clearance (m)", "Stop/Wait Runs",
  "Avoid Runs", "Rejoin Runs", "Mean Duration (s)",
]];
summary.getRange("A5:B19").values = scenarios;
for (let row = 5; row <= 19; row += 1) {
  summary.getRange(`C${row}`).formulas = [[
    `=COUNTIFS('Raw Results'!$B$2:$B$211,A${row},'Raw Results'!$E$2:$E$211,"vision")`,
  ]];
  summary.getRange(`D${row}`).formulas = [[
    `=SUMIFS('Raw Results'!$L$2:$L$211,'Raw Results'!$B$2:$B$211,A${row},'Raw Results'!$E$2:$E$211,"vision")`,
  ]];
  summary.getRange(`E${row}`).formulas = [[`=IF(C${row}=0,0,D${row}/C${row})`]];
  summary.getRange(`F${row}`).formulas = [[
    `=AVERAGEIFS('Raw Results'!$O$2:$O$211,'Raw Results'!$B$2:$B$211,A${row},'Raw Results'!$E$2:$E$211,"vision")`,
  ]];
  summary.getRange(`G${row}`).formulas = [[
    `=MAXIFS('Raw Results'!$P$2:$P$211,'Raw Results'!$B$2:$B$211,A${row},'Raw Results'!$E$2:$E$211,"vision")`,
  ]];
  summary.getRange(`H${row}`).formulas = [[
    `=SUMIFS('Raw Results'!$Q$2:$Q$211,'Raw Results'!$B$2:$B$211,A${row},'Raw Results'!$E$2:$E$211,"vision")`,
  ]];
  summary.getRange(`I${row}`).formulas = [[
    `=SUMIFS('Raw Results'!$Y$2:$Y$211,'Raw Results'!$B$2:$B$211,A${row},'Raw Results'!$E$2:$E$211,"vision")`,
  ]];
  summary.getRange(`J${row}`).formulas = [[
    `=IF(B${row}="Lane","",MIN(MINIFS('Raw Results'!$R$2:$R$211,'Raw Results'!$B$2:$B$211,A${row},'Raw Results'!$E$2:$E$211,"vision"),MINIFS('Raw Results'!$S$2:$S$211,'Raw Results'!$B$2:$B$211,A${row},'Raw Results'!$E$2:$E$211,"vision")))`,
  ]];
  summary.getRange(`K${row}`).formulas = [[
    `=SUMIFS('Raw Results'!$AA$2:$AA$211,'Raw Results'!$B$2:$B$211,A${row},'Raw Results'!$E$2:$E$211,"vision")`,
  ]];
  summary.getRange(`L${row}`).formulas = [[
    `=SUMIFS('Raw Results'!$AB$2:$AB$211,'Raw Results'!$B$2:$B$211,A${row},'Raw Results'!$E$2:$E$211,"vision")`,
  ]];
  summary.getRange(`M${row}`).formulas = [[
    `=SUMIFS('Raw Results'!$AC$2:$AC$211,'Raw Results'!$B$2:$B$211,A${row},'Raw Results'!$E$2:$E$211,"vision")`,
  ]];
  summary.getRange(`N${row}`).formulas = [[
    `=AVERAGEIFS('Raw Results'!$K$2:$K$211,'Raw Results'!$B$2:$B$211,A${row},'Raw Results'!$E$2:$E$211,"vision")`,
  ]];
}
summary.getRange("A4:N4").format = {
  fill: "#285E80",
  font: { name: "Aptos", size: 9, bold: true, color: "#FFFFFF" },
  wrapText: true,
  rowHeight: 40,
};
summary.getRange("A5:N19").format = {
  font: { name: "Aptos", size: 9, color: "#172033" },
  borders: { insideHorizontal: { style: "thin", color: "#DDE5EC" } },
};
summary.getRange("E5:E19").format.numberFormat = "0.0%";
summary.getRange("F5:G19").format.numberFormat = "0.000";
summary.getRange("J5:J19").format.numberFormat = "0.000";
summary.getRange("N5:N19").format.numberFormat = "0.0";
summary.getRange("A:N").format.autofitColumns();
summary.getRange("A:A").format.columnWidth = 27;
summary.getRange("B:B").format.columnWidth = 13;
summary.getRange("E:G").format.columnWidth = 17;
summary.getRange("I:M").format.columnWidth = 15;
summary.getRange("E5:E19").conditionalFormats.add("cellIs", {
  operator: "lessThan",
  formula: 0.9,
  format: { fill: "#FDE2E2", font: { color: "#9B1C1C", bold: true } },
});
summary.getRange("F5:F19").conditionalFormats.add("cellIs", {
  operator: "greaterThan",
  formula: 0.05,
  format: { fill: "#FFF0CC", font: { color: "#7A4B00", bold: true } },
});
summary.getRange("H5:H19").conditionalFormats.add("cellIs", {
  operator: "greaterThan",
  formula: 0,
  format: { fill: "#FDE2E2", font: { color: "#9B1C1C", bold: true } },
});

const baseline = workbook.worksheets.add("Baseline Comparison");
baseline.showGridLines = false;
baseline.getRange("A1:H1").merge();
baseline.getRange("A1").values = [["Vision Controller vs Ground-Sensor Baseline"]];
baseline.getRange("A1:H1").format = {
  fill: "#17324D",
  font: { name: "Aptos Display", size: 18, bold: true, color: "#FFFFFF" },
  rowHeight: 32,
};
baseline.getRange("A3:H3").values = [[
  "Lane Scenario", "Vision Runs", "Vision Completion", "Vision Mean Error (m)",
  "Baseline Runs", "Baseline Completion", "Baseline Mean Error (m)", "Difference (pp)",
]];
baseline.getRange("A4:A9").values = scenarios.slice(0, 6).map((item) => [item[0]]);
for (let row = 4; row <= 9; row += 1) {
  baseline.getRange(`B${row}`).formulas = [[
    `=COUNTIFS('Raw Results'!$B$2:$B$211,A${row},'Raw Results'!$E$2:$E$211,"vision")`,
  ]];
  baseline.getRange(`C${row}`).formulas = [[
    `=SUMIFS('Raw Results'!$L$2:$L$211,'Raw Results'!$B$2:$B$211,A${row},'Raw Results'!$E$2:$E$211,"vision")/B${row}`,
  ]];
  baseline.getRange(`D${row}`).formulas = [[
    `=AVERAGEIFS('Raw Results'!$O$2:$O$211,'Raw Results'!$B$2:$B$211,A${row},'Raw Results'!$E$2:$E$211,"vision")`,
  ]];
  baseline.getRange(`E${row}`).formulas = [[
    `=COUNTIFS('Raw Results'!$B$2:$B$211,A${row}&"_baseline",'Raw Results'!$E$2:$E$211,"baseline")`,
  ]];
  baseline.getRange(`F${row}`).formulas = [[
    `=SUMIFS('Raw Results'!$L$2:$L$211,'Raw Results'!$B$2:$B$211,A${row}&"_baseline",'Raw Results'!$E$2:$E$211,"baseline")/E${row}`,
  ]];
  baseline.getRange(`G${row}`).formulas = [[
    `=AVERAGEIFS('Raw Results'!$O$2:$O$211,'Raw Results'!$B$2:$B$211,A${row}&"_baseline",'Raw Results'!$E$2:$E$211,"baseline")`,
  ]];
  baseline.getRange(`H${row}`).formulas = [[`=(C${row}-F${row})*100`]];
}
baseline.getRange("A3:H3").format = {
  fill: "#285E80",
  font: { bold: true, color: "#FFFFFF" },
  wrapText: true,
  rowHeight: 38,
};
baseline.getRange("A4:H9").format = {
  borders: { insideHorizontal: { style: "thin", color: "#DDE5EC" } },
};
baseline.getRange("B4:B9").format.numberFormat = "0";
baseline.getRange("E4:E9").format.numberFormat = "0";
baseline.getRange("C4:C9").format.numberFormat = "0.0%";
baseline.getRange("F4:F9").format.numberFormat = "0.0%";
baseline.getRange("D4:D9").format.numberFormat = "0.000";
baseline.getRange("G4:G9").format.numberFormat = "0.000";
baseline.getRange("H4:H9").format.numberFormat = "0.0";
baseline.getRange("A:H").format.autofitColumns();
baseline.getRange("A:A").format.columnWidth = 28;
baseline.getRange("C:H").format.columnWidth = 20;
const baselineChart = baseline.charts.add("bar", {
  chartType: "bar",
  title: "Vision vs Baseline Completion",
  hasLegend: true,
});
baselineChart.title = "Vision vs Baseline Completion";
const baselineVisionSeries = baselineChart.series.add("Vision");
baselineVisionSeries.categoryFormula = "'Baseline Comparison'!$A$4:$A$9";
baselineVisionSeries.formula = "'Baseline Comparison'!$C$4:$C$9";
baselineVisionSeries.fill = "#1499C6";
const baselineGroundSeries = baselineChart.series.add("Ground-sensor baseline");
baselineGroundSeries.categoryFormula = "'Baseline Comparison'!$A$4:$A$9";
baselineGroundSeries.formula = "'Baseline Comparison'!$F$4:$F$9";
baselineGroundSeries.fill = "#E76F2E";
baselineChart.hasLegend = true;
baselineChart.xAxis = { axisType: "textAxis" };
baselineChart.yAxis = { numberFormatCode: "0%", min: 0, max: 1 };
baselineChart.setPosition("A12", "H29");

const dashboard = workbook.worksheets.add("Dashboard");
dashboard.showGridLines = false;
dashboard.getRange("A1:L1").merge();
dashboard.getRange("A1").values = [["Vision-Based E-puck Formal Results"]];
dashboard.getRange("A1:L1").format = {
  fill: "#17324D",
  font: { name: "Aptos Display", size: 20, bold: true, color: "#FFFFFF" },
  rowHeight: 36,
};
dashboard.getRange("A2:L2").merge();
dashboard.getRange("A2").values = [[
  "Webots R2025a | Frozen configuration 82999888659be0c7 | 210 formal trials",
]];
dashboard.getRange("A2:L2").format = {
  fill: "#DCEAF4",
  font: { italic: true, color: "#17324D" },
  rowHeight: 22,
};
dashboard.getRange("A4:B10").values = [
  ["Metric", "Result"],
  ["Vision trials", null],
  ["Vision completion", null],
  ["Baseline completion", null],
  ["Overall mean lane error (m)", null],
  ["Vision collisions", null],
  ["Minimum moving clearance (m)", null],
];
dashboard.getRange("B5").formulas = [["=COUNTIF('Raw Results'!$E$2:$E$211,\"vision\")"]];
dashboard.getRange("B6").formulas = [["=SUMIFS('Raw Results'!$L$2:$L$211,'Raw Results'!$E$2:$E$211,\"vision\")/B5"]];
dashboard.getRange("B7").formulas = [["=SUMIFS('Raw Results'!$L$2:$L$211,'Raw Results'!$E$2:$E$211,\"baseline\")/COUNTIF('Raw Results'!$E$2:$E$211,\"baseline\")"]];
dashboard.getRange("B8").formulas = [["=AVERAGEIFS('Raw Results'!$O$2:$O$211,'Raw Results'!$E$2:$E$211,\"vision\")"]];
dashboard.getRange("B9").formulas = [["=SUMIFS('Raw Results'!$Q$2:$Q$211,'Raw Results'!$E$2:$E$211,\"vision\")"]];
dashboard.getRange("B10").formulas = [["=MINIFS('Raw Results'!$S$2:$S$211,'Raw Results'!$E$2:$E$211,\"vision\",'Raw Results'!$X$2:$X$211,\">0\")"]];
dashboard.getRange("D4:E10").values = [
  ["Criterion", "Status"],
  ["Nominal completion >= 90%", null],
  ["Overall completion >= 80%", null],
  ["Obstacle detection >= 90%", null],
  ["Accepted trials collision-free", null],
  ["Mean lane error <= 0.05 m", null],
  ["Moving clearance >= 0.10 m", null],
];
dashboard.getRange("E5").formulas = [["=IF(AVERAGE('Scenario Summary'!$E$5,'Scenario Summary'!$E$8)>=0.9,\"PASS\",\"FAIL\")"]];
dashboard.getRange("E6").formulas = [["=IF(B6>=0.8,\"PASS\",\"FAIL\")"]];
dashboard.getRange("E7").formulas = [["=IF(SUM('Scenario Summary'!$I$11:$I$19)/SUM('Scenario Summary'!$C$11:$C$19)>=0.9,\"PASS\",\"FAIL\")"]];
dashboard.getRange("E8").formulas = [["=IF(B9=0,\"PASS\",\"FAIL\")"]];
dashboard.getRange("E9").formulas = [["=IF(B8<=0.05,\"PASS\",\"FAIL\")"]];
dashboard.getRange("E10").formulas = [["=IF(B10>=0.1,\"PASS\",\"FAIL\")"]];
dashboard.getRange("A4:B4").format = dashboard.getRange("D4:E4").format = {
  fill: "#285E80",
  font: { bold: true, color: "#FFFFFF" },
};
dashboard.getRange("A5:B10").format = dashboard.getRange("D5:E10").format = {
  fill: "#F7F9FB",
  borders: { insideHorizontal: { style: "thin", color: "#DDE5EC" } },
};
dashboard.getRange("B6:B7").format.numberFormat = "0.0%";
dashboard.getRange("B8:B10").format.numberFormat = "0.000";
dashboard.getRange("E5:E10").conditionalFormats.add("containsText", {
  text: "PASS",
  format: { fill: "#DDF3E4", font: { color: "#145A32", bold: true } },
});
dashboard.getRange("E5:E10").conditionalFormats.add("containsText", {
  text: "FAIL",
  format: { fill: "#FDE2E2", font: { color: "#9B1C1C", bold: true } },
});
dashboard.getRange("A:L").format.columnWidth = 14;
dashboard.getRange("A:A").format.columnWidth = 32;
dashboard.getRange("D:D").format.columnWidth = 32;
const completionChart = dashboard.charts.add("bar", {
  chartType: "bar",
  title: "Vision Completion by Scenario",
  hasLegend: false,
});
completionChart.title = "Vision Completion by Scenario";
const completionSeries = completionChart.series.add("Completion");
completionSeries.categoryFormula = "'Scenario Summary'!$A$5:$A$19";
completionSeries.formula = "'Scenario Summary'!$E$5:$E$19";
completionSeries.fill = "#1499C6";
completionChart.hasLegend = false;
completionChart.yAxis = { numberFormatCode: "0%", min: 0, max: 1 };
completionChart.setPosition("G4", "L18");
const errorChart = dashboard.charts.add("bar", {
  chartType: "bar",
  title: "Mean Lane Error by Scenario (m)",
  hasLegend: false,
});
errorChart.title = "Mean Lane Error by Scenario (m)";
const errorSeries = errorChart.series.add("Mean lane error");
errorSeries.categoryFormula = "'Scenario Summary'!$A$5:$A$19";
errorSeries.formula = "'Scenario Summary'!$F$5:$F$19";
errorSeries.fill = "#E76F2E";
errorChart.hasLegend = false;
errorChart.yAxis = { numberFormatCode: "0.000" };
errorChart.setPosition("A13", "F29");

const protocol = workbook.worksheets.add("Protocol");
protocol.showGridLines = false;
protocol.getRange("A1:D1").merge();
protocol.getRange("A1").values = [["Research Results Workbook - Reproducibility Notes"]];
protocol.getRange("A1:D1").format = {
  fill: "#17324D",
  font: { name: "Aptos Display", size: 18, bold: true, color: "#FFFFFF" },
  rowHeight: 32,
};
protocol.getRange("A3:B13").values = [
  ["Item", "Value"],
  ["Formal configuration", "82999888659be0c7"],
  ["Webots", "R2025a"],
  ["Python", "3.12.0"],
  ["NumPy", "2.4.2"],
  ["OpenCV", "4.10.0"],
  ["Vision scenarios", "15 scenarios x 10 repetitions = 150 trials"],
  ["Multi-obstacle coverage", "Sequential static, sequential moving, and mixed layouts; 10 repetitions each"],
  ["Baseline scenarios", "6 lane scenarios x 10 repetitions = 60 trials"],
  ["Raw source", "results/formal/raw/*.csv and results/formal/telemetry/*.csv"],
  ["Analysis source", "results/formal/enriched_summary.csv"],
];
protocol.getRange("A3:B3").format = {
  fill: "#285E80",
  font: { bold: true, color: "#FFFFFF" },
};
protocol.getRange("A4:B13").format = {
  borders: { insideHorizontal: { style: "thin", color: "#DDE5EC" } },
  wrapText: true,
};
protocol.getRange("A:A").format.columnWidth = 26;
protocol.getRange("B:B").format.columnWidth = 72;

const overview = await workbook.inspect({
  kind: "table",
  range: "Dashboard!A1:L29",
  include: "values,formulas",
  tableMaxRows: 30,
  tableMaxCols: 12,
});
console.log(overview.ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);
const preview = await workbook.render({
  sheetName: "Dashboard",
  range: "A1:L29",
  scale: 1.4,
  format: "png",
});
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
for (const [sheetName, range, fileName] of [
  ["Scenario Summary", "A1:N19", "workbook_scenario_summary.png"],
  ["Baseline Comparison", "A1:H29", "workbook_baseline_comparison.png"],
  ["Protocol", "A1:D13", "workbook_protocol.png"],
  ["Raw Results", "A1:AH22", "workbook_raw_sample.png"],
]) {
  const rendered = await workbook.render({
    sheetName,
    range,
    scale: 1.2,
    format: "png",
  });
  await fs.writeFile(
    path.join(projectRoot, "evidence", fileName),
    new Uint8Array(await rendered.arrayBuffer()),
  );
}
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
console.log(previewPath);

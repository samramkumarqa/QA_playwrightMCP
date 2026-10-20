// @ts-check
/**
 * Reads test-data/TestData.xlsx (the input sheet).
 *   RunControl sheet: TestCaseID | Title | Requirement | Run (Y/N)
 *   TestData sheet:   TestCaseID | Key | Value
 */
const path = require('path');
const ExcelJS = require('exceljs');

const FILE = path.join(__dirname, '..', 'test-data', 'TestData.xlsx');
let cache;

const text = (v) => (v && typeof v === 'object' && 'text' in v ? String(v.text) : String(v ?? '')).trim();

async function load() {
  if (cache) return cache;
  const wb = new ExcelJS.Workbook();
  await wb.xlsx.readFile(FILE);
  const data = {};
  const run = {};
  wb.getWorksheet('TestData')?.eachRow((row, i) => {
    if (i === 1) return;
    const [id, key, value] = [text(row.getCell(1).value), text(row.getCell(2).value), text(row.getCell(3).value)];
    if (!id || !key) return;
    (data[id] ??= {})[key] = value;
  });
  wb.getWorksheet('RunControl')?.eachRow((row, i) => {
    if (i === 1) return;
    run[text(row.getCell(1).value)] = text(row.getCell(4).value).toUpperCase() !== 'N';
  });
  cache = { data, run };
  return cache;
}

/** Key/value test data for one test case. */
async function getTestData(testCaseId) {
  return (await load()).data[testCaseId] ?? {};
}

/** False when the test case's Run column is N. */
async function shouldRun(testCaseId) {
  const { run } = await load();
  return run[testCaseId] ?? true;
}

module.exports = { getTestData, shouldRun };

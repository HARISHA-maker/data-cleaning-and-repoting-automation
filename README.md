# Data Cleaning & Reporting Automation

## Objective

Automate the full workflow of cleaning a messy dataset and producing reports with visual summaries, using Python (pandas, matplotlib, xlsxwriter).

## Files

| File | Purpose |
|---|---|
| `generate_messy_data.py` | Creates a sample sales dataset (`raw_sales.csv`) with deliberate data-quality problems |
| `clean_and_report.py` | The main pipeline: load, profile, clean, validate, report |
| `raw_sales.csv` | Input data (635 rows) |
| `cleaned_sales.csv` | Cleaned data (600 rows) |
| `sales_report.xlsx` | Excel report: summary, charts, breakdowns, cleaning log, validation, cleaned data |
| `report.html` | Standalone HTML report with KPIs and charts (download and open in a browser) |
| `revenue_by_month.png`, `revenue_by_region.png`, `revenue_by_product.png` | Chart images |
| `requirements.txt` | Python packages needed |

## How to run

```bash
pip install -r requirements.txt
python generate_messy_data.py
python clean_and_report.py raw_sales.csv output
```

Running the pipeline creates an `output/` folder containing the cleaned data, Excel report, HTML report and charts. The copies in this repository are the results from one sample run.

To use your own data, pass your CSV as the first argument and adjust the column names and valid region/product lists at the top of `clean_and_report.py`.

## Pipeline steps

1. **Load and profile**: record data types, missing counts and unique values of the raw file.
2. **Clean** (every step is logged with the number of rows affected):
   - Remove exact duplicate rows (35 removed).
   - Trim whitespace and standardise case (e.g. `" north "`, `"NORTH"` become `North`).
   - Fix typos (`Laptp` becomes `Laptop`, 15 rows).
   - Convert currency text such as `$1,200.00` to numbers.
   - Parse dates written in two formats (`YYYY-MM-DD` and `DD/MM/YYYY`).
   - Replace impossible values (negative prices, quantities over 100) with missing, then handle them like other missing values.
   - Fill missing values:
     - `unit_price`: median price of the same product
     - `quantity`: overall median
     - `region`: labelled `Unknown` rather than guessed
     - `customer_email`: left as is, since it is not used in the analysis
3. **Validate**: 7 automatic checks (no duplicate order IDs, no missing dates, positive prices and quantities, valid product and region labels). All passed.
4. **Report**: calculate revenue by month, region and product, then generate charts, an Excel workbook and an HTML report.

## Results (sample data)

- Rows: 635 raw, 600 after cleaning
- Total revenue: about $1.05M across 600 orders and 2,358 units
- Top product: Laptop. Top region: East.

## Why automate?

- **Repeatable**: the same cleaning rules run every time, so results are consistent.
- **Fast**: a new data file goes from raw to finished report in one command.
- **Transparent**: the cleaning log and validation sheet show exactly what changed.
- **Less error-prone**: manual fixes in Excel are easy to miss or apply inconsistently.

## Limitations

- Median imputation is simple; it can understate variation in the data.
- The sample data is synthetic, so the figures are for demonstration only.
- Only known typos listed in `typo_map` are corrected automatically.

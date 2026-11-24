"""
Data Cleaning & Reporting Automation
Usage:  python clean_and_report.py [input.csv] [output_dir]

Pipeline:  load -> profile -> clean (logged) -> validate -> report (Excel + charts + HTML)
"""
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("raw_sales.csv")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output")
OUT.mkdir(exist_ok=True)

VALID_REGIONS = ["North", "South", "East", "West"]
VALID_PRODUCTS = ["Laptop", "Phone", "Tablet", "Monitor", "Keyboard"]
log = []  # audit trail: (step, rows_affected, detail)


def record(step, n, detail=""):
    log.append({"step": step, "rows_affected": int(n), "detail": detail})


# ---------------------------------------------------------------- 1. LOAD
raw = pd.read_csv(INPUT)
df = raw.copy()
record("Load raw file", len(df), f"{raw.shape[1]} columns")

# ---------------------------------------------------------------- 2. PROFILE
profile = pd.DataFrame({
    "dtype": raw.dtypes.astype(str),
    "missing": raw.isna().sum(),
    "missing_%": (raw.isna().mean() * 100).round(1),
    "unique": raw.nunique(),
})

# ---------------------------------------------------------------- 3. CLEAN
# 3a. duplicates
before = len(df)
df = df.drop_duplicates()
record("Remove exact duplicate rows", before - len(df))

# 3b. text standardisation
for col in ["region", "product", "customer_email"]:
    df[col] = df[col].astype("string").str.strip()
df["region"] = df["region"].str.title()
df["product"] = df["product"].str.title()
df["customer_email"] = df["customer_email"].str.lower()
record("Trim whitespace and standardise case", len(df), "region, product, email")

# 3c. fix known typos using closest valid label
typo_map = {"Laptp": "Laptop"}
fixed = df["product"].isin(typo_map).sum()
df["product"] = df["product"].replace(typo_map)
record("Correct product typos", fixed, str(typo_map))

# 3d. numeric text -> numbers
df["unit_price"] = pd.to_numeric(
    df["unit_price"].astype("string").str.replace(r"[$,]", "", regex=True), errors="coerce"
)
record("Convert currency text to numeric", len(df), "unit_price")

# 3e. mixed date formats -> datetime
iso = pd.to_datetime(df["order_date"], format="%Y-%m-%d", errors="coerce")
dmy = pd.to_datetime(df["order_date"], format="%d/%m/%Y", errors="coerce")
df["order_date"] = iso.fillna(dmy)
bad_dates = df["order_date"].isna().sum()
record("Parse mixed date formats", len(df) - bad_dates, f"{bad_dates} unparseable")

# 3f. invalid values -> NaN (negative prices, absurd quantities)
neg = (df["unit_price"] <= 0).sum()
df.loc[df["unit_price"] <= 0, "unit_price"] = np.nan
q_cap = df["quantity"].quantile(0.99) if df["quantity"].notna().any() else np.nan
big = (df["quantity"] > 100).sum()
df.loc[df["quantity"] > 100, "quantity"] = np.nan
record("Null out impossible values", neg + big, f"{neg} negative prices, {big} quantities > 100")

# 3g. impute missing values
# price: median of the same product (prices differ by product)
miss_price = df["unit_price"].isna().sum()
df["unit_price"] = df["unit_price"].fillna(df.groupby("product")["unit_price"].transform("median"))
record("Impute missing unit_price", miss_price, "median per product")

# quantity: overall median
miss_qty = df["quantity"].isna().sum()
df["quantity"] = df["quantity"].fillna(df["quantity"].median()).astype(int)
record("Impute missing quantity", miss_qty, "overall median")

# region: cannot be guessed reliably -> label explicitly instead of inventing data
miss_reg = df["region"].isna().sum()
df["region"] = df["region"].fillna("Unknown")
record("Flag missing region", miss_reg, "set to 'Unknown'")

# email missing is kept as-is (not needed for revenue reporting)
record("Leave missing email untouched", df["customer_email"].isna().sum(), "not used in analysis")

# 3h. derived columns
df["revenue"] = (df["quantity"] * df["unit_price"]).round(2)
df["month"] = df["order_date"].dt.to_period("M").astype(str)
df = df.dropna(subset=["order_date"]).sort_values("order_date").reset_index(drop=True)

# ---------------------------------------------------------------- 4. VALIDATE
checks = {
    "No duplicate order_id": df["order_id"].is_unique,
    "No missing dates": df["order_date"].notna().all(),
    "No missing quantity/price": df[["quantity", "unit_price"]].notna().all().all(),
    "All quantities positive": (df["quantity"] > 0).all(),
    "All prices positive": (df["unit_price"] > 0).all(),
    "Products valid": df["product"].isin(VALID_PRODUCTS).all(),
    "Regions valid (incl. Unknown)": df["region"].isin(VALID_REGIONS + ["Unknown"]).all(),
}
validation = pd.DataFrame({"check": checks.keys(), "passed": checks.values()})
failed = validation[~validation["passed"]]
if len(failed):
    print("VALIDATION FAILED:\n", failed)

# ---------------------------------------------------------------- 5. REPORT
by_month = df.groupby("month", as_index=False)["revenue"].sum()
by_region = df.groupby("region", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False)
by_product = df.groupby("product", as_index=False).agg(revenue=("revenue", "sum"), units=("quantity", "sum")) \
                .sort_values("revenue", ascending=False)

kpis = {
    "Total revenue": df["revenue"].sum(),
    "Orders": len(df),
    "Units sold": int(df["quantity"].sum()),
    "Avg order value": df["revenue"].mean(),
    "Top product": by_product.iloc[0]["product"],
    "Top region": by_region[by_region["region"] != "Unknown"].iloc[0]["region"],
}

# --- charts (one consistent style)
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "font.size": 10})
BLUE, GREY = "#2f6fb3", "#9aa5b1"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=150)
    plt.close(fig)


fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(by_month["month"], by_month["revenue"] / 1000, marker="o", color=BLUE)
ax.set_title("Monthly revenue"); ax.set_ylabel("Revenue ($ thousands)")
plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
save(fig, "revenue_by_month.png")

fig, ax = plt.subplots(figsize=(6, 3.8))
ax.bar(by_region["region"], by_region["revenue"] / 1000, color=BLUE)
ax.set_title("Revenue by region"); ax.set_ylabel("Revenue ($ thousands)")
save(fig, "revenue_by_region.png")

fig, ax = plt.subplots(figsize=(6, 3.8))
ax.barh(by_product["product"][::-1], by_product["revenue"][::-1] / 1000, color=BLUE)
ax.set_title("Revenue by product"); ax.set_xlabel("Revenue ($ thousands)")
save(fig, "revenue_by_product.png")

# --- cleaned data + Excel report
df.to_csv(OUT / "cleaned_sales.csv", index=False)
log_df = pd.DataFrame(log)

with pd.ExcelWriter(OUT / "sales_report.xlsx", engine="xlsxwriter") as xw:
    wb = xw.book
    hdr = wb.add_format({"bold": True, "bg_color": "#2f6fb3", "font_color": "white", "border": 1})
    money = wb.add_format({"num_format": "$#,##0.00"})

    summary = pd.DataFrame({"Metric": list(kpis.keys()), "Value": list(kpis.values())})
    summary.to_excel(xw, "Summary", index=False)
    ws = xw.sheets["Summary"]
    ws.set_column("A:A", 22); ws.set_column("B:B", 18)
    for c, name in enumerate(summary.columns):
        ws.write(0, c, name, hdr)
    ws.write("B2", kpis["Total revenue"], money)
    ws.write("B5", kpis["Avg order value"], money)
    ws.insert_image("D2", str(OUT / "revenue_by_month.png"), {"x_scale": 0.55, "y_scale": 0.55})
    ws.insert_image("D18", str(OUT / "revenue_by_region.png"), {"x_scale": 0.45, "y_scale": 0.45})
    ws.insert_image("L18", str(OUT / "revenue_by_product.png"), {"x_scale": 0.45, "y_scale": 0.45})

    for name, frame in [("By Month", by_month), ("By Region", by_region), ("By Product", by_product),
                        ("Cleaning Log", log_df), ("Validation", validation), ("Profile (raw)", profile.reset_index())]:
        frame.to_excel(xw, name, index=False)
        w = xw.sheets[name]
        for c, col in enumerate(frame.columns):
            w.write(0, c, col, hdr)
            w.set_column(c, c, max(14, len(str(col)) + 4))

    df.to_excel(xw, "Cleaned Data", index=False)
    xw.sheets["Cleaned Data"].freeze_panes(1, 0)
    xw.sheets["Cleaned Data"].set_column("A:K", 15)

# --- HTML report
def table(frame):
    return frame.to_html(index=False, border=0, classes="t", float_format=lambda v: f"{v:,.2f}")

html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Sales Data Report</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#1f2933}}
h1{{margin-bottom:0}} .sub{{color:#6b7785;margin-top:.2rem}}
.kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:1.5rem 0}}
.kpi{{background:#f3f6fa;border-radius:8px;padding:12px 16px}}
.kpi b{{display:block;font-size:1.4rem}} .kpi span{{color:#6b7785;font-size:.85rem}}
img{{max-width:100%}} .row{{display:flex;gap:12px;flex-wrap:wrap}} .row img{{flex:1;min-width:300px}}
table.t{{border-collapse:collapse;width:100%;font-size:.9rem}}
.t th{{text-align:left;background:#2f6fb3;color:#fff;padding:6px 8px}}
.t td{{padding:6px 8px;border-bottom:1px solid #e4e9ef}}
</style></head><body>
<h1>Sales Data Report</h1>
<p class="sub">Generated {datetime.now():%Y-%m-%d %H:%M} from <code>{INPUT.name}</code></p>
<div class="kpis">
 <div class="kpi"><b>${kpis['Total revenue']:,.0f}</b><span>Total revenue</span></div>
 <div class="kpi"><b>{kpis['Orders']:,}</b><span>Orders</span></div>
 <div class="kpi"><b>${kpis['Avg order value']:,.0f}</b><span>Avg order value</span></div>
 <div class="kpi"><b>{kpis['Units sold']:,}</b><span>Units sold</span></div>
 <div class="kpi"><b>{kpis['Top product']}</b><span>Top product</span></div>
 <div class="kpi"><b>{kpis['Top region']}</b><span>Top region</span></div>
</div>
<img src="revenue_by_month.png" alt="Monthly revenue">
<div class="row"><img src="revenue_by_region.png" alt="By region"><img src="revenue_by_product.png" alt="By product"></div>
<h2>What was cleaned</h2>{table(log_df)}
<h2>Validation checks</h2>{table(validation)}
</body></html>"""
import base64
for img in ["revenue_by_month", "revenue_by_region", "revenue_by_product"]:
    b64 = base64.b64encode((OUT / f"{img}.png").read_bytes()).decode()
    html = html.replace(f'src="{img}.png"', f'src="data:image/png;base64,{b64}"')
(OUT / "report.html").write_text(html, encoding="utf-8")

print(f"Raw rows: {len(raw)}  ->  Clean rows: {len(df)}")
print(log_df.to_string(index=False))
print("\nValidation:\n", validation.to_string(index=False))
print("\nOutputs in:", OUT.resolve())

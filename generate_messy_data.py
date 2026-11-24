"""Generate a deliberately messy sales dataset (raw_sales.csv) for the cleaning demo."""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
N = 600

regions = ["North", "South", "East", "West"]
products = ["Laptop", "Phone", "Tablet", "Monitor", "Keyboard"]
price = {"Laptop": 900, "Phone": 600, "Tablet": 400, "Monitor": 250, "Keyboard": 50}

df = pd.DataFrame({
    "order_id": np.arange(1001, 1001 + N),
    "order_date": pd.to_datetime("2026-01-01") + pd.to_timedelta(rng.integers(0, 300, N), unit="D"),
    "region": rng.choice(regions, N),
    "product": rng.choice(products, N),
    "quantity": rng.integers(1, 8, N).astype(float),
    "customer_email": [f"user{i}@example.com" for i in rng.integers(1, 250, N)],
})
df["unit_price"] = df["product"].map(price) * rng.uniform(0.9, 1.1, N)
df["unit_price"] = df["unit_price"].round(2)

# ---- inject mess ----
# 1. inconsistent text formatting
df["region"] = [r.lower() if i % 7 == 0 else (r.upper() if i % 11 == 0 else f"  {r} ")
                if i % 13 == 0 else r for i, r in enumerate(df["region"])]
df["product"] = [p.lower() if i % 9 == 0 else p for i, p in enumerate(df["product"])]
df.loc[df.sample(15, random_state=1).index, "product"] = "Laptp"   # typo

# 2. mixed date formats (stored as strings)
dates = df["order_date"].dt.strftime("%Y-%m-%d")
dates = [d if i % 4 else pd.Timestamp(d).strftime("%d/%m/%Y") for i, d in enumerate(dates)]
df["order_date"] = dates

# 3. missing values
df.loc[df.sample(40, random_state=2).index, "quantity"] = np.nan
df.loc[df.sample(30, random_state=3).index, "unit_price"] = np.nan
df.loc[df.sample(25, random_state=4).index, "region"] = np.nan
df.loc[df.sample(20, random_state=5).index, "customer_email"] = np.nan

# 4. outliers / impossible values
df.loc[df.sample(4, random_state=6).index, "quantity"] = 500
df.loc[df.sample(3, random_state=7).index, "unit_price"] = -50

# 5. numbers stored as text with currency symbols
df["unit_price"] = [f"${v:,.2f}" if (pd.notna(v) and i % 10 == 0) else v
                    for i, v in enumerate(df["unit_price"])]

# 6. exact duplicates
df = pd.concat([df, df.sample(35, random_state=8)], ignore_index=True)
df = df.sample(frac=1, random_state=9).reset_index(drop=True)

df.to_csv("raw_sales.csv", index=False)
print(f"Wrote raw_sales.csv with {len(df)} rows")

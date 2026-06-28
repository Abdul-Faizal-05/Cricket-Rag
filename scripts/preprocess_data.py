import pandas as pd

# Load CSV
df = pd.read_csv("IPL.csv")

# Convert date column to datetime (adjust column name if needed)
df['date'] = pd.to_datetime(df['date'], errors='coerce')

# Filter rows between 2023 and 2025
filtered_df = df[(df['date'] >= '01-01-2024') & (df['date'] <= '31-12-2025')]

# Save result
filtered_df.to_csv("ipl_2024-2025.csv", index=False)
import pandas as pd
import re

def clean_dataframe(df):
    """Membersihkan dataframe saham agar siap masuk DB"""
    
    # Strip semua string
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].str.strip()

    # Konversi angka dengan K/M/B/T
    def convert_num(val):
        if pd.isna(val):
            return None
        val = str(val).replace(".", "").replace(",", ".")
        match = re.match(r"([\d\.]+)([KMBT]?)", val, re.IGNORECASE)
        if not match:
            return float(val) if val.replace(".", "", 1).isdigit() else None
        number, suffix = match.groups()
        number = float(number)
        multipliers = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
        return number * multipliers.get(suffix.upper(), 1)

    for col in ["Harga", "Volume", "Market_Cap", "Terakhir", "Pembukaan", "Tertinggi", "Terendah", "Vol"]:
        if col in df.columns:
            df[col] = df[col].apply(convert_num)

    # Format tanggal
    if "Tanggal" in df.columns:
        df["Tanggal"] = pd.to_datetime(df["Tanggal"], dayfirst=True, errors="coerce")
        df["Tanggal"] = df["Tanggal"].dt.strftime("%Y-%m-%d")

    # Format kolom persen
    for col in df.columns:
        if df[col].dtype == "object" and df[col].str.contains("%").any():
            df[col] = df[col].str.replace("%", "", regex=False)
            df[col] = df[col].str.replace(",", ".", regex=False)
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

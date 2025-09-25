import pandas as pd
import re

def clean_dataframe(df):
    """Membersihkan dataframe saham agar siap masuk DB"""
    
    # Strip semua string (hapus spasi depan/belakang)
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].str.strip()

    # Konversi kolom angka yang kadang ada koma / titik
    def convert_num(val):
        if pd.isna(val):
            return None
        val = str(val).replace(".", "").replace(",", ".")  # standardize decimal
        match = re.match(r"([\d\.]+)([KMBT]?)", val, re.IGNORECASE)
        if not match:
            return float(val) if val.replace(".", "", 1).isdigit() else None
        number, suffix = match.groups()
        number = float(number)
        multipliers = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
        return number * multipliers.get(suffix.upper(), 1)

    # Bersihkan kolom numeric yang umum dipakai
    for col in ["Harga", "Volume", "Market_Cap", "Terakhir", "Pembukaan", "Tertinggi", "Terendah", "Vol"]:
        if col in df.columns:
            df[col] = df[col].apply(convert_num)

    return df

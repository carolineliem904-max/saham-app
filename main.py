import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from tabulate import tabulate
from sqlalchemy import create_engine, MetaData, Table, insert, delete
from dotenv import load_dotenv
import os

# --- Load environment ---
load_dotenv()

# ===============================
# 1. DATABASE UTILITIES
# ===============================

def buat_koneksi():
    """Membuat koneksi ke database MySQL menggunakan SQLAlchemy"""
    try:
        user = os.getenv('DB_USER')
        password = os.getenv('DB_PASSWORD')
        host = 'localhost'
        db_name = 'data_saham'

        engine = create_engine(f"mysql+mysqlconnector://{user}:{password}@{host}/{db_name}")
        print("Koneksi ke database berhasil ✅")
        return engine
    except Exception as e:
        print(f"Terjadi error: '{e}'")
        return None


def tampilkan_dataframe(koneksi, nama_tabel, limit=None):
    """Menampilkan data dari tabel tertentu dalam bentuk DataFrame"""
    try:
        query = f"SELECT * FROM {nama_tabel} LIMIT {limit}"
        df = pd.read_sql(query, koneksi)
        print(f"\n=== DATA: {nama_tabel.upper()} ===")
        print(df)
        return df
    except Exception as e:
        print(f"Terjadi error saat membaca {nama_tabel}: '{e}'")
        return None



# fungsi tambah saham 
def tambah_saham(koneksi):
    """Menambahkan data Saham baru menggunakan SQLAlchemy Core"""
    print("\n=== TAMBAH SAHAM BARU ===")
    try:
        # Input data dari user
        tanggal = input("Masukkan tanggal saham (YYYY-MM-DD): ")
        nama = input("Masukkan nama saham: ")
        sektor = input("Masukkan sektor saham: ")
        kepemilikan = input("Masukkan nama kepemilikan saham: ")
        harga = int(input("Masukkan harga saham (Rp): "))
        volume = int(input("Masukkan volume saham: "))
        mcap = int(input("Masukkan marketcap saham: "))

        metadata = MetaData()
        saham_table = Table('kumpulan_saham', metadata, autoload_with=koneksi)

        stmt = insert(saham_table).values(
            Tanggal=tanggal,
            Nama_Saham=nama,
            Sektor=sektor,
            Kepemilikan=kepemilikan,
            Harga=harga,
            Volume=volume,
            Market_Cap=mcap
        )

        with koneksi.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()

        print(f"Saham '{nama}' berhasil ditambahkan! ✅")
        print(f"ID Saham Baru: {result.inserted_primary_key[0]}")

    except ValueError:
        print("Error: Harga, Volume, dan Marketcap harus berupa angka")
    except Exception as e:
        print(f"Terjadi error database: {e}")


# fungsi delete saham 

def hapus_saham(koneksi):
    """Menghapus data saham dari tabel berdasarkan Nama_Saham"""
    print("\n=== HAPUS SAHAM ===")
    try:
        nama = input("Masukkan nama saham yang ingin dihapus: ")

        metadata = MetaData()
        saham_table = Table('kumpulan_saham', metadata, autoload_with=koneksi)

        stmt = delete(saham_table).where(saham_table.c.Nama_Saham == nama)

        with koneksi.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()

        if result.rowcount > 0:
            print(f"Saham '{nama}' berhasil dihapus! ✅")
        else:
            print(f"Saham '{nama}' tidak ditemukan di database ❌")

    except Exception as e:
        print(f"Terjadi error database: {e}")



# ===============================
# 2. ANALYSIS FUNCTIONS
# ===============================

def find_undervalued_stocks(kumpulan_df):
    undervalued = []
    for sector in kumpulan_df['Sektor'].unique():
        sector_df = kumpulan_df[kumpulan_df['Sektor'] == sector]
        avg_mcap = sector_df['Market_Cap'].mean()

        for _, row in sector_df.iterrows():
            if row['Market_Cap'] < avg_mcap:
                undervalued.append({
                    'Nama_Saham': row['Nama_Saham'],
                    'Sektor': sector,
                    'Market_Cap': row['Market_Cap'],
                    'Avg_Sector_Cap': avg_mcap,
                    'Undervalued (%)': round((avg_mcap - row['Market_Cap']) / avg_mcap * 100, 2)
                })

    return pd.DataFrame(undervalued)


def owner_performance(histori_df, kumpulan_df):
    histori_df['Tanggal'] = pd.to_datetime(histori_df['Tanggal'])

    # ambil harga awal & akhir per saham (kalau datanya ada)
    price_summary = (
        histori_df.sort_values("Tanggal")
        .groupby("Nama_Saham")
        .agg(
            Harga_Awal=("Terakhir", "first"),
            Harga_Akhir=("Terakhir", "last")
        )
        .reset_index()
    )

    # join ke kumpulan_df supaya semua saham tetap muncul
    merged = pd.merge(
        kumpulan_df[["Nama_Saham", "Kepemilikan"]],
        price_summary,
        on="Nama_Saham",
        how="left"
    )

    merged["Growth_2Y (%)"] = (
        (merged["Harga_Akhir"] - merged["Harga_Awal"]) /
        merged["Harga_Awal"] * 100
    )

    # hitung rata-rata growth per kepemilikan
    owner_perf = (
        merged.groupby("Kepemilikan")["Growth_2Y (%)"]
        .mean()
        .reset_index()
        .sort_values("Growth_2Y (%)", ascending=False)
    )

    return owner_perf, merged

def stock_growth(histori_df, kumpulan_df):
    histori_df['Tanggal'] = pd.to_datetime(histori_df['Tanggal'])

    # hitung harga awal & akhir per saham (kalau datanya ada)
    growth = (
        histori_df.sort_values("Tanggal")
        .groupby("Nama_Saham")
        .agg(
            Harga_Awal=("Terakhir", "first"),
            Harga_Akhir=("Terakhir", "last")
        )
        .reset_index()
    )

    # join ke kumpulan_df supaya semua saham tetap muncul
    growth = pd.merge(
        kumpulan_df[["Nama_Saham", "Sektor", "Kepemilikan"]],
        growth,
        on="Nama_Saham",
        how="left"
    )

    # hitung growth, beri NaN kalau datanya tidak lengkap
    growth["Growth_2Y (%)"] = (
        (growth["Harga_Akhir"] - growth["Harga_Awal"]) /
        growth["Harga_Awal"] * 100
    )

    return growth.sort_values("Growth_2Y (%)", ascending=False)

def max_sector_upside(kumpulan_df):
    results = []
    
    for sector in kumpulan_df['Sektor'].unique():
        sector_df = kumpulan_df[kumpulan_df['Sektor'] == sector]
        
        for _, row in sector_df.iterrows():
            current_stock = row['Nama_Saham']
            current_cap = row['Market_Cap']
            
            # cari saham dengan market cap tertinggi di sektor (selain dirinya sendiri)
            others = sector_df[sector_df['Nama_Saham'] != current_stock]
            if others.empty:
                continue  # kalau hanya ada 1 saham di sektor, skip
            
            max_target = others.sort_values('Market_Cap', ascending=False).iloc[0]
            
            target_stock = max_target['Nama_Saham']
            target_cap = max_target['Market_Cap']
            
            upside = round((target_cap - current_cap) / current_cap * 100, 2)
            
            results.append({
                'Nama_Saham': current_stock,
                'Sektor': sector,
                'Current_MCap': f"{current_cap:,.0f}",   # format pakai koma
                'Target_Saham': target_stock,
                'Target_MCap': f"{target_cap:,.0f}",
                'Max_Upside (%)': f"{upside:+,.2f}%"    # selalu tampilkan + atau -
            })
    
    df = pd.DataFrame(results)
    
    # urutkan per sektor, lalu upside terbesar → kecil
    df = df.sort_values(by=["Sektor", "Max_Upside (%)"], ascending=[True, False])
    return df


# ===============================
# 3. VISUALIZATION FUNCTIONS
# ===============================

def plot_marketcap_by_sector(kumpulan_df):
    plt.figure(figsize=(10, 6))
    sector_mcap = kumpulan_df.groupby("Sektor")["Market_Cap"].sum().reset_index()
    sns.barplot(data=sector_mcap, x="Sektor", y="Market_Cap", palette="Set2")
    plt.title("📊 Market Cap per Sector", fontsize=14, weight="bold")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def plot_volume_vs_marketcap(histori_df, kumpulan_df):
    avg_volume = histori_df.groupby("Nama_Saham")["Vol"].mean().reset_index()
    merged = pd.merge(kumpulan_df, avg_volume, on="Nama_Saham")

    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=merged, x="Vol", y="Market_Cap", hue="Sektor",
                    size="Market_Cap", sizes=(50, 500), alpha=0.7)
    plt.xscale("log")
    plt.yscale("log")
    plt.title("📉 Volume vs Market Cap", fontsize=14, weight="bold")
    plt.xlabel("Rata-rata Volume (log)")
    plt.ylabel("Market Cap (log)")
    plt.grid(True, which="both", ls="--")
    plt.tight_layout()
    plt.show()


def plot_price_trend(histori_df, stock):
    df = histori_df[histori_df["Nama_Saham"] == stock].sort_values("Tanggal")
    plt.figure(figsize=(10, 5))
    plt.plot(df["Tanggal"], df["Terakhir"], marker="o")
    plt.title(f"📈 Price Trend of {stock} (2Y)", fontsize=14, weight="bold")
    plt.xlabel("Tanggal")
    plt.ylabel("Harga Terakhir")
    plt.grid(True)
    plt.show()


def plot_multiple_price_trends(histori_df, stocks):
    """
    Plot price trends of multiple stocks on the same chart for comparison.
    
    Parameters:
        histori_df (pd.DataFrame): Historical stock data.
        stocks (list): List of stock names to plot, e.g. ["DEWA", "UNTR", "PTRO"].
    """
    plt.figure(figsize=(12, 6))

    for stock in stocks:
        df = histori_df[histori_df["Nama_Saham"] == stock].sort_values("Tanggal")
        plt.plot(df["Tanggal"], df["Terakhir"], marker="o", label=stock)

    plt.title(f"📊 Price Trend Comparison ({', '.join(stocks)})", fontsize=14, weight="bold")
    plt.xlabel("Tanggal")
    plt.ylabel("Harga Terakhir")
    plt.legend(title="Saham")
    plt.grid(True)
    plt.show()

def plot_sector_marketcap_pie(df_kumpulan):
    """
    Menunjukkan proporsi market cap antar sektor.
    """
    sector_cap = df_kumpulan.groupby("Sektor")["Market_Cap"].sum()

    plt.figure(figsize=(8, 8))
    plt.pie(
        sector_cap,
        labels=sector_cap.index,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.85
    )
    plt.title("🥧 Proporsi Market Cap per Sektor", fontsize=14, weight="bold")
    plt.show()

#===============================
#4. MAIN MENU
#===============================

def main():
    engine = buat_koneksi()
    if not engine:
        return

    # Ambil data awal
    df_kumpulan = tampilkan_dataframe(engine, "kumpulan_saham", limit=1000)
    df_histori = tampilkan_dataframe(engine, "histori_saham", limit=10000)

    # bug fix untuk clean histori_saham nama saham yang ada space nya 3
    df_kumpulan["Nama_Saham"] = df_kumpulan["Nama_Saham"].str.strip()
    df_histori["Nama_Saham"]  = df_histori["Nama_Saham"].str.strip()

    while True:
        print("\n=== MENU UTAMA ===")
        print("1. Tampilkan data saham")
        print("2. Tambah saham baru")
        print("3. Hapus Saham")
        print("4. Analisa kinerja pemilik & pertumbuhan saham")
        print("5. Visualisasi data")
        print("6. Keluar")

        pilihan = input("Masukkan pilihan Anda (1-6): ")

        if pilihan == "1":
            tampilkan_dataframe(engine, "kumpulan_saham", 100)

        elif pilihan == "2":
            tambah_saham(engine)
        
        elif pilihan == "3":
            hapus_saham(engine)

        elif pilihan == "4":
            owner_perf, merged_detail = owner_performance(df_histori, df_kumpulan)
            print("\n=== OWNER PERFORMANCE ===")
            print(owner_perf.to_string())

            print("\n=== STOCK GROWTH (2Y) ===")
            growth_df = stock_growth(df_histori, df_kumpulan)
            print(growth_df.to_string())

            print("\n=== SAHAM UNDERVALUE (per sektor) ===")
            undervalue_df = find_undervalued_stocks(df_kumpulan)
            print(undervalue_df.to_string(index=False))

            print("\n=== POTENSI UPSIDE (per sektor) ===")
            upside_df = max_sector_upside(df_kumpulan)
            print(upside_df.to_string())

        elif pilihan == "5":
            print("\n--- MENU VISUALISASI ---")
            print("1. Market Cap per Sektor")
            print("2. Volume vs Market Cap")
            print("3. Tren harga saham (pilih kode saham)")
            print("4. Tren harga beberapa saham (pilih kode saham)")
            sub_pilihan = input("Pilih jenis visualisasi (1-4): ")

            if sub_pilihan == "1":
                plot_marketcap_by_sector(df_kumpulan)
                plot_sector_marketcap_pie(df_kumpulan)
            elif sub_pilihan == "2":
                plot_volume_vs_marketcap(df_histori, df_kumpulan)
            elif sub_pilihan == "3":
                stock_code = input("Masukkan kode saham (contoh: BRMS): ").upper()
                if stock_code in df_histori["Nama_Saham"].unique():
                    plot_price_trend(df_histori, stock_code)
                else:
                    print(f"Saham {stock_code} tidak ditemukan.")
            elif sub_pilihan == "4":
                stock_codes = input(
            "Masukkan kode saham (pisahkan dengan koma, contoh: DEWA, UNTR, PTRO): "
                ).upper().split(",")
                stock_codes = [s.strip() for s in stock_codes]  # hapus spasi ekstra

             # validasi apakah semua saham ada di data
                valid_stocks = [s for s in stock_codes if s in df_histori["Nama_Saham"].unique()]
                if valid_stocks:
                    plot_multiple_price_trends(df_histori, valid_stocks)
                else:
                    print("Tidak ada saham valid ditemukan dalam input.")
            else:
                print("Pilihan tidak valid.")
        elif pilihan == "6":
            print("Terima kasih, program dihentikan.")
            break
        else:
            print("Pilihan tidak valid. Silakan masukkan 1-6.")

    engine.dispose()


if __name__ == "__main__":
    main()


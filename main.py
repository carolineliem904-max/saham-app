import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from tabulate import tabulate
from sqlalchemy import create_engine, MetaData, Table, insert, delete
from dotenv import load_dotenv
import os

from rich.console import Console
from rich.table import Table
from rich.text import Text
from numerize import numerize

console = Console()
# --- Load environment ---
load_dotenv()

console = Console()

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

# membuat tampilan dataframe jadi lebih mudah dibaca 
def tampilkan_tabel(df, title="DATA", use_rich=True):
    """Universal beautifier for any DataFrame"""
    if df is None or df.empty:
        print(f"\n⚠️ {title} kosong / tidak ada data.")
        return

    print(f"\n=== {title.upper()} ===")

    if use_rich:
        table = Table(show_header=True, header_style="bold cyan")
        for col in df.columns:
            table.add_column(str(col))

        for _, row in df.iterrows():
            formatted_row = []
            for col in df.columns:
                val = row[col]

                # === Format angka besar jadi K/M/B/T ===
                if col.lower() in ["volume", "market_cap", "vol", "final_value", "current_mcap", "target_mcap"]:
                    val = numerize.numerize(val)

                # === Format persen growth/upside ===
                elif "%" in col.lower():
                    try:
                        num = float(val)
                        if num > 0:
                            val = Text(f"{num:.2f}%", style="bold green")
                        elif num < 0:
                            val = Text(f"{num:.2f}%", style="bold red")
                        else:
                            val = Text(f"{num:.2f}%", style="white")
                    except:
                        val = Text(str(val), style="white")

                # === Format angka biasa ===
                elif isinstance(val, (int, float)):
                    val = f"{val:,}"

                else:
                    val = str(val)

                formatted_row.append(val)   # <-- keep Text objects here!

            table.add_row(*formatted_row)

        console.print(table)
    else:
        print(df)


# menampilkan dataframe 
def tampilkan_dataframe(koneksi, nama_tabel, limit=None):
    """Menampilkan data dari tabel tertentu dalam bentuk DataFrame"""
    try:
        query = f"SELECT * FROM {nama_tabel} LIMIT {limit}"
        df = pd.read_sql(query, koneksi)
        print(f"\n=== DATA: {nama_tabel.upper()} ===")
        # print(df)
        return df
    except Exception as e:
        print(f"Terjadi error saat membaca {nama_tabel}: '{e}'")
        return None


# --- FUNGSI TAMBAH SAHAM ---
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

#  --- FUNGSI DELETE SAHAM ---

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

# --- PERFORMA OWNER ---
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

    merged["Growth_2Y (%)"] = ((
        (merged["Harga_Akhir"] - merged["Harga_Awal"]) /
        merged["Harga_Awal"] * 100).round(2)
    )

    # hitung rata-rata growth per kepemilikan
    owner_perf = (
        merged.groupby("Kepemilikan")["Growth_2Y (%)"]
        .mean()
        .reset_index()
        .sort_values("Growth_2Y (%)", ascending=False)
    )

    return owner_perf, merged

# --- STOCK GROWTH ---
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
    growth["Growth_2Y (%)"] = ((
        (growth["Harga_Akhir"] - growth["Harga_Awal"]) /
        growth["Harga_Awal"] * 100).round(2)
    )
    return growth.sort_values("Growth_2Y (%)", ascending=False)

# POTENSI UPSIDE PER SEKTOR ---
def potensi_upside(kumpulan_df, top_n=None):
    results = []

    for sector in kumpulan_df['Sektor'].unique():
        sector_df = kumpulan_df[kumpulan_df['Sektor'] == sector]

        for _, row in sector_df.iterrows():
            current_stock = row['Nama_Saham']
            current_cap = row['Market_Cap']

            # cari saham dengan market cap tertinggi di sektor (selain dirinya)
            others = sector_df[sector_df['Nama_Saham'] != current_stock]
            if others.empty:
                continue

            max_target = others.sort_values('Market_Cap', ascending=False).iloc[0]

            target_stock = max_target['Nama_Saham']
            target_cap = max_target['Market_Cap']

            upside = round((target_cap - current_cap) / current_cap * 100, 2)

            results.append({
                'Nama_Saham': current_stock,
                'Sektor': sector,
                'Current_MCap': current_cap,
                'Target_Saham': target_stock,
                'Target_MCap': target_cap,
                'Max_Upside (%)': upside
            })

    df = pd.DataFrame(results)

    if df.empty:
        return df

    # sort berdasarkan upside
    df = df.sort_values(by="Max_Upside (%)", ascending=False)

    # kalau hanya mau top N positif
    if top_n is not None:
        df = df[df["Max_Upside (%)"] > 0]  # ambil yang positif
        df = df.head(top_n)

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

# heatmap return per saham
def plot_monthly_return_heatmap(histori_df):
    # make sure date is datetime
    df = histori_df.copy()
    df["Tanggal"] = pd.to_datetime(df["Tanggal"])

    # calculate monthly return per stock
    df["Month"] = df["Tanggal"].dt.to_period("M")
    df = df.sort_values(["Nama_Saham", "Tanggal"])

    df["Return"] = df.groupby("Nama_Saham")["Terakhir"].pct_change()

    # average return per month
    monthly_returns = (
        df.groupby(["Nama_Saham", "Month"])["Return"]
        .mean()
        .reset_index()
    )

    # pivot for heatmap (stocks x months)
    pivot = monthly_returns.pivot(index="Nama_Saham", columns="Month", values="Return")

    plt.figure(figsize=(14, 8))
    sns.heatmap(pivot, cmap="RdYlGn", center=0, annot=False, cbar_kws={"label": "Return"})
    plt.title("🔥 Monthly Return Heatmap per Stock", fontsize=16, weight="bold")
    plt.xlabel("Month")
    plt.ylabel("Stock")
    plt.tight_layout()
    plt.show()

# heatmap return per sektor 
def plot_sector_monthly_return_heatmap(histori_df, kumpulan_df):
    # copy data
    df = histori_df.copy()
    df["Tanggal"] = pd.to_datetime(df["Tanggal"])

    # add Month column (period by month)
    df["Month"] = df["Tanggal"].dt.to_period("M")

    # hitung return per saham
    df = df.sort_values(["Nama_Saham", "Tanggal"])
    df["Return"] = df.groupby("Nama_Saham")["Terakhir"].pct_change()

    # gabungkan sektor
    df = pd.merge(df, kumpulan_df[["Nama_Saham", "Sektor"]], on="Nama_Saham", how="left")

    # rata-rata return per sektor per bulan
    monthly_sector_returns = (
        df.groupby(["Sektor", "Month"])["Return"]
        .mean()
        .reset_index()
    )

    # pivot untuk heatmap (Sektor x Month)
    pivot = monthly_sector_returns.pivot(index="Sektor", columns="Month", values="Return")

    # plot heatmap
    plt.figure(figsize=(14, 8))
    sns.heatmap(
        pivot,
        cmap="RdYlGn",
        center=0,
        annot=False,
        cbar_kws={"label": "Return"}
    )
    plt.title("🔥 Monthly Return Heatmap per Sector", fontsize=16, weight="bold")
    plt.xlabel("Month")
    plt.ylabel("Sector")
    plt.tight_layout()
    plt.show()

#===============================
#4. SIMULASI TRADING
#===============================

import matplotlib.ticker as ticker

def simulate_investment(histori_df, month, year, initial_money, target_date=None, show_plot=True):
    results = []

    # Pastikan Tanggal jadi datetime
    histori_df = histori_df.copy()
    histori_df["Tanggal"] = pd.to_datetime(histori_df["Tanggal"])

    # Tentukan target_date otomatis jika tidak diberikan
    if target_date is None:
        target_date = histori_df["Tanggal"].max()
    else:
        target_date = pd.to_datetime(target_date)

    # Ambil harga penutupan di target_date
    target_prices = (
        histori_df[histori_df["Tanggal"] == target_date]
        .set_index("Nama_Saham")["Terakhir"]
    )

    for stock in histori_df["Nama_Saham"].unique():
        entry_df = histori_df[
            (histori_df["Nama_Saham"] == stock) &
            (histori_df["Tanggal"].dt.month == month) &
            (histori_df["Tanggal"].dt.year == year)
        ]
        if entry_df.empty or stock not in target_prices:
            continue

        entry_price = entry_df.iloc[0]["Terakhir"]
        target_price = target_prices[stock]

        shares = initial_money / entry_price
        final_value = shares * target_price
        profit_pct = (final_value - initial_money) / initial_money * 100

        results.append({
            "Nama_Saham": stock,
            "Entry_Price": entry_price,
            "Target_Price": target_price,
            "Final_Value": round(final_value, 2),
            "Return (%)": round(profit_pct, 2)
        })

    if not results:
        print(f"\n⚠️ Tidak ada data saham untuk {month}/{year}. Coba bulan/tahun lain.")
        return pd.DataFrame()

    df = pd.DataFrame(results).sort_values("Return (%)", ascending=False)

    # === Plot Return (%) & Final Value ===
    if show_plot and not df.empty:
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Left: Return %
        axes[0].bar(df["Nama_Saham"], df["Return (%)"], color="skyblue")
        axes[0].axhline(0, color="gray", linestyle="--")
        axes[0].set_title(f"Return (%) dari {month}/{year} → {target_date.date()}")
        axes[0].set_ylabel("Return (%)")
        axes[0].tick_params(axis="x", rotation=45)

        # Right: Final Value
        axes[1].bar(df["Nama_Saham"], df["Final_Value"], color="lightgreen")
        axes[1].set_title(f"Final Value (Rp) dari {month}/{year} → {target_date.date()}")
        axes[1].set_ylabel("Rp")
        axes[1].tick_params(axis="x", rotation=45)

        # Format angka rupiah biar lebih enak dibaca
        axes[1].yaxis.set_major_formatter(
            ticker.FuncFormatter(lambda x, pos: f"{int(x):,}".replace(",", "."))
        )

        plt.tight_layout()
        plt.show()
    
    # === Auto-summary ===
    best = df.iloc[0]
    worst = df.iloc[-1]
    print("\n=== RINGKASAN SIMULASI ===")
    print(f"📈 Best performer: {best['Nama_Saham']} ({best['Return (%)']}%) → Rp {best['Final_Value']:,}".replace(",", "."))
    print(f"📉 Worst performer: {worst['Nama_Saham']} ({worst['Return (%)']}%) → Rp {worst['Final_Value']:,}".replace(",", "."))

    return df

#===============================
#5. CARI SAHAM 
#===============================

def cari_saham(histori_df, stock_code, year=None, month=None):
    # pastikan tanggal dalam datetime
    histori_df = histori_df.copy()
    histori_df["Tanggal"] = pd.to_datetime(histori_df["Tanggal"])

    # filter saham
    stock_df = histori_df[histori_df["Nama_Saham"] == stock_code.upper()]
    if stock_df.empty:
        print(f"⚠️ Saham {stock_code} tidak ditemukan.")
        return None

    if year and month:
        # cari harga berdasarkan tahun & bulan
        entry = stock_df[
            (stock_df["Tanggal"].dt.year == year) &
            (stock_df["Tanggal"].dt.month == month)
        ]
        if entry.empty:
            print(f"⚠️ Tidak ada data {stock_code} untuk {month}/{year}.")
            return None
        result = entry.iloc[0]
        print("\n=== HASIL PENCARIAN SAHAM ===")
        print(f"Saham      : {result['Nama_Saham']}")
        print(f"Tanggal    : {result['Tanggal'].date()}")
        print(f"Harga (Rp) : {result['Terakhir']}")
        return result
    else:
        # ambil harga terakhir
        latest = stock_df.sort_values("Tanggal").iloc[-1]
        print("\n=== HARGA TERBARU SAHAM ===")
        print(f"Saham      : {latest['Nama_Saham']}")
        print(f"Tanggal    : {latest['Tanggal'].date()}")
        print(f"Harga (Rp) : {latest['Terakhir']}")

        # tampilkan mini history (misal 6 bulan terakhir)
        history = stock_df.sort_values("Tanggal").tail(6)
        print("\n--- Riwayat 6 bulan terakhir ---")
        tampilkan_tabel(history[["Tanggal", "Terakhir"]], "Riwayat 6 bulan terakhir")
        return latest


#===============================
#6. MAIN MENU
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
        print("6. Simulasi Trading")
        print("7. Cari Saham")
        print("8. Keluar")

        pilihan = input("Masukkan pilihan Anda (1-8): ")

        if pilihan == "1":
            tampilkan_tabel(tampilkan_dataframe(engine, "kumpulan_saham", 100), "Kumpulan Saham")
            tampilkan_tabel(tampilkan_dataframe(engine, "histori_saham", 30), "Histori Saham")

        elif pilihan == "2":
            tambah_saham(engine)
        
        elif pilihan == "3":
            hapus_saham(engine)

        elif pilihan == "4":
            owner_perf, merged_detail = owner_performance(df_histori, df_kumpulan)
            tampilkan_tabel(owner_perf, "Owner Performance")

            growth_df = stock_growth(df_histori, df_kumpulan)
            tampilkan_tabel(growth_df, "Stock Growth (2Y)")

            upside_df = potensi_upside(df_kumpulan)   # versi lengkap
            tampilkan_tabel(upside_df, "Potensi Upside (per sektor)")

            top_upside_df = potensi_upside(df_kumpulan, top_n=5)   # hanya top 5 positif
            tampilkan_tabel(top_upside_df, "Top 5 Potensi Upside")

        elif pilihan == "5":
            print("\n--- MENU VISUALISASI ---")
            print("1. Market Cap per Sektor")
            print("2. Volume vs Market Cap")
            print("3. Tren harga saham (pilih kode saham)")
            print("4. Tren harga beberapa saham (pilih kode saham)")
            print("5. Heatmap return per saham")
            print("6. Heatmap return per sektor")
            sub_pilihan = input("Pilih jenis visualisasi (1-6): ")

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
            elif sub_pilihan == "5":
                plot_monthly_return_heatmap(df_histori)

            elif sub_pilihan == "6":
                plot_sector_monthly_return_heatmap(df_histori, df_kumpulan)
            else:
                print("Pilihan tidak valid.")

        elif pilihan == "6":
            while True:
                print("\n=== SIMULASI INVESTASI ===")
                month = int(input("Masukkan bulan entry (1-12): "))
                year = int(input("Masukkan tahun entry (contoh: 2023): "))
                money = float(input("Masukkan jumlah uang yang diinvestasikan (Rp): "))

                result_df = simulate_investment(df_histori, month, year, money, show_plot=True)
                tampilkan_tabel(result_df, "Hasil Simulasi")

                ulang = input("\nCoba simulasi lagi? (y/n): ").lower()
                if ulang != "y":
                    break

        elif pilihan == "7":
            print("\n=== CARI SAHAM ===")
            stock_code = input("Masukkan kode saham (contoh: BRMS): ").upper()
            year_input = input("Masukkan tahun (enter jika ingin harga terbaru): ")
            month_input = input("Masukkan bulan (1-12, enter jika ingin harga terbaru): ")

            year = int(year_input) if year_input.strip() else None
            month = int(month_input) if month_input.strip() else None

            cari_saham(df_histori, stock_code, year, month)

        elif pilihan == "8":
            print("Terima kasih, program dihentikan.")
            break
        else:
            print("Pilihan tidak valid. Silakan masukkan 1-8.")

    engine.dispose()


if __name__ == "__main__":
    main()


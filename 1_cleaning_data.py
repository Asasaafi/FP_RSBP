import pandas as pd
import numpy as np

# 1. Baca data CSV
print("Membaca file amazon.csv...")
try:
    df = pd.read_csv('amazon.csv')
except FileNotFoundError:
    print("Error: File 'amazon.csv' tidak ditemukan. Pastikan file ada di folder yang sama.")
    exit()

# 2. Fungsi untuk membersihkan harga (hapus ₹ dan koma)
def clean_currency(x):
    if isinstance(x, str):
        x = x.replace('₹', '').replace(',', '').strip()
        if x == '': return 0
        return float(x)
    return x

# 3. Fungsi untuk membersihkan rating (kadang ada data error seperti '|')
def clean_rating(x):
    if isinstance(x, str):
        # Hapus karakter aneh jika ada
        if '|' in x: return 0 # Menganggap 0 jika datanya rusak
        return float(x.replace(',', ''))
    return x

print("Sedang membersihkan data...")

# Terapkan pembersihan
df['discounted_price'] = df['discounted_price'].apply(clean_currency)
df['actual_price'] = df['actual_price'].apply(clean_currency)
df['discount_percentage'] = df['discount_percentage'].astype(str).str.replace('%', '').astype(float)

# Bersihkan rating dan rating_count
# Data rating kadang error di dataset ini, kita paksa jadi numeric
df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(0)
df['rating_count'] = df['rating_count'].astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce').fillna(0)

# 4. Hapus data duplikat (User ID dan Product ID yang sama persis)
df.drop_duplicates(inplace=True)

# 5. Simpan file bersih
output_filename = 'amazon_cleaned.csv'
df.to_csv(output_filename, index=False)

print(f"SUKSES! Data bersih telah disimpan sebagai '{output_filename}'")
print(f"Jumlah baris data: {len(df)}")
print("Cek folder kamu, seharusnya ada file baru.")
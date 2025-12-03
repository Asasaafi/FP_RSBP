from neo4j import GraphDatabase
import pandas as pd
import time

# --- KONFIGURASI DATABASE ---
# URI biasanya default 'bolt://localhost:7687' untuk local
URI = "bolt://localhost:7687" 
AUTH = ("neo4j", "12345678") # <--- GANTI '12345678' DENGAN PASSWORD KAMU JIKA BEDA

def import_data():
    print("1. Membaca data CSV...")
    try:
        df = pd.read_csv('amazon_cleaned.csv')
        print(f"   Data ditemukan: {len(df)} baris.")
    except FileNotFoundError:
        print("   ERROR: File 'amazon_cleaned.csv' tidak ada. Jalankan cleaning dulu!")
        return

    print("2. Menghubungkan ke Neo4j...")
    try:
        driver = GraphDatabase.driver(URI, auth=AUTH)
        driver.verify_connectivity()
        print("   Koneksi BERHASIL!")
    except Exception as e:
        print(f"   Koneksi GAGAL: {e}")
        print("   Pastikan Database di Neo4j Desktop sudah START (Hijau).")
        return

    # Query Cypher untuk memasukkan data
    # Kita pakai MERGE supaya tidak duplikat
    cypher_query = """
    UNWIND $rows AS row
    
    // 1. Buat Node Category (Kita ambil kategori utama saja dari split '|')
    MERGE (c:Category {name: split(row.category, '|')[0]})
    
    // 2. Buat Node Product
    MERGE (p:Product {id: row.product_id})
    SET p.name = row.product_name,
        p.price = toFloat(row.discounted_price),
        p.rating = toFloat(row.rating),
        p.about = row.about_product,
        p.img = row.img_link

    // 3. Buat Node User
    MERGE (u:User {id: row.user_id})
    SET u.name = row.user_name
    
    // 4. Buat Relasi: PRODUCT --> CATEGORY
    MERGE (p)-[:IN_CATEGORY]->(c)
    
    // 5. Buat Relasi: USER --> REVIEW --> PRODUCT
    // Karena Review itu unik per interaksi, kita buat sebagai relasi langsung atau node terpisah.
    // Untuk analisis sentimen nanti, lebih mudah jika Review jadi Relasi WROTE
    MERGE (u)-[r:WROTE]->(p)
    SET r.review_id = row.review_id,
        r.title = row.review_title,
        r.content = row.review_content,
        r.rating = toFloat(row.rating)
    """

    print("3. Mulai memasukkan data ke Graph (Ini mungkin butuh 1-2 menit)...")
    start_time = time.time()
    
    with driver.session() as session:
        # Kita kirim data dalam batch (paket) agar tidak berat
        batch_size = 500
        total_rows = len(df)
        
        # Ubah dataframe ke list of dictionaries (format JSON)
        data_dict = df.to_dict('records')
        
        for i in range(0, total_rows, batch_size):
            batch = data_dict[i : i+batch_size]
            print(f"   Mengupload batch {i} sampai {i+len(batch)}...")
            session.run(cypher_query, rows=batch)
            
    end_time = time.time()
    print(f"\nSUKSES! Data selesai diimport dalam {round(end_time - start_time, 2)} detik.")
    driver.close()

if __name__ == "__main__":
    import_data()
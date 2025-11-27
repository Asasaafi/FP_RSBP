from neo4j import GraphDatabase
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import time

# --- DOWNLOAD KAMUS NLP ---
# Kita perlu download kamus kata-kata dulu (cuma sekali)
print("Downloading VADER dictionary...")
nltk.download('vader_lexicon')
sia = SentimentIntensityAnalyzer()

# --- KONFIGURASI DATABASE ---
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "12345678") # <--- GANTI PASSWORD KAMU

def update_sentiment():
    print("\n1. Menghubungkan ke Neo4j...")
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    # Query untuk mengambil semua review
    # Kita ambil ID relasi supaya nanti gampang update-nya
    fetch_query = """
    MATCH (u)-[r:WROTE]->(p)
    WHERE r.content IS NOT NULL
    RETURN elementId(r) AS id, r.content AS text
    """
    
    # Query untuk update sentiment
    update_query = """
    MATCH (u)-[r:WROTE]->(p)
    WHERE elementId(r) = $id
    SET r.sentiment = $label, 
        r.sentiment_score = $score
    """

    print("2. Sedang mengambil data review dari Graph...")
    with driver.session() as session:
        result = session.run(fetch_query)
        reviews = [record for record in result]
        
    print(f"   Ditemukan {len(reviews)} review untuk dianalisis.")
    print("3. Mulai analisis sentimen (NLP)...")
    
    count = 0
    start_time = time.time()
    
    with driver.session() as session:
        for item in reviews:
            review_id = item['id']
            text = item['text']
            
            # --- PROSES NLP (VADER) DISINI ---
            # Hitung skor (-1 s/d +1)
            score = sia.polarity_scores(str(text))['compound']
            
            # Tentukan Label
            if score > 0.05:
                label = "Positive"
            elif score < -0.05:
                label = "Negative"
            else:
                label = "Neutral"
            
            # Update kembali ke Neo4j
            session.run(update_query, id=review_id, label=label, score=score)
            
            count += 1
            if count % 100 == 0:
                print(f"   Sudah memproses {count} review...")

    end_time = time.time()
    driver.close()
    print(f"\nSUKSES! {count} review telah diberi label sentimen.")
    print(f"Waktu proses: {round(end_time - start_time, 2)} detik.")

if __name__ == "__main__":
    update_sentiment()
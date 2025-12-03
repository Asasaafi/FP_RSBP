from neo4j import GraphDatabase
from nltk.sentiment import SentimentIntensityAnalyzer
import pandas as pd
import time
import nltk
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# --- SETUP ---
print("Menyiapkan VADER & Tools...")
try:
    nltk.download('vader_lexicon', quiet=True)
except:
    pass

sia = SentimentIntensityAnalyzer()
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "12345678") # <--- PASTIIN PASSWORD BENAR

# --- FUNGSI DETEKSI ALASAN (Untuk Dashboard Temanmu) ---
NEGATIVE_WORDS = ["bad", "terrible", "worst", "broken", "waste", "poor", "slow", "late", "expensive"]

def detect_reason(text):
    t = str(text).lower()
    if any(k in t for k in ["price", "expensive", "cost"]): return "Isu Harga"
    if any(k in t for k in ["late", "delay", "delivery"]): return "Pengiriman Lama"
    if any(k in t for k in ["broken", "damage", "defect"]): return "Barang Rusak"
    if any(k in t for k in ["but", "however"]): return "Ada kata 'Tapi' (Kontras)"
    return "Sentimen Negatif Umum"

# --- FUNGSI UTAMA ---
def update_sentiment_and_report():
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    print("\n1. Mengambil data review dari Neo4j...")
    fetch_query = """
    MATCH (u)-[r:WROTE]->(p)
    WHERE r.content IS NOT NULL AND r.rating IS NOT NULL
    RETURN elementId(r) AS id, r.review_id AS review_id, r.content AS text, r.rating AS rating
    """
    
    with driver.session() as session:
        reviews = [record.data() for record in session.run(fetch_query)]
    
    print(f"   Ditemukan {len(reviews)} review. Mulai analisis...")

    # Variabel untuk menampung data laporan
    detailed_rows = []
    
    # Query update (supaya graph tetap update)
    update_query = """
    MATCH (u)-[r:WROTE]->(p)
    WHERE elementId(r) = $id
    SET r.sentiment = $label, r.sentiment_score = $score
    """
    
    start_time = time.time()
    
    with driver.session() as session:
        count = 0
        for item in reviews:
            text = str(item['text'])
            rating = float(item['rating']) if item['rating'] is not None else 0.0
            
            # --- LOGIKA VADER JUJUR (TANPA CHEAT) ---
            score = sia.polarity_scores(text)['compound']
            
            if score > 0.05:
                label = "Positive"
            elif score < -0.05:
                label = "Negative"
            else:
                label = "Neutral"
            
            # Update ke Database Neo4j
            session.run(update_query, id=item['id'], label=label, score=score)
            
            # --- Tentukan Ground Truth (Standar E-commerce yang DIBENARKAN) ---
            if rating >= 4.0: 
                ground_truth = "Positive"
            elif rating < 3.0:  # Rating 0.0 - 2.9 dianggap NEGATIVE
                ground_truth = "Negative"
            else: 
                ground_truth = "Neutral" # Rating 3.0 - 3.9 dianggap NETRAL
            
            # Simpan data untuk laporan CSV
            detailed_rows.append({
                'review_id': item.get('review_id'),
                'element_id': item['id'],
                'rating': rating,
                'ground_truth': ground_truth,
                'predicted': label,
                'score': score,
                'text': text,
                'reason': detect_reason(text) if label == 'Negative' else "-"
            })
            
            count += 1
            if count % 500 == 0:
                print(f"   Memproses {count} data...")

    driver.close()
    
    # --- BAGIAN PELAPORAN (GENERATING CSV) ---
    print("\n2. Membuat File Laporan Lengkap...")
    
    df = pd.DataFrame(detailed_rows)
    
    # Hitung Akurasi
    acc = accuracy_score(df['ground_truth'], df['predicted'])
    report = classification_report(df['ground_truth'], df['predicted'], output_dict=True, zero_division=0)
    
    # 1. Simpan CSV Utama: Evaluasi Akurasi (Dibaca sidebar dashboard)
    eval_results = {
        'overall_accuracy': acc * 100,
        'positive_accuracy': report.get('Positive', {}).get('precision', 0) * 100,
        'negative_accuracy': report.get('Negative', {}).get('precision', 0) * 100,
        'neutral_accuracy':  report.get('Neutral', {}).get('precision', 0) * 100,
        'avg_sentiment_score': df['score'].mean()
    }
    pd.DataFrame([eval_results]).to_csv('sentiment_evaluation.csv', index=False)
    
    # 2. Simpan CSV: Mismatches (Semua yang Bintang != AI)
    mismatches = df[df['ground_truth'] != df['predicted']]
    mismatches.to_csv('mismatches_all.csv', index=False)
    
    # 3. PECAHAN KASUS SPESIFIK (LENGKAP)
    
    # A. Kasus "Positif Terbuang" (False Negative)
    # Ground Truth = Positive, tapi AI bilang Negative/Neutral
    mis_pos = df[(df['ground_truth'] == 'Positive') & (df['predicted'] != 'Positive')]
    mis_pos.to_csv('misclassified_cases.csv', index=False) # WAJIB ADA buat dashboard teman
    mis_pos.to_csv('misclassified_Positive_missed.csv', index=False) 

    # B. Kasus "Negatif Lolos" (False Positive)
    # Ground Truth = Negative, tapi AI bilang Positive/Neutral
    mis_neg = df[(df['ground_truth'] == 'Negative') & (df['predicted'] != 'Negative')]
    mis_neg.to_csv('misclassified_Negative_missed.csv', index=False)

    # C. Kasus "Netral Bingung"
    # Ground Truth = Neutral, tapi AI bilang Positive/Negative
    mis_neu = df[(df['ground_truth'] == 'Neutral') & (df['predicted'] != 'Neutral')]
    mis_neu.to_csv('misclassified_Neutral_missed.csv', index=False)
    
    # 4. Simpan Detail Prediksi Lengkap
    df.to_csv('predictions_detailed.csv', index=False)
    
    print("\n" + "="*50)
    print("✅ SUKSES! Analisis Selesai.")
    print(f"   Akurasi Model VADER: {round(acc*100, 2)}%")
    print(f"   [File] Negatif Lolos : {len(mis_neg)} data")
    print(f"   [File] Netral Meleset: {len(mis_neu)} data")
    print(f"   [File] Dashboard Ready: sentiment_evaluation.csv & misclassified_cases.csv")
    print("="*50)

if __name__ == "__main__":
    update_sentiment_and_report()
import streamlit as st
from neo4j import GraphDatabase
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN WEB ---
st.set_page_config(
    page_title="Amazon Sentiment Graph",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- KONEKSI DATABASE ---
# GANTI PASSWORD DISINI SESUAI PNY MU
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "12345678") 

@st.cache_resource
def get_driver():
    return GraphDatabase.driver(URI, auth=AUTH)

def run_query(query, params={}):
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, params)
        return [record.data() for record in result]

# --- JUDUL DASHBOARD ---
st.title("📊 Amazon Product Knowledge Graph & Sentiment")
st.markdown("Dashboard analisis sentimen berbasis Graph Database dan NLP.")

# --- SIDEBAR (FILTER) ---
st.sidebar.header("Filter Data")
category_query = "MATCH (c:Category) RETURN c.name as category ORDER BY c.name"
categories = [r['category'] for r in run_query(category_query)]
selected_category = st.sidebar.selectbox("Pilih Kategori Produk:", ["All"] + categories)

# --- BAGIAN 1: RINGKASAN DATA (KPI) ---
col1, col2, col3 = st.columns(3)

# Hitung Total Review
if selected_category == "All":
    count_query = "MATCH ()-[r:WROTE]->() RETURN count(r) as total"
    params = {}
else:
    count_query = "MATCH ()-[r:WROTE]->()-[:IN_CATEGORY]->(c:Category {name: $cat}) RETURN count(r) as total"
    params = {'cat': selected_category}

total_reviews = run_query(count_query, params)[0]['total']
col1.metric("Total Review Dianalisis", total_reviews)

# Hitung Sentiment Breakdown
if selected_category == "All":
    sent_query = """
    MATCH ()-[r:WROTE]->() 
    RETURN r.sentiment as sentiment, count(r) as count
    """
else:
    sent_query = """
    MATCH ()-[r:WROTE]->()-[:IN_CATEGORY]->(c:Category {name: $cat})
    RETURN r.sentiment as sentiment, count(r) as count
    """

sentiment_data = pd.DataFrame(run_query(sent_query, params))

# Visualisasi Pie Chart Sentimen
if not sentiment_data.empty:
    fig_pie = px.pie(sentiment_data, values='count', names='sentiment', 
                     title=f"Distribusi Sentimen ({selected_category})",
                     color='sentiment',
                     color_discrete_map={'Positive':'#2ecc71', 'Negative':'#e74c3c', 'Neutral':'#95a5a6'})
    col2.plotly_chart(fig_pie, use_container_width=True)
else:
    col2.info("Belum ada data sentimen.")

# --- BAGIAN 2: TOP PRODUK POSITIF ---
st.subheader("🏆 Top 5 Produk Paling Disukai")
top_pos_query = """
MATCH (p:Product)<-[r:WROTE]-(u)
WHERE r.sentiment = 'Positive'
MATCH (p)-[:IN_CATEGORY]->(c)
WHERE $cat = 'All' OR c.name = $cat
RETURN p.name as Produk, count(r) as Jumlah_Review_Positif
ORDER BY Jumlah_Review_Positif DESC LIMIT 5
"""
top_products = pd.DataFrame(run_query(top_pos_query, params))
if not top_products.empty:
    st.dataframe(top_products, use_container_width=True)
else:
    st.write("Tidak ada data.")

# --- BAGIAN 3: SEMANTIC SEARCH (FITUR KEREN) ---
st.divider()
st.subheader("🔍 Cari Produk Berdasarkan Kata Kunci")
search_term = st.text_input("Ketik nama produk (misal: Cable, Samsung, dll):")

if search_term:
    search_query = """
    MATCH (u)-[r:WROTE]->(p:Product)
    WHERE toLower(p.name) CONTAINS toLower($term)
    RETURN p.name as Nama_Produk, r.sentiment as Sentimen, r.content as Isi_Review, r.rating as Rating
    LIMIT 10
    """
    results = pd.DataFrame(run_query(search_query, {'term': search_term}))
    
    if not results.empty:
        st.write(f"Menampilkan hasil pencarian untuk: **{search_term}**")
        # Warnai tabel berdasarkan sentimen
        def highlight_sentiment(val):
            color = '#d4edda' if val == 'Positive' else '#f8d7da' if val == 'Negative' else ''
            return f'background-color: {color}'
        
        st.dataframe(results.style.applymap(highlight_sentiment, subset=['Sentimen']), use_container_width=True)
    else:
        st.warning("Produk tidak ditemukan.")

# --- FOOTER ---
st.markdown("---")
st.caption("Dikembangkan oleh Kelompok Graph Project - TM16 Demo")
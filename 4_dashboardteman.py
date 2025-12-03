import os
import streamlit as st
from neo4j import GraphDatabase
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Amazon Sentiment Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================================================
#                   GLOBAL CSS FIX (FINAL)
# ========================================================

st.markdown("""
<style>

:root {
    --bg-color: #ffffff;
    --text-color: #222222;
    --muted-text: #6b7280;
    --card-bg: #ffffff;
    --card-border: #e6e6e6;
}

[data-theme="dark"] {
    --bg-color: #0e1117;
    --text-color: #f2f2f2;
    --muted-text: #9aa4b2;
    --card-bg: #161a23;
    --card-border: #2a2f3d;
}

/* ----------------------------------------------------------------------------
   FIX METRIC VISIBILITY
---------------------------------------------------------------------------- */

[data-testid="stMetric"] * {
    color: var(--text-color) !important;
}

[data-testid="stMetricValue"],
strong {
    color: var(--text-color) !important;
    font-weight: 700 !important;
}

[data-testid="stMetricLabel"] {
    color: var(--text-color) !important;
    font-weight: 600 !important;
}

[data-testid="stMetric"] span,
[data-testid="stMetric"] div {
    color: var(--text-color) !important;
}

/* ----------------------------------------------------------------------------
   Layout & Component Styling
---------------------------------------------------------------------------- */

.block-container {
    padding-top: 20px !important;
    padding-left: 20px !important;
    padding-right: 20px !important;
}

/* ----------------------------------------------------------------------------
   HEADER TITLE FIX (BIAR GA TERPOTONG)
---------------------------------------------------------------------------- */

.main-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;

    padding: 20px 22px;               /* lebih tebal agar tidak terpotong */
    margin-top: 20px;                 /* JARAK dari atas, mencegah clipping */
    margin-bottom: 20px;

    border-radius: 12px;
    border: 1px solid var(--card-border);
    background: var(--card-bg);
    color: var(--text-color);

    font-size: 2rem;
    font-weight: 700;
    width: 100%;
    overflow: visible;                 /* FIX UTAMA → ikonnya tidak terpotong */
}

/* Icon di header */
.main-header img {
    height: 42px;                      /* ikon tidak terpotong */
    width: auto;
    object-fit: contain;
    margin-right: 5px;
}

/* ----------------------------------------------------------------------------
   Metric Cards
---------------------------------------------------------------------------- */

.stMetric {
    background-color: var(--card-bg) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 12px !important;
    padding: 14px !important;
}

/* Sidebar */
.sidebar .sidebar-content {
    background-color: var(--card-bg) !important;
    border: 1px solid var(--card-border);
    border-radius: 10px;
    padding: 15px;
}

/* Dataframe Styling */
div[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    border: 1px solid var(--card-border) !important;
    background-color: var(--card-bg) !important;
}

</style>
""", unsafe_allow_html=True)


# ========================================================
#                    DATABASE CONNECTION
# ========================================================

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "12345678")

@st.cache_resource
def get_driver():
    return GraphDatabase.driver(URI, auth=AUTH)

def run_query(query, params={}):
    with get_driver().session() as session:
        return [record.data() for record in session.run(query, params)]


# ========================================================
#                          HEADER
# ========================================================

st.markdown('<div class="main-header">📊 Amazon Product Sentiment Analysis</div>', unsafe_allow_html=True)


# ========================================================
#                        SIDEBAR
# ========================================================

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg", width=160)

    st.markdown("### Filter & Navigasi")

    try:
        categories = [r['category'] for r in run_query(
            "MATCH (c:Category) RETURN c.name AS category ORDER BY c.name")]
    except:
        categories = []

    selected_category = st.selectbox("Kategori Produk:", ["All"] + categories)

    st.markdown("---")
    st.markdown("### Metrik Akurasi & Score")

    try:
        eval_df = pd.read_csv('sentiment_evaluation.csv')

        overall_acc = eval_df['overall_accuracy'].iloc[0]
        pos_acc     = eval_df['positive_accuracy'].iloc[0]
        neg_acc     = eval_df['negative_accuracy'].iloc[0]
        neu_acc     = eval_df['neutral_accuracy'].iloc[0]
        avg_score   = eval_df['avg_sentiment_score'].iloc[0]

        st.metric("Overall Accuracy", f"{overall_acc:.1f}%")
        st.metric("Avg Sentiment Score", f"{avg_score:.3f}")
        st.caption(f"Positive: {pos_acc:.1f}% | Negative: {neg_acc:.1f}% | Neutral: {neu_acc:.1f}%")
    except:
        st.info("Jalankan sentiment_analysis.py dulu.")

    st.markdown("---")
    st.caption("💻 Neo4j + VADER Analysis | Built with Streamlit")


# ========================================================
#                        KPI CARDS
# ========================================================

params = {"cat": selected_category}
st.markdown("### Key Performance Indicators")

col1, col2, col3, col4 = st.columns(4)

# Helper run wrapper
def safe_query(query):
    try:
        data = run_query(query, params)
        return data[0] if data else {}
    except:
        return {}

# Total Reviews
res = safe_query("""
MATCH ()-[r:WROTE]->(p:Product)-[:IN_CATEGORY]->(c:Category)
WHERE $cat='All' OR c.name=$cat
RETURN count(r) AS total
""")
col1.metric("Total Reviews", f"{res.get('total',0):,}")

# Total Products
res = safe_query("""
MATCH (p:Product)-[:IN_CATEGORY]->(c:Category)
WHERE $cat='All' OR c.name=$cat
RETURN count(DISTINCT p) AS total
""")
col2.metric("Total Products", f"{res.get('total',0):,}")

# Avg Rating
res = safe_query("""
MATCH ()-[r:WROTE]->(p:Product)-[:IN_CATEGORY]->(c:Category)
WHERE $cat='All' OR c.name=$cat
RETURN avg(r.rating) AS avg_rating
""")
col3.metric("Avg Rating", f"{res.get('avg_rating',0):.2f} / 5.0")

# Positive Ratio
res_pos = safe_query("""
MATCH ()-[r:WROTE]->(p:Product)-[:IN_CATEGORY]->(c:Category)
WHERE r.sentiment='Positive' AND ($cat='All' OR c.name=$cat)
RETURN count(r) AS pos
""")
total_reviews = safe_query("""
MATCH ()-[r:WROTE]->(p:Product)-[:IN_CATEGORY]->(c:Category)
WHERE $cat='All' OR c.name=$cat
RETURN count(r) AS total
""").get("total", 1)

positive_ratio = (res_pos.get("pos", 0) / total_reviews * 100)
col4.metric("Positive Ratio", f"{positive_ratio:.1f}%")


# ========================================================
#                  SENTIMENT DISTRIBUTION
# ========================================================

st.markdown("---")
st.markdown("### Sentiment Distribution")

col1, col2 = st.columns(2)

sent_data = pd.DataFrame(run_query("""
MATCH ()-[r:WROTE]->(p:Product)-[:IN_CATEGORY]->(c:Category)
WHERE $cat='All' OR c.name=$cat
RETURN r.sentiment AS sentiment, count(r) AS count
""", params))

if not sent_data.empty:
    with col1:
        fig = px.pie(sent_data, names="sentiment", values="count",
                     hole=0.45, title=f"Sentiment Overview - {selected_category}")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.bar(sent_data, x="sentiment", y="count",
                      title="Review Count per Sentiment")
        st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("⚠ Tidak ada data.")


# ========================================================
#                        TOP PRODUCTS
# ========================================================

st.markdown("---")
st.markdown("### Top Products")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 🏆 Most Loved")
    df = pd.DataFrame(run_query("""
    MATCH (p:Product)<-[r:WROTE]-(u)
    WHERE r.sentiment='Positive'
    MATCH (p)-[:IN_CATEGORY]->(c)
    WHERE $cat='All' OR c.name=$cat
    RETURN p.name AS Product, count(r) AS Positive_Reviews, avg(r.rating) AS Avg_Rating
    ORDER BY Positive_Reviews DESC LIMIT 5
    """, params))
    st.dataframe(df, hide_index=True, use_container_width=True)

with col2:
    st.markdown("#### 💔 Most Disliked")
    df = pd.DataFrame(run_query("""
    MATCH (p:Product)<-[r:WROTE]-(u)
    WHERE r.sentiment='Negative'
    MATCH (p)-[:IN_CATEGORY]->(c)
    WHERE $cat='All' OR c.name=$cat
    RETURN p.name AS Product, count(r) AS Negative_Reviews, avg(r.rating) AS Avg_Rating
    ORDER BY Negative_Reviews DESC LIMIT 5
    """, params))
    st.dataframe(df, hide_index=True, use_container_width=True)


# ========================================================
#                 MISCLASSIFIED POSITIVE
# ========================================================

import os
st.markdown("---")
st.markdown("### 🔍 Misclassified & Mismatches (bukan hanya Positive→notPositive)")

misfile = 'misclassified_cases.csv'
mismatch_all = 'mismatches_all.csv'
pred_file = 'predictions_detailed.csv'

# If misclassified file exists and has rows -> show it
if os.path.exists(misfile):
    try:
        mis_df = pd.read_csv(misfile)
        if not mis_df.empty:
            st.metric("Total Misclassified (Positive→not Positive)", len(mis_df))
            display_df = mis_df[['rating','predicted','score','reason','text']].head(10)
            display_df.columns = ['Rating','Predicted','Score','Reason','Review Text']
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            # fallback to mismatches_all.csv
            if os.path.exists(mismatch_all):
                mdf = pd.read_csv(mismatch_all)
                if not mdf.empty:
                    st.metric("Total Mismatches (any ground_truth != predicted)", len(mdf))
                    dir_counts = mdf.groupby(['ground_truth','predicted']).size().reset_index(name='count')
                    st.write("Mismatch breakdown:")
                    st.dataframe(dir_counts, use_container_width=True, hide_index=True)
                    display_df = mdf[['rating','ground_truth','predicted','score','reason','text']].head(15)
                    display_df.columns = ['Rating','Ground Truth','Predicted','Score','Reason','Review Text']
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                else:
                    st.info("Tidak ada mismatch (semua prediksi sesuai ground truth).")
            else:
                # Try build from predictions_detailed if exists
                if os.path.exists(pred_file):
                    pred_df = pd.read_csv(pred_file)
                    mis = pred_df[(pred_df['ground_truth']=='Positive') & (pred_df['predicted']!='Positive')]
                    if not mis.empty:
                        mis[['review_id','element_id','rating','ground_truth','predicted','score','text','reason']].to_csv(misfile, index=False)
                        st.metric("Total Misclassified (Positive→not Positive)", len(mis))
                        display_df = mis[['rating','predicted','score','reason','text']].head(10)
                        display_df.columns = ['Rating','Predicted','Score','Reason','Review Text']
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("Tidak ada kasus misclassified (berdasarkan predictions_detailed).")
                else:
                    st.info("File misclassified kosong dan predictions_detailed.csv tidak ditemukan. Jalankan sentiment_analysis.py")
    except Exception as e:
        st.error(f"Error membaca {misfile}: {e}")
else:
    # If misfile doesn't exist, try mismatches_all first
    if os.path.exists(mismatch_all):
        mdf = pd.read_csv(mismatch_all)
        if not mdf.empty:
            st.metric("Total Mismatches (any ground_truth != predicted)", len(mdf))
            dir_counts = mdf.groupby(['ground_truth','predicted']).size().reset_index(name='count')
            st.write("Mismatch breakdown:")
            st.dataframe(dir_counts, use_container_width=True, hide_index=True)
            display_df = mdf[['rating','ground_truth','predicted','score','reason','text']].head(15)
            display_df.columns = ['Rating','Ground Truth','Predicted','Score','Reason','Review Text']
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada mismatch. Jalankan sentiment_analysis.py")
    else:
        # fallback: try to build from predictions_detailed.csv
        if os.path.exists(pred_file):
            pred_df = pd.read_csv(pred_file)
            mis = pred_df[(pred_df['ground_truth']=='Positive') & (pred_df['predicted']!='Positive')]
            if not mis.empty:
                mis[['review_id','element_id','rating','ground_truth','predicted','score','text','reason']].to_csv(misfile, index=False)
                st.metric("Total Misclassified (Positive→not Positive)", len(mis))
                display_df = mis[['rating','predicted','score','reason','text']].head(10)
                display_df.columns = ['Rating','Predicted','Score','Reason','Review Text']
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.info("Belum ada file misclassified_cases.csv atau mismatches_all.csv. Jalankan sentiment_analysis.py untuk menghasilkan file tersebut.")
        else:
            st.info("Belum ada file misclassified_cases.csv atau predictions_detailed.csv. Jalankan sentiment_analysis.py terlebih dahulu.")
# ========================================================
#                     SEMANTIC SEARCH
# ========================================================

st.markdown("---")
st.markdown("### 🔎 Semantic Search")

term = st.text_input("Cari nama produk...")
if term:
    df = pd.DataFrame(run_query("""
    MATCH (u)-[r:WROTE]->(p:Product)
    WHERE toLower(p.name) CONTAINS toLower($term)
    RETURN p.name AS Product, r.sentiment AS Sentiment, r.content AS Review, r.rating AS Rating
    LIMIT 50
    """, {"term": term}))
    if df.empty:
        st.error("Tidak ada hasil.")
    else:
        st.success(f"Found {len(df)} results.")
        st.dataframe(df, hide_index=True, use_container_width=True)


# ========================================================
#                          FOOTER
# ========================================================

st.markdown("---")
st.markdown("<div style='text-align:center; color:var(--muted-text);'>Amazon Sentiment Dashboard • Neo4j + Streamlit</div>", unsafe_allow_html=True)
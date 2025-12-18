import streamlit as st
import json
import pandas as pd
import os
import altair as alt # Uvozimo Altair za grafe
from transformers import pipeline

# --- 1. KONFIGURACIJA STRANI ---
st.set_page_config(
    page_title="Web Scraping Dashboard",
    page_icon="🕷️",
    layout="wide"
)

# --- 2. FUNKCIJE ZA NALAGANJE ---

@st.cache_data
def load_data():
    file_path = 'scraped_data.json'
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

@st.cache_resource
def load_sentiment_model():
    return pipeline("sentiment-analysis")

data = load_data()

if not data:
    st.error("⚠️ Datoteka 'scraped_data.json' ne obstaja! Najprej poženi scraper.py.")
    st.stop()

# --- 3. SIDEBAR NAVIGACIJA ---
st.sidebar.title("Navigation")
view_option = st.sidebar.radio(
    "Go to:",
    ["Products", "Testimonials", "Reviews"]
)
st.sidebar.markdown("---")

selected_rating_filter = "All"
if view_option == "Testimonials":
    st.sidebar.subheader("Filter Testimonials")
    selected_rating_filter = st.sidebar.radio(
        "Show by Rating:",
        ["All", "5 Stars", "4 Stars", "3 Stars", "2 Stars", "1 Star"]
    )

st.sidebar.info("Web Scraping Project\nStreamlit Dashboard")

# --- 4. GLAVNI PRIKAZ ---
st.title(f"📊 {view_option} Overview")

# ==========================================
# A) PRODUCTS VIEW
# ==========================================
if view_option == "Products":
    st.write("List of all scraped products.")
    products_list = data.get("products", [])
    
    if products_list:
        df_products = pd.DataFrame(products_list)
        st.metric("Total Products", len(df_products))
        st.dataframe(
            df_products, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "price": st.column_config.TextColumn("Price", width="small"),
                "title": st.column_config.TextColumn("Product Name")
            }
        )
    else:
        st.warning("No products found.")

# ==========================================
# B) TESTIMONIALS VIEW
# ==========================================
elif view_option == "Testimonials":
    st.write("Customer feedback filtered by rating.")
    testimonials_list = data.get("testimonials", [])
    
    if testimonials_list:
        df_testi = pd.DataFrame(testimonials_list)
        if "rating" in df_testi.columns:
            if selected_rating_filter != "All":
                star_num = int(selected_rating_filter.split()[0])
                filtered_df = df_testi[df_testi['rating'] == star_num]
            else:
                filtered_df = df_testi
            
            st.metric("Testimonials Visible", len(filtered_df))
            
            if not filtered_df.empty:
                filtered_df["rating_display"] = filtered_df["rating"].apply(lambda x: "⭐" * int(x))
                st.dataframe(
                    filtered_df[["rating_display", "text"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "rating_display": st.column_config.TextColumn("Rating", width="small"),
                        "text": "Testimonial"
                    }
                )
            else:
                st.info(f"No testimonials found with {selected_rating_filter}.")
        else:
            st.dataframe(df_testi, use_container_width=True, hide_index=True)
    else:
        st.warning("No testimonials found.")

# ==========================================
# C) REVIEWS VIEW (SENTIMENT + VIZUALIZACIJA)
# ==========================================
elif view_option == "Reviews":
    st.write("Filter reviews by month (Year 2023) and analyze sentiment.")
    
    reviews_list = data.get("reviews", [])
    
    if reviews_list:
        df_reviews = pd.DataFrame(reviews_list)
        df_reviews['date_obj'] = pd.to_datetime(df_reviews['date'], errors='coerce')
        df_reviews = df_reviews.dropna(subset=['date_obj'])
        
        # Slider
        months = ["January", "February", "March", "April", "May", "June", 
                  "July", "August", "September", "October", "November", "December"]
        selected_month_name = st.select_slider("Select a month in 2023:", options=months)
        month_map = {m: i+1 for i, m in enumerate(months)}
        selected_month_num = month_map[selected_month_name]
        
        # Filter
        filtered_df = df_reviews[
            (df_reviews['date_obj'].dt.month == selected_month_num) & 
            (df_reviews['date_obj'].dt.year == 2023)
        ].copy()
        
        col1, col2 = st.columns(2)
        col1.metric("Selected Month", selected_month_name)
        col2.metric("Reviews Found", len(filtered_df))
        
        if not filtered_df.empty:
            
            st.markdown("### 🤖 AI Sentiment Analysis")
            
            with st.spinner('Calculating sentiment...'):
                try:
                    sentiment_pipeline = load_sentiment_model()
                    texts_to_analyze = filtered_df['text'].tolist()
                    results = sentiment_pipeline(texts_to_analyze)
                    
                    # Shranimo rezultate
                    filtered_df['sentiment_label'] = [r['label'] for r in results]
                    # Shranimo score kot float za izračune
                    filtered_df['sentiment_score'] = [r['score'] for r in results]
                    
                    # --- 4. VIZUALIZACIJA (ALTAIR CHART) ---
                    st.markdown("#### Sentiment Distribution")
                    
                    # Pripravimo podatke za graf:
                    # Grupiramo po Labeli (POSITIVE/NEGATIVE) in izračunamo:
                    # - count() -> število reviewjev
                    # - mean() -> povprečni score
                    chart_data = filtered_df.groupby('sentiment_label').agg(
                        count=('sentiment_label', 'count'),
                        avg_confidence=('sentiment_score', 'mean')
                    ).reset_index()
                    
                    # Pretvorimo confidence v procente za lepši izpis
                    chart_data['avg_confidence_pct'] = (chart_data['avg_confidence'] * 100).round(1)

                    # Ustvarimo Altair Chart
                    # Barva: Zelena za POSITIVE, Rdeča za NEGATIVE
                    base = alt.Chart(chart_data).encode(
                        x=alt.X('sentiment_label', axis=alt.Axis(title="Sentiment")),
                        y=alt.Y('count', axis=alt.Axis(title="Number of Reviews")),
                        color=alt.Color('sentiment_label', 
                                      scale=alt.Scale(domain=['POSITIVE', 'NEGATIVE'], range=['#28a745', '#dc3545']),
                                      legend=None),
                        tooltip=[
                            alt.Tooltip('sentiment_label', title="Sentiment"),
                            alt.Tooltip('count', title="Count"),
                            alt.Tooltip('avg_confidence_pct', title="Avg Confidence (%)")
                        ]
                    )

                    bar_chart = base.mark_bar().properties(height=300)
                    
                    # Dodamo tekst nad stolpce (število)
                    text = base.mark_text(dy=-10, color='white').encode(text='count')
                    
                    st.altair_chart(bar_chart + text, use_container_width=True)
                    
                    # --- PRIKAZ TABELE ---
                    st.markdown("#### Detailed Data")
                    
                    def get_sentiment_icon(label):
                        return "🟢 Positive" if label == "POSITIVE" else "🔴 Negative"
                    
                    filtered_df['Sentiment'] = filtered_df['sentiment_label'].apply(get_sentiment_icon)
                    
                    # Formatiramo score za prikaz v tabeli (npr. "98.5%")
                    filtered_df['Confidence'] = (filtered_df['sentiment_score'] * 100).apply(lambda x: f"{x:.1f}%")

                    if "rating" in filtered_df.columns:
                        filtered_df["Stars"] = filtered_df["rating"].apply(lambda x: "⭐" * int(x))
                        display_cols = ["date", "Stars", "Sentiment", "Confidence", "text"]
                    else:
                        display_cols = ["date", "Sentiment", "Confidence", "text"]
                    
                    st.dataframe(
                        filtered_df[display_cols],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "date": st.column_config.TextColumn("Date", width="small"),
                            "Stars": st.column_config.TextColumn("Rating", width="small"),
                            "Sentiment": st.column_config.TextColumn("AI Sentiment", width="medium"),
                            "Confidence": st.column_config.TextColumn("AI Confidence", width="small"),
                            "text": "Review Content"
                        }
                    )
                    
                except Exception as e:
                    st.error(f"Error during analysis: {e}")
                    st.dataframe(filtered_df)
        else:
            st.info(f"No reviews found for {selected_month_name} 2023.")
    else:
        st.warning("No reviews found.")
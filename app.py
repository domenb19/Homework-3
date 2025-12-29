import streamlit as st
import pandas as pd
import json
import os
import altair as alt

# --- KONFIGURACIJA STRANI ---
st.set_page_config(
    page_title="Web Scraping & AI Analytics",
    page_icon="📊",
    layout="wide"
)

# --- FUNKCIJA ZA NALAGANJE PODATKOV ---
@st.cache_data
def load_data():
    # Preverimo, če datoteka obstaja
    if not os.path.exists('final_data.json'):
        st.error("Datoteka 'final_data.json' manjka! Prepričaj se, da si jo naložil na GitHub.")
        return None, None, None

    with open('final_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Priprava DataFrame-ov
    df_reviews = pd.DataFrame(data['reviews'])
    df_products = pd.DataFrame(data['products'])
    df_testimonials = pd.DataFrame(data['testimonials'])

    # Pretvorba datumov v datetime objekte
    if 'date' in df_reviews.columns:
        df_reviews['date'] = pd.to_datetime(df_reviews['date'])
        # Dodamo stolpec z imenom meseca za lažje filtriranje
        df_reviews['month_name'] = df_reviews['date'].dt.month_name()

    return df_reviews, df_products, df_testimonials

# Naloži podatke
df_reviews, df_products, df_testimonials = load_data()

# Če ni podatkov, ustavi izvajanje
if df_reviews is None:
    st.stop()

# --- SIDEBAR NAVIGACIJA ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Products", "Testimonials", "Reviews"])

st.sidebar.markdown("---")
st.sidebar.info(
    """
    **Project Info:**
    \nWeb Scraping & Sentiment Analysis
    \nAuthor: Domen Belantič
    """
)

# --- 1. STRAN: PRODUCTS ---
if page == "Products":
    st.title("🛍️ Products Overview")
    st.write("List of all scraped products from the store.")
    
    st.metric("Total Products", len(df_products))
    
    st.dataframe(
        df_products,
        use_container_width=True,
        column_config={
            "price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "image": st.column_config.ImageColumn("Product Image")
        }
    )

# --- 2. STRAN: TESTIMONIALS ---
elif page == "Testimonials":
    st.title("💬 Testimonials Overview")
    st.write("Customer feedback filtered by rating.")
    
    # Filter po zvezdicah
    rating_filter = st.radio(
        "Filter Testimonials by Rating:",
        ["All", "5 Stars", "4 Stars", "3 Stars", "2 Stars", "1 Star"],
        horizontal=True
    )
    
    filtered_testimonials = df_testimonials.copy()
    
    if rating_filter != "All":
        stars = int(rating_filter.split()[0])
        filtered_testimonials = filtered_testimonials[filtered_testimonials['rating'] == stars]
    
    st.metric("Testimonials Visible", len(filtered_testimonials))
    
    # Prikaz tabele
    filtered_testimonials['Visual Rating'] = filtered_testimonials['rating'].apply(lambda x: '⭐' * int(x))
    
    # Dinamično iskanje imena stolpca z besedilom
    text_col = 'text' if 'text' in filtered_testimonials.columns else 'content'
    
    st.dataframe(
        filtered_testimonials[['Visual Rating', text_col]],
        use_container_width=True,
        column_config={
            "Visual Rating": "Rating",
            text_col: "Testimonial"
        }
    )

# --- 3. STRAN: REVIEWS ---
elif page == "Reviews":
    # --- NASLOV ---
    st.title("📊 Reviews Overview")
    st.write("Filter reviews by month (Year 2023) and analyze sentiment.")
    
    # Ročno definiran vrstni red mesecev
    months_order = [
        "January", "February", "March", "April", "May", "June", 
        "July", "August", "September", "October", "November", "December"
    ]
    
    # Slider
    selected_month = st.select_slider("Select a month in 2023:", options=months_order)
    
    # Filtriraj podatke
    monthly_data = df_reviews[df_reviews['month_name'] == selected_month]
    
    st.markdown("---")
    
    # Metrike
    col1, col2 = st.columns(2)
    col1.metric("Selected Month", selected_month)
    col1.metric("Reviews Found", len(monthly_data))
    
    # --- POGOJ: Če obstajajo podatki za ta mesec ---
    if not monthly_data.empty:
        
        # --- WORD CLOUD ---
        st.subheader("☁️ Word Cloud")
        image_path = os.path.join("wc_images", f"{selected_month}.png")
        if os.path.exists(image_path):
            st.image(image_path, caption=f"Most frequent words in {selected_month}", use_container_width=True)
        else:
            st.info(f"No generated Word Cloud image found for {selected_month}.")
            
        # --- SENTIMENT CHART ---
        st.subheader("📊 Sentiment Distribution")
        
        if 'sentiment' in monthly_data.columns:
            chart = alt.Chart(monthly_data).mark_bar().encode(
                x=alt.X('sentiment', axis=alt.Axis(title='Sentiment')),
                y=alt.Y('count()', axis=alt.Axis(title='Number of Reviews')),
                color=alt.Color('sentiment', scale=alt.Scale(domain=['POSITIVE', 'NEGATIVE'], range=['#28a745', '#dc3545'])),
                tooltip=[
                    alt.Tooltip('sentiment', title='Sentiment'),
                    alt.Tooltip('count()', title='Count'),
                    # POPRAVEK TUKAJ: format='.1%' spremeni 0.99 v 99.0%
                    alt.Tooltip('mean(confidence)', title='Avg Confidence', format='.1%')
                ]
            ).properties(height=400).interactive()
            st.altair_chart(chart, use_container_width=True)

        # --- DATA TABLE ---
        st.subheader("📝 Detailed Data")
        
        # Kopija za prikaz
        display_df = monthly_data.copy()
        
        # 1. Formatiranje Zvezdic
        display_df['Rating'] = display_df['rating'].apply(lambda x: '⭐' * int(x) if pd.notnull(x) else 'N/A')
        
        # 2. Formatiranje Sentimenta (Pika + Tekst)
        def format_sentiment(val):
            if str(val).upper() == 'POSITIVE':
                return "🟢 Positive"
            elif str(val).upper() == 'NEGATIVE':
                return "🔴 Negative"
            return val

        display_df['AI Sentiment'] = display_df['sentiment'].apply(format_sentiment)
        
        # 3. Formatiranje Confidence v procente za tabelo
        display_df['AI Confidence'] = (display_df['confidence'] * 100).map('{:.1f}%'.format)

        # Ugotovimo ime stolpca z besedilom
        text_col_rev = 'content' if 'content' in display_df.columns else 'text'
        
        # Prikaz tabele
        st.dataframe(
            display_df[['date', 'Rating', 'AI Sentiment', 'AI Confidence', text_col_rev]],
            use_container_width=True,
            column_config={
                "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                "AI Sentiment": st.column_config.TextColumn("AI Sentiment"),
                "AI Confidence": st.column_config.TextColumn("AI Confidence"),
                text_col_rev: "Review Content"
            }
        )

    else:
        st.warning(f"⚠️ No reviews found for {selected_month}.")
        st.write("Try selecting a different month where reviews exist.")
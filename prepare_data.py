import pandas as pd
import json
import os
from transformers import pipeline
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# 1. Naloži podatke
print("Nalagam scraped_data.json ...")
with open('scraped_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

df = pd.DataFrame(data['reviews'])

# --- POPRAVEK: Uporabimo stolpec 'text', ki prihaja iz scraperja ---
# Preverimo za vsak slučaj
if 'text' not in df.columns:
    print("NAPAKA: Stolpec 'text' ne obstaja. Preveri scraper output.")
    exit()

# 2. AI Sentiment Analysis (Lokalno)
print("Začenjam analizo sentimenta (to lahko traja minuto ali dve)...")
# Uporabimo CPU (device=-1) ali GPU (device=0), če je na voljo, ampak za ta model je CPU ok
sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

def get_sentiment(text):
    # Skrajšamo tekst na 512 znakov, ker model ne prenese več
    # Uporabimo 'text' argument
    result = sentiment_pipeline(text[:512])[0]
    return result['label'], result['score']

# Uporabi funkcijo na stolpcu 'text'
df[['sentiment', 'confidence']] = df['text'].apply(lambda x: pd.Series(get_sentiment(x)))

print("Sentiment analiza končana.")

# 3. Generiranje Word Cloud slik za vsak mesec (Lokalno)
print("Generiram Word Cloud slike...")
if not os.path.exists('wc_images'):
    os.makedirs('wc_images')

# Pretvori datum v datetime
# Scraper ima formate kot "September 24, 2023", pandas to zna prebrati
df['date'] = pd.to_datetime(df['date'])
months = df['date'].dt.month_name().unique()

for month in months:
    # Filtriramo po mesecu in združimo vsa besedila (stolpec 'text')
    monthly_text = " ".join(df[df['date'].dt.month_name() == month]['text'])
    
    if monthly_text:
        # Generiraj oblak
        wc = WordCloud(width=800, height=400, background_color='white').generate(monthly_text)
        
        # Shrani sliko
        plt.figure(figsize=(10, 5))
        plt.imshow(wc, interpolation='bilinear')
        plt.axis('off')
        save_path = f"wc_images/{month}.png"
        plt.savefig(save_path, format='png', bbox_inches='tight')
        plt.close()
        print(f" -> Shranjena slika: {save_path}")

# 4. PRIPRAVA ZA APP.PY (Preimenovanje)
# Da ne rabimo spreminjati app.py, preimenujemo 'text' v 'content' tukaj
df = df.rename(columns={'text': 'content'})

# Pretvori nazaj v string za JSON (datumov JSON ne mara)
df['date'] = df['date'].dt.strftime('%Y-%m-%d')

# Posodobi glavni slovar
data['reviews'] = df.to_dict(orient='records')

# Shrani nov JSON
with open('final_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4)

print("\n✅ Vse končano! Ustvarjena datoteka 'final_data.json' in mapa 'wc_images'.")
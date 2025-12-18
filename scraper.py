import json
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def count_yellow_stars(element):
    """Prešteje rumene zvezdice (SVG)."""
    try:
        stars = element.find_elements(By.XPATH, ".//*[local-name()='path' and @fill='#ffce31']")
        return len(stars)
    except:
        return 0

def scrape_final_v14_year_limit():
    print("🚀 Zaganjam V14 Scraper (Leto 2023 limit)...")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    wait = WebDriverWait(driver, 10)
    
    data = {
        "products": [],
        "testimonials": [],
        "reviews": []
    }

    # ==========================================
    # 1. PRODUCTS
    # ==========================================
    print("\n📦 Zbiram: PRODUCTS...")
    page = 1
    while True:
        driver.get(f"https://web-scraping.dev/products?page={page}")
        time.sleep(1)
        prods = driver.find_elements(By.CSS_SELECTOR, "div.product-item, div[class*='product']")
        
        if not prods: break
            
        added = 0
        for p in prods:
            try:
                ft = p.text.split('\n')
                title = ft[0]
                match = re.search(r'[$€£]?\s*\d+\.\d{2}', p.text)
                price = match.group(0).strip() if match else "N/A"
                if price == "N/A":
                    nums = re.findall(r'\d+\.\d+', p.text)
                    if nums: price = f"${nums[-1]}".strip()
                
                if not any(e['title'] == title for e in data['products']):
                    if len(title) > 2 and title != "Log in":
                        data["products"].append({"title": title, "price": price})
                        added += 1
            except: continue
        
        print(f"      Stran {page}: +{added} novih.")
        if added == 0: break
        page += 1

    # ==========================================
    # 2. REVIEWS (STOP PRI 2022)
    # ==========================================
    print("\n⭐ Zbiram: REVIEWS (Samo 2023 in novejše)...")
    driver.get("https://web-scraping.dev/reviews")
    time.sleep(2)
    
    stop_scraping_reviews = False # Zastavica za konec
    
    while not stop_scraping_reviews:
        # 1. Poberi trenutne
        reviews = driver.find_elements(By.CLASS_NAME, "review")
        
        for review in reviews:
            try:
                lines = review.text.strip().split('\n')
                
                # --- LOGIKA ZA DATUM ---
                # Poiščemo vrstico, ki vsebuje letnico (4 številke)
                date_str = None
                found_year = 0
                
                for line in lines:
                    year_match = re.search(r'(20\d\d)', line)
                    if year_match:
                        found_year = int(year_match.group(1))
                        date_str = line
                        break
                
                # ČE NI DATUMA: Preskoči (ne izmišljuj si 2023-01-01)
                if not date_str:
                    continue

                # ČE JE STARO (2022 ali manj): USTAVI VSE!
                if found_year < 2023:
                    print(f"      ⛔ Našel staro mnenje iz leta {found_year}. Ustavljam zbiranje reviewjev.")
                    stop_scraping_reviews = True
                    break # Prekine for zanko
                
                # Če je 2023 ali 2024 -> Shrani
                text = max(lines, key=len)
                rating = count_yellow_stars(review) or 5
                
                if not any(r['text'] == text for r in data['reviews']):
                    data["reviews"].append({
                        "date": date_str,
                        "text": text,
                        "rating": rating
                    })
            except: continue
            
        if stop_scraping_reviews:
            break # Prekine while zanko

        print(f"   -> Skupaj v bazi: {len(data['reviews'])}")
        
        # 2. Klikni Load More (če nismo ustavili)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        try:
            load_more_btn = driver.find_element(By.ID, "page-load-more")
            if not load_more_btn.is_displayed(): break
            
            count_before = len(reviews)
            driver.execute_script("arguments[0].click();", load_more_btn)
            
            try:
                wait.until(lambda d: len(d.find_elements(By.CLASS_NAME, "review")) > count_before)
                time.sleep(1)
            except:
                print("      Ni novih elementov. Konec.")
                break
        except:
            print("      Gumba ni več. Konec.")
            break

    # ==========================================
    # 3. TESTIMONIALS
    # ==========================================
    print("\n💬 Zbiram: TESTIMONIALS...")
    driver.get("https://web-scraping.dev/testimonials")
    time.sleep(2)
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        cards = driver.find_elements(By.CSS_SELECTOR, "div.testimonial-item, div[class*='testimonial']")
        if not cards: cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'testimonial')]")
        
        for card in cards:
            try:
                ft = card.text.strip()
                if "Take a look" in ft or "collection" in ft or len(ft) > 400 or len(ft) < 10: continue
                ct = ft.replace("\n", " ").strip()
                if not any(t['text'] == ct for t in data['testimonials']):
                    rating = count_yellow_stars(card) or 5
                    data["testimonials"].append({"text": ct, "rating": rating})
            except: continue
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height: break
        last_height = new_height
        print(f"   -> Skupaj testimonials: {len(data['testimonials'])}")

    driver.quit()
    return data

if __name__ == "__main__":
    final_data = scrape_final_v14_year_limit()
    
    with open("scraped_data.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=4, ensure_ascii=False)
        
    print(f"\n✅ KONČANO!")
    print(f"📦 Products: {len(final_data['products'])}")
    print(f"⭐ Reviews: {len(final_data['reviews'])} (Samo 2023+)")
    print(f"💬 Testimonials: {len(final_data['testimonials'])}")
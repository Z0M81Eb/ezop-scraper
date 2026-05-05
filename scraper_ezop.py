import cloudscraper
from bs4 import BeautifulSoup
import csv
import re
import time

print("Inicijalizacija scrapera za Ezop Antikvarijat...", flush=True)

def ocisti_sliku(url):
    if not url: return ""
    # Briše oznake dimenzija poput -300x300, -600x600 itd. prije ekstenzije
    return re.sub(r'-\d+x\d+(?=\.[a-zA-Z]+$)', '', url)

def pretvori_ocjenu(ezop_ocjena):
    try:
        ocjena = int(ezop_ocjena)
        mape = {10: "M", 9: "NM", 8: "VG+", 7: "VG", 6: "G+", 5: "G"}
        return mape.get(ocjena, "F/P")
    except: return ""

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

csv_filename = 'ezop_ploce.csv'
sve_ploce = {} # Koristimo rječnik s URL-om kao ključem radi lakšeg osvježavanja

# === SKENIRANJE ===
page = 1
print("\n=== POKREĆEM SKENIRANJE I OSVJEŽAVANJE ===", flush=True)

while True:
    url = 'https://ezop-antikvarijat.hr/kategorija/glazba/' if page == 1 else f'https://ezop-antikvarijat.hr/kategorija/glazba/page/{page}/'
    print(f"Skeniram stranicu {page}...", flush=True)
    
    try:
        response = scraper.get(url, timeout=30)
        if response.status_code == 404: break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('div.arhiva-all-info')
        
        if not items: break
            
        for item in items:
            try:
                a_tag = item.find('a')
                product_url = a_tag['href'] if a_tag and a_tag.has_attr('href') else ""
                if not product_url: continue
                
                is_vinyl = False
                s_medija, s_omota = "", ""
                
                # Provjera je li vinil i kakvo je stanje
                info_list = item.select('ul.arhiva-cf li')
                for li in info_list:
                    t = li.text.lower()
                    if "medij" in t and "gramofon" in t: is_vinyl = True
                    if "stanje omota" in t:
                        span = li.select_one('span.red')
                        if span: s_omota = pretvori_ocjenu(span.text.strip())
                    if "stanje medija" in t:
                        span = li.select_one('span.red')
                        if span: s_medija = pretvori_ocjenu(span.text.strip())
                
                if not is_vinyl: continue

                # Naslov i cijena
                art_el = item.select_one('h2.woocommerce-loop-product__title')
                alb_el = item.select_one('p.product_author_black')
                title = f"{art_el.text.strip()} - {alb_el.text.strip()}" if art_el and alb_el else ""
                
                e, c = item.select_one('span.big'), item.select_one('span.small_price')
                price = f"{e.text.strip()},{c.text.strip()}" if e and c else ""

                # Slike - Čišćenje za punu rezoluciju
                parent_block = item.find_parent('li')
                img_tag = parent_block.select_one('img') if parent_block else item.select_one('img')
                raw_image_url = ""
                if img_tag:
                    raw_image_url = img_tag.get('src', '')
                
                final_image_url = ocisti_sliku(raw_image_url)
                
                if title and price:
                    # Spremamo u rječnik. Ako link već postoji, novi podaci će pregaziti stare (osvježavanje)
                    sve_ploce[product_url] = [title, price, product_url, final_image_url, s_medija, s_omota, "Vinil"]
                    
            except: continue
            
        page += 1
        time.sleep(1)
        
    except Exception as e:
        print(f"Greška: {e}")
        break

# === SPREMANJE ===
if sve_ploce:
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
        writer.writerows(sve_ploce.values())
    print(f"\nGotovo. Ukupno obrađeno {len(sve_ploce)} ploča s ažurnim podacima.")

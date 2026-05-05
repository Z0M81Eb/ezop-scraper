import cloudscraper
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from bs4 import BeautifulSoup
import csv
import os
import time
import re

# Prilagođeni SSL adapter koji dopušta starije TLS verzije na novim sustavima
class TlsAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.set_ciphers('DEFAULT@SECLEVEL=1') # Spuštamo sigurnost na razinu 1 za ovaj proces
        kwargs['ssl_context'] = context
        return super(TlsAdapter, self).init_poolmanager(*args, **kwargs)

print(f"Trenutna radna mapa: {os.getcwd()}", flush=True)
print("ANALOGNI ZVUK: Pokrećem Cloudscraper s Custom SSL adapterom...", flush=True)

csv_filename = 'analognizvuk_ploce.csv'
sve_ploce = {}
vidjeni_linkovi = set()
uspjesno_skenirano = True

# === 1. UČITAVANJE STARE BAZE ===
if os.path.exists(csv_filename):
    with open(csv_filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) >= 7:
                sve_ploce[row[2]] = row
    print(f"Učitano {len(sve_ploce)} postojećih ploča.", flush=True)

# Inicijalizacija scrapera i montiranje SSL adaptera
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)
scraper.mount('https://', TlsAdapter())

# Probijanje zaštite
print("\nProbijanje početne zaštite (Naslovnica)...", flush=True)
try:
    scraper.get("https://analogni-zvuk.hr/", timeout=30)
    time.sleep(5)
    print("Prolaz odobren.", flush=True)
except Exception as e:
    print(f"Upozorenje: {e}", flush=True)

# === 2. SKENIRANJE (Filteri) ===
filteri = [
    {'url_param': 'novo', 'stanje': 'Novo'},
    {'url_param': 'rabljeno', 'stanje': 'Second Hand'},
    {'url_param': 'raritet', 'stanje': 'Second Hand'}
]

for f_data in filteri:
    param = f_data['url_param']
    stanje_kataloga = f_data['stanje']
    current_page_num = 1
    
    print(f"\n--- Skeniram: {param.upper()} ---", flush=True)

    while True:
        cat_url = f'https://analogni-zvuk.hr/product-category/gramofonske-ploce/'
        if current_page_num > 1:
            cat_url += f'page/{current_page_num}/'
        cat_url += f'?filter_stanje={param}'
        
        print(f"Stranica {current_page_num}...", end=" ", flush=True)
        
        try:
            response = scraper.get(cat_url, timeout=30)
            if response.status_code == 404:
                print("-> Kraj.", flush=True)
                break
            
            soup = BeautifulSoup(response.text, 'html.parser')
            products = soup.find_all('li', class_='product')
            
            if not products:
                print("-> Nema više proizvoda.", flush=True)
                break
                
            dodano = 0
            for prod in products:
                if 'outofstock' in prod.get('class', []): continue
                
                a_tag = prod.find('a', class_='woocommerce-LoopProduct-link')
                if not a_tag: continue
                
                link = a_tag['href']
                vidjeni_linkovi.add(link)
                
                title = prod.find(class_='woocommerce-loop-product__title').text.strip()
                
                # Cijena
                price = ""
                price_wrap = prod.find(class_='price')
                if price_wrap:
                    bdi = price_wrap.find('bdi')
                    if bdi: price = bdi.text.replace('€', '').replace(',', '.').replace('\xa0', '').strip()

                # Slika
                img_url = ""
                img_el = prod.find('img')
                if img_el:
                    img_url = img_el.get('data-src') or img_el.get('src') or ""
                
                if title and price:
                    sve_ploce[link] = [title, price, link, img_url, stanje_kataloga, stanje_kataloga, "Vinil"]
                    dodano += 1
            
            print(f"-> OK ({dodano})", flush=True)
            current_page_num += 1
            time.sleep(1)
            
        except Exception as e:
            print(f"Greška: {e}", flush=True)
            uspjesno_skenirano = False
            break

# === 3. BRISANJE I SPREMANJE ===
if uspjesno_skenirano:
    sve_ploce = {k: v for k, v in sve_ploce.items() if k in vidjeni_linkovi}
    
with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(sve_ploce.values())

print(f"\nGotovo! Ukupno: {len(sve_ploce)}", flush=True)

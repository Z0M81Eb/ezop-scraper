import requests
from bs4 import BeautifulSoup
import csv
import time
import re

print("Učitavam biblioteke i pripremam radnike za Analogni Zvuk...", flush=True)

csv_filename = 'analognizvuk_ploce.csv'
konacna_baza = []

# Maska Chrome preglednika
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'hr,en-US;q=0.7,en;q=0.3'
})

# Konfiguracija WooCommerce filtera i stanja koje ćemo upisati
filteri = [
    {'url_param': 'novo', 'stanje': 'Novo'},
    {'url_param': 'rabljeno', 'stanje': 'Second Hand'},
    {'url_param': 'raritet', 'stanje': 'Second Hand'}
]

print("\n=== POKREĆEM GRID SWEEP ZA ANALOGNI ZVUK ===", flush=True)

for f in filteri:
    page = 1
    zaustavi = False
    param = f['url_param']
    stanje_kataloga = f['stanje']
    
    print(f"\n--- Skeniram arhivu: {param.upper()} (Sustav piše: {stanje_kataloga}) ---", flush=True)

    while not zaustavi:
        # Standardna WooCommerce paginacija s GET parametrima za filter
        if page == 1:
            cat_url = f'https://analogni-zvuk.hr/product-category/gramofonske-ploce/?filter_stanje={param}'
        else:
            cat_url = f'https://analogni-zvuk.hr/product-category/gramofonske-ploce/page/{page}/?filter_stanje={param}'
        
        try:
            print(f"Stranica {page}...", end=" ", flush=True)
            res = session.get(cat_url, timeout=15)
            
            # Provjera kraja
            if res.status_code == 404:
                print(f"-> Kraj arhive za ovaj filter.", flush=True)
                break
            elif res.status_code != 200:
                print(f" [GREŠKA SERVERA: {res.status_code}]", flush=True)
                time.sleep(5)
                page += 1
                continue
                
            soup = BeautifulSoup(res.text, 'html.parser')
            products = soup.find_all('li', class_='product')
            
            if not products:
                print(f"-> Nema proizvoda na stranici. Prelazim na idući filter.", flush=True)
                break
                
            dodano_na_stranici = 0
            
            for prod in products:
                # 1. KONTROLA ZALIHE
                klase = prod.get('class', [])
                if 'outofstock' in klase:
                    continue
                    
                # 2. DOHVAT LINKA I NASLOVA
                a_tag = prod.find('a', class_='woocommerce-LoopProduct-link')
                if not a_tag:
                    a_tag = prod.find('a')
                    
                if not a_tag or not a_tag.has_attr('href'):
                    continue
                
                link = a_tag['href']
                
                title_el = prod.find(class_='woocommerce-loop-product__title')
                title = title_el.text.strip() if title_el else "Nepoznat naslov"
                
                # 3. DOHVAT CIJENE
                price = ""
                price_wrap = prod.find(class_='price')
                if price_wrap:
                    ins = price_wrap.find('ins')
                    target = ins if ins else price_wrap
                    bdi = target.find('bdi')
                    
                    if bdi:
                        price = bdi.text.replace('€', '').replace('\xa0', '').strip()
                    else:
                        price = target.text.replace('€', '').replace('\xa0', '').strip()
                
                # 4. DOHVAT ORIGINALNE SLIKE (Uklanjanje -250x250)
                img_url = ""
                img_el = prod.find('img')
                if img_el:
                    src = img_el.get('data-src') or img_el.get('src')
                    if src:
                        img_url = re.sub(r'-\d+x\d+(\.\w+)$', r'\1', src)
                
                if title and link and price:
                    konacna_baza.append([title, price, link, img_url, stanje_kataloga, stanje_kataloga, "Vinil"])
                    dodano_na_stranici += 1
                    
            print(f"-> Dodano: {dodano_na_stranici}", flush=True)
            
            page += 1
            time.sleep(1) # Sigurnosna pauza
            
        except Exception as e:
            print(f"\n[GREŠKA] Problem pri obradi: {e}", flush=True)
            time.sleep(5)
            page += 1

print(f"\n=== ZAVRŠENO SKENIRANJE. SPREMAM BAZU ===", flush=True)

with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(konacna_baza)

print(f"Uspješno generiran '{csv_filename}'. Ukupno spremno za uvoz: {len(konacna_baza)} aktivnih ploča.", flush=True)

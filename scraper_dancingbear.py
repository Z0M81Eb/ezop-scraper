import requests
from bs4 import BeautifulSoup
import csv
import time
import os

print("Učitavam biblioteke i pripremam radnike...", flush=True)

csv_filename = 'dancingbear_ploce.csv'
konacna_baza = []
page = 1
zaustavi = False

# Umjesto nestabilnog cloudscrapera, koristimo brzi 'requests' s maskom pravog Chrome preglednika
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'hr,en-US;q=0.7,en;q=0.3'
})

print("\n=== POKREĆEM GRID SWEEP (SIGURNO SKENIRANJE KATALOGA) ===", flush=True)
print("Ovaj proces ignorira rasprodane artikle u startu i ne opterećuje server.\n", flush=True)

while not zaustavi:
    cat_url = 'https://dancingbear.hr/kategorija-proizvoda/vinyl/' if page == 1 else f'https://dancingbear.hr/kategorija-proizvoda/vinyl/page/{page}/'
    
    try:
        print(f"Skeniram: {cat_url} ...", end=" ", flush=True)
        res = session.get(cat_url, timeout=15)
        
        if res.status_code == 404:
            print(f"\n[INFO] Došli smo do kraja kataloga (Stranica {page} ne postoji).", flush=True)
            break
        elif res.status_code != 200:
            print(f" [GREŠKA SERVERA: {res.status_code}]", flush=True)
            time.sleep(5)
            page += 1
            continue
            
        soup = BeautifulSoup(res.text, 'html.parser')
        products = soup.find_all('li', class_='product')
        
        if not products:
            print(f"\n[INFO] Stranica {page} nema proizvoda. Završavam skeniranje.", flush=True)
            break
            
        dodano_na_stranici = 0
        
        for prod in products:
            # 1. KONTROLA ZALIHE
            klase = prod.get('class', [])
            if 'outofstock' in klase:
                continue
                
            # 2. DOHVAT LINKA
            a_tag = prod.find('a', class_='woocommerce-LoopProduct-link')
            if not a_tag:
                a_tag = prod.find('a')
                
            if not a_tag or not a_tag.has_attr('href'):
                continue
            
            link = a_tag['href']
            
            # 3. DOHVAT NASLOVA
            title_el = prod.find(class_='woocommerce-loop-product__title')
            title = title_el.text.strip() if title_el else "Nepoznat naslov"
            
            # 4. DOHVAT SLIKE
            img_el = prod.find('img')
            img_url = ""
            if img_el:
                if img_el.has_attr('data-src'):
                    img_url = img_el['data-src']
                elif img_el.has_attr('src'):
                    img_url = img_el['src']
            
            # 5. DOHVAT CIJENE
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
            
            if title and link and price:
                konacna_baza.append([title, price, link, img_url, "Sealed", "Sealed", "Novo"])
                dodano_na_stranici += 1
                
        print(f"-> Dodano dostupnih: {dodano_na_stranici}", flush=True)
        
        page += 1
        time.sleep(1) # Prisebno pauziramo 1 sekundu
        
    except Exception as e:
        print(f"\n[GREŠKA] Problem pri obradi stranice {page}: {e}", flush=True)
        time.sleep(5)
        page += 1

print(f"\n=== ZAVRŠENO SKENIRANJE. SPREMAM BAZU ===", flush=True)

with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(konacna_baza)

print(f"Uspješno generiran '{csv_filename}'. Spremljeno {len(konacna_baza)} aktivnih ploča.", flush=True)

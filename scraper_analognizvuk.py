from curl_cffi import requests
from bs4 import BeautifulSoup
import csv
import os
import time
import re

print(f"Trenutna radna mapa: {os.getcwd()}", flush=True)
print("ANALOGNI ZVUK: Pokrećem curl_cffi TLS spoofing sustav...", flush=True)

csv_filename = 'analognizvuk_ploce.csv'
sve_ploce = {}
vidjeni_linkovi = set()
uspjesno_skenirano = True

filteri = [
    {'url_param': 'novo', 'stanje': 'Novo'},
    {'url_param': 'rabljeno', 'stanje': 'Second Hand'},
    {'url_param': 'raritet', 'stanje': 'Second Hand'}
]

# === 1. UČITAVANJE STARE BAZE ===
if os.path.exists(csv_filename):
    with open(csv_filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) >= 7:
                sve_ploce[row[2]] = row
    print(f"Učitano {len(sve_ploce)} postojećih ploča iz memorije.", flush=True)
else:
    print("CSV datoteka ne postoji, krećem ispočetka.", flush=True)

# Inicijalizacija sesije koja savršeno simulira Chrome otisak mreže
session = requests.Session(impersonate="chrome116")

# === 2. SKENIRANJE I OSVJEŽAVANJE ===
for f_data in filteri:
    param = f_data['url_param']
    stanje_kataloga = f_data['stanje']
    current_page_num = 1
    zaustavi = False

    print(f"\n--- Skeniram arhivu: {param.upper()} ---", flush=True)

    while not zaustavi:
        if current_page_num == 1:
            cat_url = f'https://analogni-zvuk.hr/product-category/gramofonske-ploce/?filter_stanje={param}'
        else:
            cat_url = f'https://analogni-zvuk.hr/product-category/gramofonske-ploce/page/{current_page_num}/?filter_stanje={param}'
        
        print(f"Stranica {current_page_num}...", end=" ", flush=True)
        
        try:
            # Šaljemo upit kroz lažni Chrome TLS
            response = session.get(cat_url, timeout=30)
            
            if response.status_code == 404:
                print("-> Kraj arhive za ovaj filter.", flush=True)
                break
            elif response.status_code != 200:
                print(f"-> [GREŠKA SERVERA: {response.status_code}]", flush=True)
                uspjesno_skenirano = False
                zaustavi = True
                break
                
            soup = BeautifulSoup(response.content, 'html.parser')
            products = soup.find_all('li', class_='product')
            
            if not products:
                print("-> Nema proizvoda na stranici. Kraj.", flush=True)
                break
                
            dodano_na_stranici = 0
            
            for prod in products:
                klase = prod.get('class', [])
                if 'outofstock' in klase:
                    continue
                    
                a_tag = prod.find('a', class_='woocommerce-LoopProduct-link') or prod.find('a')
                if not a_tag or not a_tag.has_attr('href'):
                    continue
                    
                link = a_tag['href']
                vidjeni_linkovi.add(link)
                
                title_el = prod.find(class_='woocommerce-loop-product__title')
                title = title_el.text.replace('&#8211;', '-').strip() if title_el else "Nepoznat naslov"
                
                price = ""
                price_wrap = prod.find(class_='price')
                if price_wrap:
                    ins = price_wrap.find('ins')
                    target = ins if ins else price_wrap
                    bdi = target.find('bdi')
                    if bdi:
                        price = bdi.text.replace('€', '').replace(',', '.').replace('\xa0', '').strip()
                    else:
                        price = target.text.replace('€', '').replace(',', '.').replace('\xa0', '').strip()
                        
                img_url = ""
                img_el = prod.find('img')
                if img_el:
                    src = img_el.get('data-src') or img_el.get('src')
                    if src:
                        img_url = re.sub(r'-\d+x\d+(\.\w+)$', r'\1', src)
                        
                if title and link and price:
                    sve_ploce[link] = [title, price, link, img_url, stanje_kataloga, stanje_kataloga, "Vinil"]
                    dodano_na_stranici += 1
                    
            print(f"-> Dodano/Ažurirano: {dodano_na_stranici}", flush=True)
            current_page_num += 1
            time.sleep(1)
            
        except Exception as e:
            print(f"\n[GREŠKA MREŽE] {e}", flush=True)
            uspjesno_skenirano = False
            break

# === 3. LOGIKA BRISANJA PRODANIH ===
if uspjesno_skenirano:
    pocetni_broj = len(sve_ploce)
    sve_ploce = {k: v for k, v in sve_ploce.items() if k in vidjeni_linkovi}
    obrisano = pocetni_broj - len(sve_ploce)
    print(f"\nAnaliza završena. Obrisano {obrisano} prodanih ploča koje više ne postoje na webshopu.", flush=True)
else:
    print("\nUPOZORENJE: Skripta nije završila čisto zbog greške ili prekida veze. Preskačem brisanje starih ploča radi sigurnosti baze.", flush=True)

# === 4. SPREMANJE ===
if sve_ploce:
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
        writer.writerows(sve_ploce.values())
    print(f"Završeno! Baza je ažurna i sadrži {len(sve_ploce)} ploča.", flush=True)
else:
    print("Nema podataka za spremanje.", flush=True)

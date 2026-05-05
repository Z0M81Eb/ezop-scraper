import cloudscraper
from bs4 import BeautifulSoup
import csv
import os
import time

print(f"Trenutna radna mapa: {os.getcwd()}", flush=True)
print("KARMA VINIL: Pokrećem redovito skeniranje, osvježavanje i čišćenje baze...", flush=True)

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

base_url = "https://www.karmavinil.com"
csv_filename = 'karma_ploce.csv'

sve_ploce = {}
vidjeni_linkovi = set()
uspjesno_skenirano = False

# === 1. UČITAVANJE STARE BAZE ===
if os.path.exists(csv_filename):
    with open(csv_filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None) # preskoči zaglavlje
        for row in reader:
            if len(row) >= 7:
                sve_ploce[row[2]] = row # URL je ključ
    print(f"Učitano {len(sve_ploce)} postojećih ploča iz memorije.", flush=True)
else:
    print("CSV datoteka ne postoji, krećem ispočetka.", flush=True)

# === 2. SKENIRANJE I OSVJEŽAVANJE ===
page = 1
zaustavi = False

while not zaustavi:
    url = f"{base_url}/vinyl-ploce?page_size=64&sort=3&page_number={page}&f=1&min_price=1&max_price=1000"
    print(f"Skeniram stranicu {page}...", end=" ", flush=True)
    
    try:
        res = scraper.get(url, timeout=20)
        
        # Karma ponekad vrati preusmjeravanje ili 404 kada dođe do kraja
        if res.status_code != 200:
            print(f"-> Kraj arhive (Kod: {res.status_code}).", flush=True)
            uspjesno_skenirano = True
            break
            
        soup = BeautifulSoup(res.text, 'html.parser')
        product_links = soup.find_all('a', class_='product-click')
        
        if not product_links:
            print("-> Nema više proizvoda. Kraj arhive.", flush=True)
            uspjesno_skenirano = True
            break
            
        novih_na_stranici = 0
        
        for a_tag in product_links:
            # 1. LINK
            rel_url = a_tag.get('href', '')
            if not rel_url: continue
            full_url = base_url + rel_url if not rel_url.startswith('http') else rel_url
            
            # Bilježimo da smo vidjeli ovaj link danas (bitno za brisanje)
            vidjeni_linkovi.add(full_url)
            
            # 2. NASLOV
            title = a_tag.get('title', '').strip()
            if not title: title = a_tag.text.strip()
            
            # 3. KONTEJNER
            container = a_tag.parent
            for _ in range(5):
                if container and container.find(class_='price-value'):
                    break
                if container: container = container.parent
                    
            if not container: continue
                
            # 4. SLIKA
            image_url = ""
            img_tag = container.find('img')
            if img_tag:
                img_src = img_tag.get('data-src') or img_tag.get('data-original') or img_tag.get('src') or ""
                if img_src and not img_src.startswith('data:image') and 'placeholder' not in img_src.lower():
                    image_url = base_url + img_src if not img_src.startswith('http') else img_src
            
            # 5. CIJENA
            price = ""
            price_span = container.find(class_='price-value')
            if price_span:
                strong = price_span.find('strong')
                if strong: price = strong.text.replace('€', '').replace(',', '.').strip()
                else: price = price_span.text.replace('€', '').replace(',', '.').strip()
                
            # 6. STANJE I FORMAT
            stanje_medija = "Rabljeno"
            stanje_omota = "Rabljeno"
            tip_artikla = "Vinil ploča" 
            
            sve_vrijednosti = container.find_all('div', class_=lambda c: c and 'text-right' in c)
            
            for div in sve_vrijednosti:
                tekst = div.text.strip().upper()
                if tekst in ['LP', '7"', '12"', '2LP', 'CD', 'MC', '10"']:
                    tip_artikla = tekst
                elif '/' in tekst or tekst in ['M', 'NM', 'EX', 'VG+', 'VG', 'G', 'F', 'P', 'SS']:
                    if '/' in tekst:
                        dijelovi = tekst.split('/')
                        stanje_medija = dijelovi[0].strip()
                        stanje_omota = dijelovi[1].strip() if len(dijelovi) > 1 else stanje_medija
                    else:
                        stanje_medija = tekst
                        stanje_omota = tekst
            
            if title and price:
                # Osvježavamo ili dodajemo ploču u rječnik
                sve_ploce[full_url] = [title, price, full_url, image_url, stanje_medija, stanje_omota, tip_artikla]
                novih_na_stranici += 1
                
        print(f"-> Pronađeno/ažurirano ploča: {novih_na_stranici}", flush=True)
        page += 1
        time.sleep(1) 
        
    except Exception as e:
        print(f"\nGreška na stranici {page}: {e}", flush=True)
        break

# === 3. LOGIKA BRISANJA PRODANIH ===
if uspjesno_skenirano:
    pocetni_broj = len(sve_ploce)
    # Zadržavamo samo one ploče čiji su linkovi primijećeni tijekom današnjeg skeniranja
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

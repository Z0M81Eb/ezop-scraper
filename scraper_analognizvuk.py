import requests
import csv
import time
import re

print("Spajam se na Analogni Zvuk API...", flush=True)

csv_filename = 'analognizvuk_ploce.csv'
konacna_baza = []
page = 1

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
})

print("\n=== POKREĆEM BRZI API SWEEP (ANALOGNI ZVUK) ===", flush=True)

while True:
    api_url = f"https://analogni-zvuk.hr/wp-json/wc/store/products?page={page}&per_page=100"
    
    try:
        print(f"Skidam stranicu {page}...", end=" ", flush=True)
        res = session.get(api_url, timeout=15)
        
        if res.status_code == 400:
            print("-> Došli smo do kraja baze.", flush=True)
            break
        elif res.status_code != 200:
            print(f" [GREŠKA: {res.status_code}]", flush=True)
            break
            
        data = res.json()
        
        if not data:
            print("-> Nema više proizvoda.", flush=True)
            break
            
        dodano_na_stranici = 0
        
        for item in data:
            # 1. KONTROLA ZALIHE
            if not item.get('is_in_stock', False):
                continue
                
            # 2. KATEGORIJA (Filtriramo samo ploče/vinile)
            kategorije = [kat.get('name', '').lower() for kat in item.get('categories', [])]
            if not any('plo' in k or 'vinil' in k or 'vinyl' in k for k in kategorije):
                continue
                
            # 3. OSNOVNI PODACI
            title = item.get('name', 'Nepoznat naslov').replace('&#8211;', '-').strip()
            link = item.get('permalink', '')
            
            # Cijena u Store API-ju
            prices = item.get('prices', {})
            raw_price = prices.get('price', '0')
            minor_unit = prices.get('currency_minor_unit', 2)
            try:
                price_val = float(raw_price) / (10 ** minor_unit)
                price = f"{price_val:.2f}"
            except:
                price = "0.00"
                
            # Slika
            images = item.get('images', [])
            img_url = images[0].get('src', '') if images else ''
            
            # 4. IZVLAČENJE STANJA IZ OPISA
            opis = item.get('description', '') + " " + item.get('short_description', '')
            opis_clean = re.sub(r'<[^>]+>', ' ', opis)
            
            # Po defaultu je sve iz Analognog Zvuka "Second Hand", osim ako u imenu/opisu piše "Novo"
            stanje_kataloga = "Second Hand"
            if "novo" in opis_clean.lower() or "novo" in title.lower():
                stanje_kataloga = "Novo"
            
            stanje_ploce = stanje_kataloga
            stanje_omota = stanje_kataloga
            
            # Traženje specifične ocjene (VG+, NM...) iz teksta
            match_ploca = re.search(r'Stanje plo[čc]e:\s*([A-Za-z0-9\+\-\/]+)', opis_clean, re.IGNORECASE)
            if match_ploca:
                stanje_ploce = match_ploca.group(1).strip()
                
            match_omot = re.search(r'Stanje omota:\s*([A-Za-z0-9\+\-\/]+)', opis_clean, re.IGNORECASE)
            if match_omot:
                stanje_omota = match_omot.group(1).strip()
                
            if title and link and price != "0.00":
                konacna_baza.append([title, price, link, img_url, stanje_ploce, stanje_omota, "Vinil"])
                dodano_na_stranici += 1
                
        print(f"-> Dodano ploča: {dodano_na_stranici}", flush=True)
        
        page += 1
        time.sleep(0.5)
        
    except Exception as e:
        print(f"\n[GREŠKA] Problem pri obradi API-ja: {e}", flush=True)
        time.sleep(5)
        page += 1

print(f"\n=== ZAVRŠENO SKENIRANJE. SPREMAM BAZU ===", flush=True)

with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(konacna_baza)

print(f"Uspješno generiran '{csv_filename}'. Ukupno spremno za uvoz: {len(konacna_baza)} aktivnih ploča.", flush=True)

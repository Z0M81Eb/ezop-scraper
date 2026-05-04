import requests
import csv
import time
import html

print("Inicijalizacija API sustava za Dancing Bear...", flush=True)

csv_filename = 'dancingbear_ploce.csv'
konacna_baza = []
page = 1
per_page = 100 

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
})

print("\n=== POKREĆEM BRZI API SWEEP (DANCING BEAR) ===", flush=True)

while True:
    api_url = f"https://dancingbear.hr/wp-json/wc/store/products?page={page}&per_page={per_page}"
    
    try:
        print(f"Preuzimam API paket {page}...", end=" ", flush=True)
        res = session.get(api_url, timeout=20)
        
        if res.status_code == 400:
            print("-> Kraj baze dosegnut.", flush=True)
            break
        elif res.status_code != 200:
            print(f" [GREŠKA SERVERA: {res.status_code}]", flush=True)
            break
            
        data = res.json()
        
        if not data:
            print("-> Paket prazan, završavam.", flush=True)
            break
            
        dodano_na_stranici = 0
        
        for item in data:
            if not item.get('is_in_stock', False):
                continue
                
            kategorije = [k.get('slug', '').lower() for k in item.get('categories', [])]
            if not any('vinyl' in k or 'vinil' in k or 'ploce' in k or 'ploca' in k for k in kategorije):
                continue
                
            title = html.unescape(item.get('name', 'Nepoznat naslov')).strip()
            link = item.get('permalink', '')
            
            prices = item.get('prices', {})
            raw_price = prices.get('price', '0')
            minor_unit = prices.get('currency_minor_unit', 2)
            try:
                price_val = float(raw_price) / (10 ** minor_unit)
                price = f"{price_val:.2f}"
            except:
                price = "0.00"
                
            if price == "0.00":
                continue
                
            # --- ISPRAVAK SLIKE ---
            images = item.get('images', [])
            img_url = ""
            if images and isinstance(images, list):
                # Vučemo 'src' iz prvog objekta u listi
                img_url = images[0].get('src', '') 
            
            stanje = "Novo"
            tip = "Vinil"
            
            # --- ISPRAVAN REDOSLIJED ZAPISIVANJA (Važno!) ---
            # Mora odgovarati zaglavlju: Naslov, Cijena, URL_Proizvoda, URL_Slike, Stanje_Medija, Stanje_Omota, Tip_Artikla
            konacna_baza.append([title, price, link, img_url, stanje, stanje, tip])
            dodano_na_stranici += 1
            
        print(f"-> Uspješno izvučeno vinila: {dodano_na_stranici}", flush=True)
        
        page += 1
        time.sleep(0.5)
        
    except Exception as e:
        print(f"\n[GREŠKA KONEKCIJE] {e}", flush=True)
        time.sleep(5)

print(f"\n=== ZAVRŠENO API SKENIRANJE. SPREMAM BAZU ===", flush=True)

with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    # Ovaj redoslijed mora savršeno odgovarati `konacna_baza.append` redu iznad
    writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(konacna_baza)

print(f"Uspješno generiran '{csv_filename}'. Ukupno spremno za Agregator: {len(konacna_baza)} aktivnih ploča.", flush=True)

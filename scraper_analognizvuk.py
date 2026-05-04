from playwright.sync_api import sync_playwright
import csv
import time
import re

print("Inicijalizacija hibridnog sustava (In-Page Fetch) za Analogni Zvuk...", flush=True)

csv_filename = 'analognizvuk_ploce.csv'
konacna_baza = []

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("1. Otvaram naslovnicu kako bih riješio Cloudflare zaštitu...", flush=True)
        try:
            page.goto("https://analogni-zvuk.hr/", wait_until="networkidle", timeout=60000)
            # Produžujemo pauzu na 10 sekundi za sigurnu provjeru
            print("-> Naslovnica učitana. Čekam 10 sekundi za potpunu CF verifikaciju...", flush=True)
            time.sleep(10) 
        except Exception as e:
            print(f"-> Upozorenje pri učitavanju naslovnice: {e}", flush=True)

        print("\n2. Pokrećem In-Page API skeniranje unutar provjerenog preglednika...", flush=True)

        page_num = 1
        while True:
            api_url = f"https://analogni-zvuk.hr/wp-json/wc/store/products?page={page_num}&per_page=100"
            
            try:
                print(f"Skidam stranicu {page_num}...", end=" ", flush=True)
                
                # KLJUČNA PROMJENA: JS kod se izvršava unutar samog preglednika
                # Cloudflare ovo tretira kao legitiman AJAX poziv same stranice
                js_code = f"""
                async () => {{
                    try {{
                        const response = await fetch('{api_url}');
                        if (!response.ok) {{
                            return {{ status: response.status, data: null }};
                        }}
                        const data = await response.json();
                        return {{ status: response.status, data: data }};
                    }} catch (e) {{
                        return {{ status: 500, data: null, error: e.toString() }};
                    }}
                }}
                """
                
                result = page.evaluate(js_code)
                status = result.get('status')
                data = result.get('data')
                
                if status == 400:
                    print("-> Došli smo do kraja baze.", flush=True)
                    break
                elif status != 200:
                    print(f" [GREŠKA SERVERA: {status}]", flush=True)
                    break
                    
                if not data:
                    print("-> Nema više proizvoda.", flush=True)
                    break
                    
                dodano_na_stranici = 0
                
                for item in data:
                    # 1. KONTROLA ZALIHE
                    if not item.get('is_in_stock', False):
                        continue
                        
                    # 2. KATEGORIJA
                    kategorije = [kat.get('name', '').lower() for kat in item.get('categories', [])]
                    if not any('plo' in k or 'vinil' in k or 'vinyl' in k for k in kategorije):
                        continue
                        
                    # 3. OSNOVNI PODACI
                    title = item.get('name', 'Nepoznat naslov').replace('&#8211;', '-').strip()
                    link = item.get('permalink', '')
                    
                    prices = item.get('prices', {})
                    raw_price = prices.get('price', '0')
                    minor_unit = prices.get('currency_minor_unit', 2)
                    try:
                        price_val = float(raw_price) / (10 ** minor_unit)
                        price = f"{price_val:.2f}"
                    except:
                        price = "0.00"
                        
                    images = item.get('images', [])
                    img_url = images[0].get('src', '') if images else ''
                    
                    # 4. IZVLAČENJE STANJA
                    opis = item.get('description', '') + " " + item.get('short_description', '')
                    opis_clean = re.sub(r'<[^>]+>', ' ', opis)
                    
                    stanje_kataloga = "Second Hand"
                    if "novo" in opis_clean.lower() or "novo" in title.lower():
                        stanje_kataloga = "Novo"
                    
                    stanje_ploce = stanje_kataloga
                    stanje_omota = stanje_kataloga
                    
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
                
                page_num += 1
                time.sleep(1) # Prisebna pauza između JS poziva
                
            except Exception as e:
                print(f"\n[GREŠKA] Problem pri obradi: {e}", flush=True)
                time.sleep(5)
                page_num += 1

        browser.close()

run()

print(f"\n=== ZAVRŠENO SKENIRANJE. SPREMAM BAZU ===", flush=True)

with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(konacna_baza)

print(f"Uspješno generiran '{csv_filename}'. Ukupno spremno za uvoz: {len(konacna_baza)} aktivnih ploča.", flush=True)

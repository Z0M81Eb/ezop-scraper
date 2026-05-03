from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import csv
import time
import re

print("Učitavam biblioteke i pripremam radnike za Analogni Zvuk...", flush=True)

csv_filename = 'analognizvuk_ploce.csv'
konacna_baza = []

filteri = [
    {'url_param': 'novo', 'stanje': 'Novo'},
    {'url_param': 'rabljeno', 'stanje': 'Second Hand'},
    {'url_param': 'raritet', 'stanje': 'Second Hand'}
]

print("\n=== POKREĆEM GRID SWEEP ZA ANALOGNI ZVUK (PLAYWRIGHT ENGINE) ===", flush=True)

def run():
    with sync_playwright() as p:
        # Pokrećemo headless Chromium preglednik
        browser = p.chromium.launch(headless=True)
        # Dodajemo masku i agenta kako bi izbjegli osnovne detekcije
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for f in filteri:
            current_page_num = 1
            zaustavi = False
            param = f['url_param']
            stanje_kataloga = f['stanje']
            
            print(f"\n--- Skeniram arhivu: {param.upper()} (Sustav piše: {stanje_kataloga}) ---", flush=True)

            while not zaustavi:
                if current_page_num == 1:
                    cat_url = f'https://analogni-zvuk.hr/product-category/gramofonske-ploce/?filter_stanje={param}'
                else:
                    cat_url = f'https://analogni-zvuk.hr/product-category/gramofonske-ploce/page/{current_page_num}/?filter_stanje={param}'
                
                try:
                    print(f"Stranica {current_page_num}...", end=" ", flush=True)
                    
                    # Playwright čeka da se stranica u potpunosti učita i svi skriptovi izvrše
                    response = page.goto(cat_url, wait_until="networkidle", timeout=30000)
                    
                    if response is None:
                        print(f" [GREŠKA: Nema odgovora]", flush=True)
                        time.sleep(5)
                        current_page_num += 1
                        continue

                    # Playwright nam omogućava da vidimo pravi status kod, nakon Cloudflare-a
                    if response.status == 404:
                         print(f"-> Kraj arhive za ovaj filter.", flush=True)
                         break
                    elif response.status not in (200, 304):
                         print(f" [GREŠKA SERVERA: {response.status}]", flush=True)
                         time.sleep(5)
                         current_page_num += 1
                         continue

                    # Ako smo dobili 200, vadimo čisti HTML kod
                    html_content = page.content()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    products = soup.find_all('li', class_='product')
                    
                    if not products:
                        print(f"-> Nema proizvoda na stranici. Prelazim na idući filter.", flush=True)
                        break
                        
                    dodano_na_stranici = 0
                    
                    for prod in products:
                        klase = prod.get('class', [])
                        if 'outofstock' in klase:
                            continue
                            
                        a_tag = prod.find('a', class_='woocommerce-LoopProduct-link')
                        if not a_tag:
                            a_tag = prod.find('a')
                            
                        if not a_tag or not a_tag.has_attr('href'):
                            continue
                        
                        link = a_tag['href']
                        
                        title_el = prod.find(class_='woocommerce-loop-product__title')
                        title = title_el.text.strip() if title_el else "Nepoznat naslov"
                        
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
                    
                    current_page_num += 1
                    time.sleep(1) # Prisebna pauza
                    
                except Exception as e:
                    print(f"\n[GREŠKA] Problem pri obradi: {e}", flush=True)
                    time.sleep(5)
                    current_page_num += 1

        browser.close()

run()

print(f"\n=== ZAVRŠENO SKENIRANJE. SPREMAM BAZU ===", flush=True)

with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(konacna_baza)

print(f"Uspješno generiran '{csv_filename}'. Ukupno spremno za uvoz: {len(konacna_baza)} aktivnih ploča.", flush=True)

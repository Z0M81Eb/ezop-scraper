import cloudscraper
from bs4 import BeautifulSoup
import csv
import os
import time

print(f"Trenutna radna mapa: {os.getcwd()}")
print("KARMA VINIL: Pokrećem 'Dan 0' paginacijski uvoz baze...")

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

base_url = "https://www.karmavinil.com"
csv_filename = 'karma_ploce.csv'
sve_ploce = []
uhvaceni_linkovi = set()

page = 1
zaustavi = False

while not zaustavi:
    url = f"{base_url}/vinyl-ploce?page={page}"
    print(f"Skeniram stranicu {page}...")
    
    try:
        res = scraper.get(url, timeout=15)
        if res.status_code != 200:
            print("Kraj stranica (greška servera).")
            break
            
        soup = BeautifulSoup(res.text, 'html.parser')
        product_links = soup.find_all('a', class_='product-click')
        
        if not product_links:
            print("Nema više proizvoda na ovoj stranici. Završavam!")
            break
            
        novih_na_stranici = 0
        
        for a_tag in product_links:
            # 1. LINK
            rel_url = a_tag.get('href', '')
            if not rel_url: continue
            full_url = base_url + rel_url if not rel_url.startswith('http') else rel_url
            
            if full_url in uhvaceni_linkovi:
                continue
                
            uhvaceni_linkovi.add(full_url)
            novih_na_stranici += 1
            
            # 2. NASLOV
            title = a_tag.get('title', '').strip()
            if not title: title = a_tag.text.strip()
            
            # 3. KONTEJNER (Tražimo okvir koji drži i sliku i cijenu)
            container = a_tag.parent
            for _ in range(5):
                if container and container.find(class_='price-value'):
                    break
                if container: container = container.parent
                    
            if not container: continue
                
            # 4. SLIKA
            image_url = ""
            img_tag = container.find('img')
            if img_tag and img_tag.has_attr('src'):
                img_src = img_tag['src']
                image_url = base_url + img_src if not img_src.startswith('http') else img_src
                
            # 5. CIJENA
            price = ""
            price_span = container.find(class_='price-value')
            if price_span:
                strong = price_span.find('strong')
                if strong: price = strong.text.replace('€', '').replace(',', '.').strip()
                else: price = price_span.text.replace('€', '').replace(',', '.').strip()
                    
            # 6. STANJE OMOTA I MEDIJA (iz tvog HTML-a: <div class="value text-right" title="EX/EX">EX/EX</div>)
            stanje_medija = "Rabljeno"
            stanje_omota = "Rabljeno"
            
            stanje_div = container.find('div', class_=lambda c: c and 'text-right' in c)
            if stanje_div:
                stanje_tekst = stanje_div.text.strip()
                if '/' in stanje_tekst:
                    dijelovi = stanje_tekst.split('/')
                    stanje_medija = dijelovi[0].strip()
                    stanje_omota = dijelovi[1].strip() if len(dijelovi) > 1 else stanje_medija
                else:
                    stanje_medija = stanje_tekst
                    stanje_omota = stanje_tekst
                    
            if title and price:
                sve_ploce.append([title, price, full_url, image_url, stanje_medija, stanje_omota, "Rabljeno"])
                
        if novih_na_stranici == 0:
            print("\nDetektirano ponavljanje proizvoda. Došli smo do kraja asortimana. Prekidam!")
            zaustavi = True
            break
            
        print(f" -> Stranica {page} obrađena. Ukupno izvučeno do sada: {len(sve_ploce)}")
        page += 1
        time.sleep(1) # Prijateljski delay
        
    except Exception as e:
        print(f"Greška na stranici {page}: {e}")
        break

# === SPREMANJE ===
with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(sve_ploce)

print(f"\nGOTOVO! Baza uspješno inicijalizirana s {len(sve_ploce)} ploča.")

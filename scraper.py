import cloudscraper
from bs4 import BeautifulSoup
import csv
import time

scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

all_products = []
page = 1

while True:
    if page == 1:
        url = 'https://ezop-antikvarijat.hr/kategorija/glazba/'
    else:
        url = f'https://ezop-antikvarijat.hr/kategorija/glazba/page/{page}/'
        
    print(f"Skeniram stranicu {page}...")
    
    try:
        response = scraper.get(url, timeout=30)
        
        if response.status_code == 404:
            print("Došli smo do kraja kataloga (Error 404).")
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('div.arhiva-all-info')
        
        if len(items) == 0:
            print("Nema više proizvoda. Završavam pretraživanje.")
            break
            
        for item in items:
            try:
                # NOVI KORAK: Provjera je li proizvod zaista gramofonska ploča
                is_vinyl = False
                for li in item.select('li'):
                    if "Medij:" in li.text and "Gramofonska ploča" in li.text:
                        is_vinyl = True
                        break
                
                # Ako nije gramofonska ploča, odmah preskačemo na idući proizvod
                if not is_vinyl:
                    continue

                artist_el = item.select_one('h2.woocommerce-loop-product__title')
                artist = artist_el.text.strip() if artist_el else ""
                
                album_el = item.select_one('p.product_author_black')
                album = album_el.text.strip() if album_el else ""
                
                full_title = f"{artist} - {album}" if album else artist
                
                euro_el = item.select_one('span.big')
                cent_el = item.select_one('span.small_price')
                
                if euro_el and cent_el:
                    price = f"{euro_el.text.strip()},{cent_el.text.strip()} €"
                elif euro_el:
                    price = f"{euro_el.text.strip()} €"
                else:
                    price = ""
                
                if full_title and price:
                    all_products.append([full_title, price])
                    
            except Exception as e:
                continue
                
        print(f"Stranica {page} obrađena. Trenutno uhvaćeno: {len(all_products)} gramofonskih ploča.")
        page += 1
        
        time.sleep(2)
        
    except Exception as e:
        print(f"Greška na stranici {page}: {e}. Prekidam rad.")
        break

with open('ezop_ploce.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena'])
    writer.writerows(all_products)
    print(f"GOTOVO! Uspješno filtrirano i spremljeno ukupno {len(all_products)} isključivo gramofonskih ploča.")

import cloudscraper
from bs4 import BeautifulSoup
import csv
import time

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

all_products = []
page = 1

# OGRANIČENO NA 5 STRANICA ZA TEST
while page <= 5:
    url = f'https://dancingbear.hr/kategorija-proizvoda/vinyl/page/{page}/'
    print(f"Skeniram Dancing Bear stranicu {page}...")
    
    try:
        response = scraper.get(url, timeout=30)
        
        if response.status_code == 404: 
            print("Kraj kataloga detektiran.")
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('div.product-inner')
        
        if len(items) == 0: 
            break
            
        for item in items:
            try:
                title_el = item.select_one('li.title h2')
                full_title = title_el.text.strip() if title_el else ""
                
                price_el = item.select_one('span.woocommerce-Price-amount bdi')
                if price_el:
                    price = price_el.text.replace('€', '').replace('\xa0', '').strip()
                else:
                    price = ""
                
                if full_title and price:
                    stanje_medija = "Sealed"
                    stanje_omota = "Sealed"
                    tip_artikla = "Novo"
                    
                    all_products.append([full_title, price, stanje_medija, stanje_omota, tip_artikla])
                    
            except Exception as e:
                continue
                
        print(f"Stranica {page} obrađena. Trenutno uhvaćeno: {len(all_products)} ploča.")
        page += 1
        
        time.sleep(2)
        
    except Exception as e:
        print(f"Greška na stranici {page}: {e}")
        break

with open('dancingbear_ploce.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(all_products)
    print("TEST GOTOV! CSV je spreman.")

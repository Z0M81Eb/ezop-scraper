import cloudscraper
from bs4 import BeautifulSoup
import csv
import time

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

all_products = []
page = 1

while True:
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
                title_el = item.select_one('li.title h2 a')
                full_title = title_el.text.strip() if title_el else ""
                
                product_url = title_el['href'] if title_el and title_el.has_attr('href') else ""
                
                img_el = item.select_one('div.woo-entry-image img')
                image_url = img_el['src'] if img_el and img_el.has_attr('src') else ""
                
                price_el = item.select_one('span.woocommerce-Price-amount bdi')
                if price_el:
                    price = price_el.text.replace('€', '').replace('\xa0', '').strip()
                else:
                    price = ""
                
                if full_title and price:
                    # Struktura: Naslov, Cijena, URL_Proizvoda, URL_Slike, Stanje_Medija, Stanje_Omota, Tip_Artikla
                    all_products.append([
                        full_title, price, product_url, image_url, "Sealed", "Sealed", "Novo"
                    ])
                    
            except Exception as e:
                continue
                
        print(f"Stranica {page} obrađena. Uhvaćeno: {len(all_products)} ploča.")
        page += 1
        time.sleep(2)
        
    except Exception as e:
        break

with open('dancingbear_ploce.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(all_products)
    print("Dancing Bear GOTOV!")

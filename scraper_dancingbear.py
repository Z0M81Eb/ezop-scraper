import cloudscraper
from bs4 import BeautifulSoup
import csv
import time

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

all_products = []
page = 1

# OGRANIČENO NA 5 STRANICA ZA TEST NOVIH POLJA
while page <= 5:
    url = f'https://dancingbear.hr/kategorija-proizvoda/vinyl/page/{page}/'
    print(f"Skeniram Dancing Bear stranicu {page}...")
    
    try:
        response = scraper.get(url, timeout=30)
        if response.status_code == 404: break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('div.product-inner')
        
        if len(items) == 0: break
            
        for item in items:
            try:
                # 1. Naslov
                title_el = item.select_one('li.title h2 a')
                full_title = title_el.text.strip() if title_el else ""
                
                # 2. Link proizvoda (URL)
                product_url = title_el['href'] if title_el and title_el.has_attr('href') else ""
                
                # 3. Link slike (Za FIFU dodatak)
                img_el = item.select_one('div.woo-entry-image img')
                image_url = img_el['src'] if img_el and img_el.has_attr('src') else ""
                
                # 4. Cijena
                price_el = item.select_one('span.woocommerce-Price-amount bdi')
                if price_el:
                    price = price_el.text.replace('€', '').replace('\xa0', '').strip()
                else:
                    price = ""
                
                if full_title and price:
                    # Spremamo sve podatke u identičnom redoslijedu
                    all_products.append([
                        full_title, 
                        price, 
                        product_url, 
                        image_url, 
                        "Sealed", 
                        "Sealed", 
                        "Novo"
                    ])
                    
            except Exception as e:
                continue
                
        print(f"Stranica {page} obrađena. Uhvaćeno: {len(all_products)} ploča.")
        page += 1
        time.sleep(2)
        
    except Exception as e:
        break

# Zapisujemo CSV sa svim potrebnim kolonama
with open('dancingbear_ploce.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(all_products)
    print("TEST USPJEŠAN! Provjeri datoteku za nove linkove.")

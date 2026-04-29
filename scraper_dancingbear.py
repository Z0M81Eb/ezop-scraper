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
        # Ako server javi da stranica ne postoji, došli smo do kraja
        if response.status_code == 404: 
            print("Kraj kataloga detektiran (404).")
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('div.product-inner')
        
        # Ako je stranica učitana, ali na njoj nema proizvoda, također smo na kraju
        if len(items) == 0: 
            print("Nema više proizvoda na stranici, završavam skeniranje.")
            break
            
        for item in items:
            try:
                title_el = item.select_one('li.title h2 a')
                full_title = title_el.text.strip() if title_el else ""
                
                product_url = title_el['href'] if title_el and title_el.has_attr('href') else ""
                
                img_el = item.select_one('div.woo-entry-image img')
                image_url = ""
                
                if img_el:
                    # 1. Prvo provjeravamo data atribute (zaštita od Lazy Loada)
                    for attr in ['data-src', 'data-lazy-src']:
                        if img_el.has_attr(attr) and 'placeholder' not in img_el[attr]:
                            image_url = img_el[attr]
                            break
                    
                    # 2. Ako nema u data atributima, gledamo srcset
                    if not image_url and img_el.has_attr('srcset'):
                        srcset_links = img_el['srcset'].split(',')
                        if srcset_links:
                            first_link = srcset_links[0].strip().split(' ')[0]
                            if 'placeholder' not in first_link:
                                image_url = first_link
                    
                    # 3. Na kraju gledamo standardni src, samo ako NIJE placeholder
                    if not image_url and img_el.has_attr('src'):
                        if 'placeholder' not in img_el['src']:
                            image_url = img_el['src']

                price_el = item.select_one('span.woocommerce-Price-amount bdi')
                if price_el:
                    price = price_el.text.replace('€', '').replace('\xa0', '').strip()
                else:
                    price = ""
                
                if full_title and price:
                    all_products.append([
                        full_title, price, product_url, image_url, "Sealed", "Sealed", "Novo"
                    ])
                    
            except Exception as e:
                continue
                
        print(f"Stranica {page} obrađena. Ukupno uhvaćeno do sada: {len(all_products)} ploča.")
        page += 1
        time.sleep(2) # Pauza da ne preopteretimo njihov server
        
    except Exception as e:
        print(f"Došlo je do greške u spajanju: {e}")
        break

with open('dancingbear_ploce.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(all_products)
    print("Dancing Bear GOTOV! Spreman za uvoz u Agregator.")

import cloudscraper
from bs4 import BeautifulSoup
import csv

url = 'https://ezop-antikvarijat.hr/kategorija/glazba/'

scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

try:
    response = scraper.get(url, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    products = []
    
    # Sada gađamo točno onaj glavni kontejner koji drži cijelu ploču
    items = soup.select('div.arhiva-all-info')
    
    for item in items:
        try:
            # Tražimo izvođača (h2)
            artist_el = item.select_one('h2.woocommerce-loop-product__title')
            artist = artist_el.text.strip() if artist_el else ""
            
            # Tražimo naziv albuma (p)
            album_el = item.select_one('p.product_author_black')
            album = album_el.text.strip() if album_el else ""
            
            # Spajamo ih crticom kako bi lijepo izgledalo u WP-u
            full_title = f"{artist} - {album}" if album else artist
            
            # Tražimo cijenu (spajamo eure i cente)
            euro_el = item.select_one('span.big')
            cent_el = item.select_one('span.small_price')
            
            if euro_el and cent_el:
                price = f"{euro_el.text.strip()},{cent_el.text.strip()} €"
            elif euro_el:
                price = f"{euro_el.text.strip()} €"
            else:
                price = ""
            
            # Ako postoji naslov i cijena, ubacujemo u listu
            if full_title and price:
                products.append([full_title, price])
                
        except Exception as e:
            continue

    # Zapisujemo rezultate
    with open('ezop_ploce.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Naslov', 'Cijena'])
        writer.writerows(products)
        print(f"Bravo! Uspješno posisano i spremljeno {len(products)} ploča.")

except Exception as e:
    print(f"Greška: {e}")

import cloudscraper
from bs4 import BeautifulSoup
import csv

# URL koji ciljamo
url = 'https://ezop-antikvarijat.hr/kategorija/glazba/'

# Inicijalizacija posebnog scrapera koji zaobilazi Cloudflare zaštitu
scraper = cloudscraper.create_scraper()
html = scraper.get(url).text
soup = BeautifulSoup(html, 'html.parser')

products = []

# Pronalazak WooCommerce proizvoda
for item in soup.select('li.product'):
    try:
        title = item.select_one('.woocommerce-loop-product__title').text.strip()
        price = item.select_one('.price').text.strip()
        products.append([title, price])
    except AttributeError:
        continue

# Zapisivanje u CSV datoteku
with open('ezop_ploce.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena'])
    writer.writerows(products)

print("Scraping završen! CSV datoteka je generirana.")

import cloudscraper
from bs4 import BeautifulSoup
import csv
import time

def pretvori_ocjenu(ezop_ocjena):
    try:
        ocjena = int(ezop_ocjena)
        if ocjena == 10: return "M"
        elif ocjena == 9: return "NM"
        elif ocjena == 8: return "VG+"
        elif ocjena == 7: return "VG"
        elif ocjena == 6: return "G+"
        elif ocjena == 5: return "G"
        else: return "F/P"
    except: return ""

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

all_products = []
page = 1

while True:
    url = 'https://ezop-antikvarijat.hr/kategorija/glazba/' if page == 1 else f'https://ezop-antikvarijat.hr/kategorija/glazba/page/{page}/'
    print(f"Skeniram Ezop stranicu {page}...")
    
    try:
        response = scraper.get(url, timeout=30)
        if response.status_code == 404: break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('div.arhiva-all-info')
        if len(items) == 0: break
            
        for item in items:
            try:
                is_vinyl = False
                s_medija, s_omota = "", ""
                
                info_list = item.select('ul.arhiva-cf li')
                for li in info_list:
                    t = li.text.lower()
                    if "medij" in t and "gramofon" in t: is_vinyl = True
                    if "stanje omota" in t:
                        span = li.select_one('span.red')
                        if span: s_omota = pretvori_ocjenu(span.text.strip())
                    if "stanje medija" in t:
                        span = li.select_one('span.red')
                        if span: s_medija = pretvori_ocjenu(span.text.strip())
                
                if not is_vinyl: continue

                art = item.select_one('h2.woocommerce-loop-product__title')
                alb = item.select_one('p.product_author_black')
                title = f"{art.text.strip()} - {alb.text.strip()}" if art and alb else ""
                
                e, c = item.select_one('span.big'), item.select_one('span.small_price')
                price = f"{e.text.strip()},{c.text.strip()}" if e and c else ""
                
                if title and price:
                    # Dodajemo "Rabljeno" na kraj za kompatibilnost
                    all_products.append([title, price, s_medija, s_omota, "Rabljeno"])
            except: continue
        page += 1
        time.sleep(2)
    except: break

with open('ezop_ploce.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(all_products)
    print("Ezop uspješno završen!")

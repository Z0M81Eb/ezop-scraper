import cloudscraper
from bs4 import BeautifulSoup
import csv
import time

# Provjerena funkcija za pretvorbu ocjena prema Goldmine standardu
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
    except:
        return ""

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

all_products = []
page = 1

# OGRANIČENO NA 5 STRANICA ZA ZADNJU VERIFIKACIJU
while page <= 5:
    url = 'https://ezop-antikvarijat.hr/kategorija/glazba/' if page == 1 else f'https://ezop-antikvarijat.hr/kategorija/glazba/page/{page}/'
    print(f"Skeniram stranicu {page}...")
    
    try:
        response = scraper.get(url, timeout=30)
        if response.status_code == 404: break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('div.arhiva-all-info')
        if len(items) == 0: break
            
        for item in items:
            try:
                is_vinyl = False
                stanje_medija = ""
                stanje_omota = ""
                
                info_list = item.select('ul.arhiva-cf li')
                for li in info_list:
                    tekst = li.text.lower()
                    
                    # Tražimo bilo koju varijantu koja sadrži 'gramofon' (ploča, singl, maxi)
                    if "medij" in tekst and "gramofon" in tekst:
                        is_vinyl = True
                    
                    if "stanje omota" in tekst:
                        ocjena_span = li.select_one('span.red')
                        if ocjena_span:
                            stanje_omota = pretvori_ocjenu(ocjena_span.text.strip())
                            
                    if "stanje medija" in tekst:
                        ocjena_span = li.select_one('span.red')
                        if ocjena_span:
                            stanje_medija = pretvori_ocjenu(ocjena_span.text.strip())
                
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
                    price = f"{euro_el.text.strip()},{cent_el.text.strip()}"
                elif euro_el:
                    price = f"{euro_el.text.strip()}"
                else:
                    price = ""
                
                if full_title and price:
                    all_products.append([full_title, price, stanje_medija, stanje_omota])
                    
            except Exception as e:
                continue
                
        print(f"Stranica {page} obrađena. Trenutno uhvaćeno: {len(all_products)} vinila.")
        page += 1
        time.sleep(2)
        
    except Exception as e:
        print(f"Greška na stranici {page}: {e}")
        break

with open('ezop_ploce.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'Stanje_Medija', 'Stanje_Omota'])
    writer.writerows(all_products)
    print("TEST USPJEŠAN! Provjeri CSV datoteku.")

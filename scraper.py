import cloudscraper
from bs4 import BeautifulSoup
import csv
import time

# Naš prevoditelj Ezop ocjena u Goldmine standard
def pretvori_ocjenu(ezop_ocjena):
    try:
        ocjena = int(ezop_ocjena)
        if ocjena == 10: return "M"
        elif ocjena == 9: return "NM"
        elif ocjena == 8: return "VG+"
        elif ocjena == 7: return "VG"
        elif ocjena == 6: return "G+"
        elif ocjena == 5: return "G"
        elif ocjena <= 4: return "F/P"
        else: return ezop_ocjena
    except:
        return ezop_ocjena # Ako nije broj, vrati originalni tekst

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

all_products = []
page = 1

# OGRANIČENO NA 5 STRANICA ZA BRZI TEST
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
                    
                    # Provjera je li ploča
                    if "medij" in tekst and "gramofonska" in tekst:
                        is_vinyl = True
                    
                    # Izvlačenje i pretvorba ocjene omota
                    if "stanje omota" in tekst:
                        ocjena_span = li.select_one('span.red')
                        if ocjena_span:
                            stanje_omota = pretvori_ocjenu(ocjena_span.text.strip())
                            
                    # Izvlačenje i pretvorba ocjene medija
                    if "stanje medija" in tekst:
                        ocjena_span = li.select_one('span.red')
                        if ocjena_span:
                            stanje_medija = pretvori_ocjenu(ocjena_span.text.strip())
                
                if not is_vinyl:
                    continue

                # Naslov
                artist_el = item.select_one('h2.woocommerce-loop-product__title')
                artist = artist_el.text.strip() if artist_el else ""
                album_el = item.select_one('p.product_author_black')
                album = album_el.text.strip() if album_el else ""
                full_title = f"{artist} - {album}" if album else artist
                
                # Cijena
                euro_el = item.select_one('span.big')
                cent_el = item.select_one('span.small_price')
                if euro_el and cent_el:
                    price = f"{euro_el.text.strip()},{cent_el.text.strip()}" # Maknuli smo € simbol jer je to bolje za WooCommerce
                elif euro_el:
                    price = f"{euro_el.text.strip()}"
                else:
                    price = ""
                
                if full_title and price:
                    # Dodajemo nova dva stupca u tablicu
                    all_products.append([full_title, price, stanje_medija, stanje_omota])
                    
            except Exception as e:
                continue
                
        print(f"Stranica {page} obrađena. Trenutno uhvaćeno: {len(all_products)} ploča.")
        page += 1
        time.sleep(2)
        
    except Exception as e:
        print(f"Greška na stranici {page}: {e}")
        break

# Zapisujemo CSV s 4 stupca
with open('ezop_ploce.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'Stanje_Medija', 'Stanje_Omota']) # Ažurirana zaglavlja
    writer.writerows(all_products)
    print("TEST GOTOV! CSV je spreman.")

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

                art_el = item.select_one('h2.woocommerce-loop-product__title')
                alb_el = item.select_one('p.product_author_black')
                title = f"{art_el.text.strip()} - {alb_el.text.strip()}" if art_el and alb_el else ""
                
                # Izvlačenje URL-a proizvoda
                a_tag = item.find('a')
                if not a_tag:
                    parent_li = item.find_parent('li')
                    a_tag = parent_li.find('a') if parent_li else None
                product_url = a_tag['href'] if a_tag and a_tag.has_attr('href') else ""
                
                # --- POPRAVLJENO IZVLAČENJE SLIKE ZA LAZY LOAD ---
                parent_block = item.find_parent('li') or item.find_parent('div') or item.parent
                img_tag = parent_block.find('img') if parent_block else item.find('img')
                
                image_url = ""
                if img_tag:
                    # 1. Pokušaj prvo naći "srcset"
                    if img_tag.has_attr('srcset'):
                        srcset_links = img_tag['srcset'].split(',')
                        if srcset_links:
                            image_url = srcset_links[0].strip().split(' ')[0]
                    
                    # 2. Ako nema srcset ili je on neobičan, pokušavamo s data-src
                    if not image_url or image_url.startswith('data:image'):
                         if img_tag.has_attr('data-src'):
                              image_url = img_tag['data-src']
                              
                    # 3. Ako i dalje nemamo dobar link, povlačimo standardni 'src'
                    if not image_url or image_url.startswith('data:image'):
                         if img_tag.has_attr('src'):
                              image_url = img_tag['src']
                              
                    # Očisti ako je neki krivi format i dalje ostao (npr. prazan SVG kod)
                    if image_url.startswith('data:image'):
                        image_url = ""
                # ------------------------------------------------
                
                # Cijena
                e, c = item.select_one('span.big'), item.select_one('span.small_price')
                price = f"{e.text.strip()},{c.text.strip()}" if e and c else ""
                
                if title and price:
                    all_products.append([
                        title, price, product_url, image_url, s_medija, s_omota, "Rabljeno"
                    ])
            except Exception as e:
                continue
                
        print(f"Stranica {page} obrađena. Uhvaćeno ukupno: {len(all_products)} ploča.")
        page += 1
        time.sleep(2)
        
    except Exception as e:
        break

with open('ezop_ploce.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(all_products)
    print("Ezop GOTOV!")

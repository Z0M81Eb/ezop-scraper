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
                
                a_tag = item.find('a')
                if not a_tag:
                    parent_li = item.find_parent('li')
                    a_tag = parent_li.find('a') if parent_li else None
                product_url = a_tag['href'] if a_tag and a_tag.has_attr('href') else ""
                
                # --- NOVI, PAMETNI SUSTAV ZA SLIKE ---
                parent_block = item.find_parent('li') or item.find_parent('div') or item.parent
                
                # SADA tražimo SVE slike unutar bloka
                img_tags = parent_block.find_all('img') if parent_block else item.find_all('img')
                
                image_url = ""
                for img in img_tags:
                    temp_url = ""
                    
                    # 1. Gledamo srcset (vučemo najbolju rezoluciju)
                    if img.has_attr('srcset'):
                        srcset_links = img['srcset'].split(',')
                        if srcset_links:
                            # Uzimamo zadnji link iz niza (jer je u WP-u obično onaj s najvećim 'w' brojem)
                            temp_url = srcset_links[-1].strip().split(' ')[0]
                    
                    # 2. Ako nema srcset, tražimo data-src
                    if not temp_url and img.has_attr('data-src'):
                        temp_url = img['data-src']
                              
                    # 3. Na kraju gledamo standardni src
                    if not temp_url and img.has_attr('src'):
                        temp_url = img['src']
                              
                    # PROVJERA: Zanemarujemo base64 i generičke Ezop ikone
                    if temp_url and not temp_url.startswith('data:image'):
                        if 'themes/ezop' not in temp_url and 'placeholder' not in temp_url.lower():
                            image_url = temp_url
                            break # Našli smo pravu sliku, možemo prekinuti petlju traženja!
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

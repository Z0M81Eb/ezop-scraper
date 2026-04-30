import cloudscraper
from bs4 import BeautifulSoup
import csv
import os
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

csv_filename = 'ezop_ploce.csv'

# === 1. UČITAJ STARU BAZU ===
old_data = []
poznati_linkovi = set()

print(f"Trenutna radna mapa: {os.getcwd()}")
if os.path.exists(csv_filename):
    with open(csv_filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if len(row) >= 7:
                old_data.append(row)
                # Čistimo link od mogućih dodataka (?kategorija=...) kako bi usporedba bila točna
                cisti_link = row[2].split('?')[0].strip('/')
                poznati_linkovi.add(cisti_link)

print(f"Učitano {len(old_data)} starih ploča iz memorije.")

# === 2. SKENIRANJE STRANICA S PAMETNIM PREKIDOM ===
novih_ploca = []
page = 1
zaustavi_skeniranje = False

while not zaustavi_skeniranje:
    url = 'https://ezop-antikvarijat.hr/kategorija/glazba/' if page == 1 else f'https://ezop-antikvarijat.hr/kategorija/glazba/page/{page}/'
    print(f"Skeniram Ezop stranicu {page}...")
    
    try:
        response = scraper.get(url, timeout=30)
        if response.status_code == 404: break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('div.arhiva-all-info')
        if len(items) == 0: break
            
        novih_na_ovoj_stranici = 0
            
        for item in items:
            try:
                # Izvlačenje URL-a
                a_tag = item.find('a')
                if not a_tag:
                    parent_li = item.find_parent('li')
                    a_tag = parent_li.find('a') if parent_li else None
                product_url = a_tag['href'] if a_tag and a_tag.has_attr('href') else ""
                
                if not product_url: continue
                
                # Usporedba sa starom bazom
                cisti_trenutni_link = product_url.split('?')[0].strip('/')
                
                if cisti_trenutni_link in poznati_linkovi:
                    # Ova ploča nam je već poznata! Preskačemo je.
                    continue
                
                # --- Ako smo došli ovdje, ploča je NOVA. Analiziramo je. ---
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
                
                # Nove slike logic
                parent_block = item.find_parent('li') or item.find_parent('div') or item.parent
                img_tags = parent_block.find_all('img') if parent_block else item.find_all('img')
                
                image_url = ""
                for img in img_tags:
                    temp_url = ""
                    if img.has_attr('srcset'):
                        srcset_links = img['srcset'].split(',')
                        if srcset_links:
                            temp_url = srcset_links[-1].strip().split(' ')[0]
                    if not temp_url and img.has_attr('data-src'): temp_url = img['data-src']
                    if not temp_url and img.has_attr('src'): temp_url = img['src']
                          
                    if temp_url and not temp_url.startswith('data:image'):
                        if 'themes/ezop' not in temp_url and 'placeholder' not in temp_url.lower():
                            image_url = temp_url
                            break
                
                # Cijena
                e, c = item.select_one('span.big'), item.select_one('span.small_price')
                price = f"{e.text.strip()},{c.text.strip()}" if e and c else ""
                
                if title and price:
                    novih_ploca.append([title, price, product_url, image_url, s_medija, s_omota, "Rabljeno"])
                    novih_na_ovoj_stranici += 1
                    print(f" -> Nova ploča dodana: {title}")
                    
            except Exception as e:
                continue
        
        # PAMETNA KOČNICA: Ako na cijeloj stranici nismo našli nijednu novu ploču (sve su već u CSV-u), prekidamo!
        if novih_na_ovoj_stranici == 0:
            print("\nNaišli smo na stare ploče. Nema više noviteta. Prekidam skeniranje!")
            zaustavi_skeniranje = True
            break
            
        page += 1
        time.sleep(1)
        
    except Exception as e:
        print(f"Greška na stranici {page}: {e}")
        break

# === 3. SPAJANJE I SPREMANJE ===
if len(novih_ploca) > 0:
    sve_ploce = novih_ploca + old_data # Nove stavljamo na vrh
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
        writer.writerows(sve_ploce)
    print(f"\nUspješno dodano {len(novih_ploca)} novih ploča u bazu!")
else:
    print("\nNema novih ploča za dodavanje. Baza je već ažurna!")

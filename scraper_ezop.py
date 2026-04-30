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
old_data = {}

# --- DIJAGNOSTIKA ZA GITHUB ACTIONS ---
print(f"Trenutna radna mapa: {os.getcwd()}")
print(f"Datoteke u mapi: {os.listdir('.')}")
# --------------------------------------

# === 1. UČITAJ STARU BAZU (Ako postoji) ===
if os.path.exists(csv_filename):
    with open(csv_filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if len(row) >= 7:
                old_data[row[2]] = row

print(f"Učitano {len(old_data)} starih ploča iz memorije.")

# === 2. POVUCI SITEMAP (Glavni indeks + Pod-sitemapi) ===
print("Skeniram glavni Ezop sitemap_index.xml...")
sitemap_urls = set()

try:
    res = scraper.get('https://ezop-antikvarijat.hr/sitemap_index.xml', timeout=30)
    # ISPRAVAK: Koristimo brzi 'xml' parser umjesto html-a
    soup = BeautifulSoup(res.content, 'xml')
    
    # Nalazimo samo linkove koji u sebi imaju 'product-sitemap'
    product_sitemaps = [loc.text for loc in soup.find_all('loc') if 'product-sitemap' in loc.text]
    print(f"Pronađeno {len(product_sitemaps)} pod-sitemapa s proizvodima. Krećem u izvlačenje linkova...")

    for i, ps_url in enumerate(product_sitemaps):
        ps_res = scraper.get(ps_url, timeout=30)
        # ISPRAVAK: Koristimo brzi 'xml' parser
        ps_soup = BeautifulSoup(ps_res.content, 'xml')
        for loc in ps_soup.find_all('loc'):
            sitemap_urls.add(loc.text)
        print(f" -> Sitemap {i+1}/{len(product_sitemaps)} obrađen.")
        
except Exception as e:
    print(f"Greška pri čitanju sitemapa: {e}")

print(f"\nUkupno na webshopu u sitemapu pronađeno {len(sitemap_urls)} jedinstvenih linkova.")

# === 3. DELTA USPOREDBA ===
azurirani_podaci = []
novi_linkovi = []

for surl in sitemap_urls:
    if surl in old_data:
        azurirani_podaci.append(old_data[surl])
    else:
        novi_linkovi.append(surl)

print(f"Zadržano ploča: {len(azurirani_podaci)} (Obrisano onih kojih više nema).")
print(f"Pronađeno NOVIH proizvoda za provjeru: {len(novi_linkovi)}.")

# === 4. SKENIRANJE SAMO NOVIH ARTIKALA (POJEDINAČNE STRANICE) ===
if len(novi_linkovi) > 0:
    print("\nKrećem u skeniranje detalja samo za nove proizvode...")
    for i, link in enumerate(novi_linkovi):
        print(f"Provjeravam URL ({i+1}/{len(novi_linkovi)}): {link}")
        try:
            response = scraper.get(link, timeout=15)
            if response.status_code != 200: continue
            
            # ISPRAVAK: Za obične stranice webshopa ostaje 'html.parser'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # PROVJERA ZALIHE
            if soup.find(class_='out-of-stock'):
                print(" -> Preskačem, rasprodano.")
                continue
                
            # FILTAR VINILA: Pretražujemo cjelokupni tekst stranice
            text_lower = soup.get_text().lower()
            if 'gramofon' not in text_lower and 'vinyl' not in text_lower and 'vinil' not in text_lower and 'lp' not in text_lower:
                print(" -> Preskačem, nije vinil.")
                continue
            
            # NASLOV
            title_el = soup.find('h1', class_='product_title')
            full_title = title_el.text.strip() if title_el else ""
            
            # CIJENA
            price = ""
            price_el = soup.find('p', class_='price')
            if price_el:
                ins = price_el.find('ins')
                target = ins if ins else price_el
                bdi = target.find('bdi')
                if bdi: price = bdi.text.replace('€', '').replace('\xa0', '').strip()
            
            # OCJENE: Tražimo crvene spanove unutar stranice
            s_medija, s_omota = "", ""
            red_spans = soup.find_all('span', class_='red')
            for span in red_spans:
                parent_text = span.parent.text.lower() if span.parent else ""
                if "stanje omota" in parent_text:
                    s_omota = pretvori_ocjenu(span.text.strip())
                elif "stanje medija" in parent_text:
                    s_medija = pretvori_ocjenu(span.text.strip())
            
            # SLIKA (Pametni sustav sa srcset prebačen na galeriju pojedinačne stranice)
            image_url = ""
            img_wrap = soup.find('div', class_='woocommerce-product-gallery__image')
            if img_wrap:
                img_tag = img_wrap.find('img')
                if img_tag:
                    if img_tag.has_attr('srcset'):
                        srcset_links = img_tag['srcset'].split(',')
                        if srcset_links:
                            image_url = srcset_links[-1].strip().split(' ')[0]
                    if not image_url and img_tag.has_attr('data-src'):
                        image_url = img_tag['data-src']
                    if not image_url and img_tag.has_attr('src'):
                        image_url = img_tag['src']
            
            if full_title and price:
                azurirani_podaci.append([full_title, price, link, image_url, s_medija, s_omota, "Rabljeno"])
                print(f" -> USPJEH: {full_title} | Medij: {s_medija} | Omot: {s_omota}")
                
            time.sleep(1)
        except Exception as e:
            print(f"Greška na pojedinačnom linku: {e}")
else:
    print("\nNema novih proizvoda za dodavanje. Sve je već usklađeno!")

# === 5. ZAVRŠNO SPREMANJE ===
with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(azurirani_podaci)

print("\nDELTA SUSTAV: Skeniranje uspješno dovršeno! CSV je spreman.")

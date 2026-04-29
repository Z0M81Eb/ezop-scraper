import cloudscraper
from bs4 import BeautifulSoup
import csv
import os
import time

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

csv_filename = 'dancingbear_ploce.csv'

# === 1. UČITAJ STARU BAZU (Ako postoji) ===
old_data = {}
if os.path.exists(csv_filename):
    with open(csv_filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if len(row) >= 7:
                # URL_Proizvoda je na 3. mjestu (indeks 2)
                old_data[row[2]] = row

print(f"Učitano {len(old_data)} starih ploča iz memorije.")

# === 2. POVUCI SITEMAP (Svi aktivni proizvodi) ===
print("Skeniram Dancing Bear sitemap (ovo traje par sekundi)...")
sitemap_urls = set()

def fetch_sitemap(url):
    try:
        res = scraper.get(url, timeout=30)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Ako je ovo sitemap indeks (koji u sebi ima pod-sitemape)
        sitemaps = soup.find_all('sitemap')
        if sitemaps:
            for sm in sitemaps:
                loc = sm.find('loc')
                # WordPress sitemapi za proizvode zovu se npr. wp-sitemap-posts-product-1.xml
                if loc and 'product' in loc.text:
                    fetch_sitemap(loc.text)
        else:
            # Ovo je krajnji sitemap s linkovima na proizvode
            urls = soup.find_all('url')
            for u in urls:
                loc = u.find('loc')
                if loc:
                    # Dodajemo u listu samo ako je URL proizvoda
                    if '/trgovina/' in loc.text or '/proizvod/' in loc.text:
                        sitemap_urls.add(loc.text)
    except Exception as e:
        print(f"Greška pri čitanju sitemapa: {e}")

# OVDJE JE UBAČEN PRAVI LINK!
fetch_sitemap('https://dancingbear.hr/wp-sitemap.xml')

print(f"Na cijelom webshopu aktivno je ukupno {len(sitemap_urls)} proizvoda (CD-i, Vinili, Majice...).")

# === 3. DELTA USPOREDBA ===
azurirani_podaci = []
novi_linkovi = []

for surl in sitemap_urls:
    if surl in old_data:
        # Zadrži stare podatke bez otvaranja te stranice
        azurirani_podaci.append(old_data[surl])
    else:
        # Registriran novi link koji još nemamo u CSV-u
        novi_linkovi.append(surl)

print(f"Zadržano ploča: {len(azurirani_podaci)} (Obrisano onih kojih više nema u prodaji).")
print(f"Pronađeno NOVIH proizvoda za provjeru: {len(novi_linkovi)}.")

# === 4. SKENIRANJE SAMO NOVIH ARTIKALA ===
if len(novi_linkovi) > 0:
    print("\nKrećem u skeniranje detalja samo za nove proizvode...")
    for i, link in enumerate(novi_linkovi):
        print(f"Provjeravam novi URL ({i+1}/{len(novi_linkovi)}): {link}")
        try:
            res = scraper.get(link, timeout=15)
            if res.status_code != 200: continue
            
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # FILTAR: Provjeravamo je li ovo Vinil kroz breadcrumb i kategorije
            kategorije = ""
            bc = soup.find('nav', class_='woocommerce-breadcrumb')
            if bc: kategorije += bc.text.lower()
            cat_span = soup.find('span', class_='posted_in')
            if cat_span: kategorije += cat_span.text.lower()
            
            if 'vinyl' not in kategorije and 'vinil' not in kategorije and 'lp' not in kategorije:
                continue # Nije ploča, preskači
                
            # Naslov
            title_el = soup.find('h1', class_='product_title')
            full_title = title_el.text.strip() if title_el else ""
            
            # Cijena
            price = ""
            price_el = soup.find('p', class_='price')
            if price_el:
                ins = price_el.find('ins')
                if ins: price_el = ins
                bdi = price_el.find('bdi')
                if bdi: price = bdi.text.replace('€', '').replace('\xa0', '').strip()
                
            # Slika s pojedinačne WooCommerce stranice proizvoda
            image_url = ""
            img_wrap = soup.find('div', class_='woocommerce-product-gallery__image')
            if img_wrap:
                # U glavnoj galeriji prava slika je uvijek unutar href od a taga
                a_tag = img_wrap.find('a')
                if a_tag and a_tag.has_attr('href'):
                    image_url = a_tag['href']
                else:
                    img_tag = img_wrap.find('img')
                    if img_tag and img_tag.has_attr('src'):
                        image_url = img_tag['src']
            
            # Ako smo uspjeli izvući potrebno, dodajemo u finalni CSV
            if full_title and price:
                azurirani_podaci.append([full_title, price, link, image_url, "Sealed", "Sealed", "Novo"])
                
            time.sleep(1) # Malena pauza između zahtjeva
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

import cloudscraper
from bs4 import BeautifulSoup
import warnings
from bs4 import XMLParsedAsHTMLWarning
import csv
import os
import time

# Ušutkavamo iritantno upozorenje za XML jer html.parser sasvim dobro čita sitemap
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

csv_filename = 'dancingbear_ploce.csv'

# === 1. UČITAJ STARU BAZU ===
old_data = {}
print(f"Trenutna radna mapa: {os.getcwd()}")

if os.path.exists(csv_filename):
    with open(csv_filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if len(row) >= 7:
                old_data[row[2]] = row

print(f"Učitano {len(old_data)} starih ploča iz memorije.")

# === 2. BRZO ČIŠĆENJE (SITEMAP) ===
print("Skeniram sitemap za provjeru statusa starih ploča...")
sitemap_urls = set()

def fetch_sitemap(url):
    try:
        res = scraper.get(url, timeout=30)
        soup = BeautifulSoup(res.text, 'html.parser')
        sitemaps = soup.find_all('sitemap')
        if sitemaps:
            for sm in sitemaps:
                loc = sm.find('loc')
                if loc and 'product' in loc.text:
                    fetch_sitemap(loc.text)
        else:
            urls = soup.find_all('url')
            for u in urls:
                loc = u.find('loc')
                if loc:
                    if '/trgovina/' in loc.text or '/proizvod/' in loc.text:
                        sitemap_urls.add(loc.text)
    except Exception as e:
        print(f"Greška sitemapa: {e}")

fetch_sitemap('https://dancingbear.hr/wp-sitemap.xml')

# --- SIGURNOSNA KOČNICA PROTIV BRISANJA BAZE ---
azurirani_podaci_dict = {}
if len(sitemap_urls) > 1000:
    for stara_url, stari_red in old_data.items():
        if stara_url in sitemap_urls:
            azurirani_podaci_dict[stara_url] = stari_red
    print(f"Zadržano {len(azurirani_podaci_dict)} aktivnih ploča. (Obrisano {len(old_data) - len(azurirani_podaci_dict)} povučenih iz prodaje).")
else:
    print(f"SIGURNOSNO UPOZORENJE: Nešto nije u redu sa sitemapom, izvučeno je samo {len(sitemap_urls)} linkova. Zbog sigurnosti preskačem brisanje starih ploča!")
    azurirani_podaci_dict = old_data.copy()

# === 3. PAMETNO SKENIRANJE NOVIH PLOČA (KATEGORIJA VINYL) ===
print("\nKrećem u pametno traženje noviteta preko kategorije Vinyl (Zaobilazim CD-ove!)...")
page = 1
zaustavi = False
novih_ploca = []

while not zaustavi:
    cat_url = 'https://dancingbear.hr/kategorija-proizvoda/vinyl/?orderby=date' if page == 1 else f'https://dancingbear.hr/kategorija-proizvoda/vinyl/page/{page}/?orderby=date'
    print(f"Pregledavam stranicu noviteta {page}...")
    
    try:
        res = scraper.get(cat_url, timeout=15)
        if res.status_code == 404: break
        
        soup = BeautifulSoup(res.text, 'html.parser')
        products = soup.find_all('li', class_='product')
        if not products: break
        
        starih_na_stranici = 0
        
        for prod in products:
            a_tag = prod.find('a', class_='woocommerce-LoopProduct-link') or prod.find('a')
            if not a_tag or not a_tag.has_attr('href'): continue
            
            link = a_tag['href']
            
            # FILTAR: Blokiramo generičke kategorijske linkove, uzimamo samo stvarne proizvode
            if '/trgovina/' not in link and '/proizvod/' not in link:
                continue
            
            # KOČNICA: Ako smo naišli na ploču koju već imamo, dodajemo je u brojač i preskačemo detekciju
            if link in azurirani_podaci_dict:
                starih_na_stranici += 1
                continue
                
            print(f" -> Nova ploča detektirana, provjeravam detalje: {link}")
            
            try:
                prod_res = scraper.get(link, timeout=15)
                if prod_res.status_code != 200: continue
                prod_soup = BeautifulSoup(prod_res.text, 'html.parser')
                
                if prod_soup.find(class_='out-of-stock'):
                    print("   - Rasprodano, preskačem.")
                    continue
                    
                title_el = prod_soup.find('h1', class_='product_title')
                full_title = title_el.text.strip() if title_el else ""
                
                # Prilagođeno hvatanje cijene
                price = ""
                price_el = prod_soup.find('p', class_='price')
                if price_el:
                    ins = price_el.find('ins')
                    target = ins if ins else price_el
                    bdi = target.find('bdi')
                    if bdi: 
                        price = bdi.text.replace('€', '').replace('\xa0', '').strip()
                    else:
                        price = target.text.replace('€', '').replace('\xa0', '').strip()
                    
                image_url = ""
                img_wrap = prod_soup.find('div', class_='woocommerce-product-gallery__image')
                if img_wrap:
                    img_a = img_wrap.find('a')
                    if img_a and img_a.has_attr('href'): image_url = img_a['href']
                    else:
                        img_tag = img_wrap.find('img')
                        if img_tag and img_tag.has_attr('src'): image_url = img_tag['src']
                
                if full_title and price:
                    novih_ploca.append([full_title, price, link, image_url, "Sealed", "Sealed", "Novo"])
                    print(f"   - USPJEH: {full_title} dodan u bazu!")
                else:
                    print("   - Fali cijena ili naslov, preskačem.")
                    
                time.sleep(1)
            except Exception as e:
                print(f"   - Greška na linku ploče: {e}")
                
        # NOVA PAMETNA LOGIKA PREKIDA: Znamo da smo gotovi tek kada na stranici ugledamo stare ploče
        if starih_na_stranici > 0:
            print(f"\nNaišli smo na stare ploče (pronađeno {starih_na_stranici} starih na ovoj stranici). Nema više noviteta! Prekidam skeniranje.")
            zaustavi = True
            break
            
        page += 1
        time.sleep(1)
    except Exception as e:
        print(f"Greška na kategoriji: {e}")
        break

# === 4. SPAJANJE I SPREMANJE ===
konacna_baza = novih_ploca + list(azurirani_podaci_dict.values())

with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(konacna_baza)

print(f"\nGOTOVO! Sustav ažuriran. Nova veličina baze: {len(konacna_baza)} ploča (Dodano {len(novih_ploca)} novih).")

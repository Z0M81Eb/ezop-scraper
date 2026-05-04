import requests
from bs4 import BeautifulSoup
import csv
import time
import re

# --- POSTAVKE ---
BASE_URL = "https://menartshop.hr/kategorija-proizvoda/glazba/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
CSV_FILENAME = "menart_katalog.csv"

def clean_image_url(url):
    """
    Menart servira umanjene slike u gridu (npr. slika-200x300.png).
    Ova funkcija briše te dimenzije kako bismo dobili originalnu 
    veliku sliku za tvoj webshop (slika.png).
    """
    if not url: return ""
    # Traži i briše -200x300, -150x150 i slično prije ekstenzije
    return re.sub(r'-\d+x\d+(?=\.[a-zA-Z]+$)', '', url)

def get_lp_filters():
    """Izviđač: Skenira Menartove filtere sa strane i kupi sve LP formate."""
    print("🔍 Tražim sve žive 'LP' filtere u njihovom izborniku...", flush=True)
    
    try:
        # DODAN TIMEOUT! Bez ovoga skripta beskonačno visi ako server ne odgovori.
        response = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        filters = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'filter_format-glazba=' in href and 'lp' in href.lower():
                match = re.search(r'filter_format-glazba=([^&]+)', href)
                if match:
                    filters.add(match.group(1))
    except Exception as e:
        print(f"⚠️ Greška pri učitavanju filtera: {e}. Prebacujem se na Plan B.", flush=True)
        filters = set()
                
    # Ako pukne veza ili sakriju kod, ovo je Plan B
    if not filters:
        filters = {'2lp-cd-bd-dvd', 'cd-bd-lp', 'cd-dvd-bd-lp', 'lp', 'lp-cd'}
        
    print(f"✅ Pronađeni filteri: {', '.join(filters)}", flush=True)
    return list(filters)

def scrape_menart():
    filters = get_lp_filters()
    all_products = []
    seen_urls = set() # Da spriječimo duplikate ako je ploča u više kategorija
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    for fmt in filters:
        page = 1
        print(f"\n🚀 Započinjem struganje za format: {fmt}", flush=True)
        
        while True:
            # Konstrukcija URL-a s paginacijom koju si naveo
            if page == 1:
                url = f"{BASE_URL}?filter_format-glazba={fmt}"
            else:
                url = f"{BASE_URL}page/{page}/?filter_format-glazba={fmt}"
                
            print(f"📄 Učitavam stranicu {page}: {url}", flush=True)
            try:
                response = session.get(url, timeout=15)
                # Ako udarimo u zid (nema više stranica), WooCommerce često vraća 404
                if response.status_code == 404:
                    break 
                    
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Tražimo isključivo h2 naslove s njihovim Tailwind klasama
                titles = soup.find_all('h2', class_=lambda c: c and 'font-bold' in c and 'text-gray-900' in c)
                
                if not titles:
                    break # Našli smo praznu stranicu, kraj ovog formata
                    
                for title_elem in titles:
                    # Naslovnica (li element) koji drži cijeli taj proizvod
                    container = title_elem.find_parent('li')
                    if not container:
                        container = title_elem.parent.parent

                    # --- KONTROLA ZALIHE ---
                    # Preskačemo ploču ako WooCommerce kontejner sadrži klasu rasprodanog artikla
                    if container and 'outofstock' in container.get('class', []):
                        continue
                        
                    # 1. Naslov
                    naslov = title_elem.text.strip()
                    
                    # 2. URL Proizvoda
                    a_tag = container.find('a', href=True)
                    link = a_tag['href'] if a_tag else ""
                    
                    # Preskačemo ako smo ju već unijeli preko drugog filtera
                    if link in seen_urls:
                        continue 
                        
                    # 3. Cijena
                    price_elem = container.find('span', class_='woocommerce-Price-amount')
                    cijena = ""
                    if price_elem:
                        bdi = price_elem.find('bdi')
                        raw_price = bdi.text if bdi else price_elem.text
                        # Očisti Menartov &nbsp; i euro znak
                        cijena = raw_price.replace('\xa0', '').replace('&nbsp;', '').replace('€', '').strip()
                        
                    # 4. Slika (Znamo da je img tag unutar containera)
                    img_elem = container.find('img')
                    slika_url = ""
                    if img_elem:
                        # Lazy load osiguranje
                        if 'data-src' in img_elem.attrs:
                            slika_url = img_elem['data-src']
                        elif 'src' in img_elem.attrs:
                            slika_url = img_elem['src']
                        # Brišemo -200x300 iz imena
                        slika_url = clean_image_url(slika_url)
                        
                    # 5. Medij (LP, 2LP, CD+LP...)
                    medij_elem = container.find('span', class_=lambda c: c and 'text-gray-600' in c and 'ml-3' in c)
                    medij_tekst = medij_elem.text.strip() if medij_elem else "LP"
                    
                    all_products.append({
                        "Naslov": naslov,
                        "Cijena": cijena,
                        "URL_Proizvoda": link,
                        "URL_Slike": slika_url,
                        "Stanje_Medija": "Novo",
                        "Stanje_Omota": "Novo",
                        "Tip_Artikla": medij_tekst
                    })
                    seen_urls.add(link)
                    
                # Traženje next gumba. Ako ga nema, petlja se lomi
                next_page = soup.find('a', class_='next page-numbers')
                if not next_page:
                    break 
                    
                page += 1
                time.sleep(1) # Pristojnost da nas ne blokiraju
                
            except Exception as e:
                print(f"❌ Greška na stranici {page}: {e}", flush=True)
                break
                
    # --- ZAPISIVANJE U CSV ---
    if all_products:
        # Poredak usklađen s Agregator standardom
        zaglavlja = ["Naslov", "Cijena", "URL_Proizvoda", "URL_Slike", "Stanje_Medija", "Stanje_Omota", "Tip_Artikla"]
        with open(CSV_FILENAME, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=zaglavlja)
            writer.writeheader()
            writer.writerows(all_products)
            
        print(f"\n🎉 GOTOVO! Uspješno preuzeto {len(all_products)} unikatnih ploča s Menarta.", flush=True)
    else:
        print("⚠️ Nije pronađena niti jedna ploča.", flush=True)

if __name__ == "__main__":
    scrape_menart()

import cloudscraper
from bs4 import BeautifulSoup
import warnings
from bs4 import XMLParsedAsHTMLWarning
import csv
import time

# Ušutkavamo upozorenja parsera
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Cloudscraper simulira stvarni Chrome preglednik kako nas ne bi blokirali
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

csv_filename = 'dancingbear_ploce.csv'
konacna_baza = []
page = 1
zaustavi = False

print("\n=== POKREĆEM GRID SWEEP (SIGURNO SKENIRANJE KATALOGA) ===")
print("Ovaj proces ignorira rasprodane artikle u startu i ne opterećuje server.\n")

while not zaustavi:
    # WooCommerce standardna paginacija arhive
    cat_url = 'https://dancingbear.hr/kategorija-proizvoda/vinyl/' if page == 1 else f'https://dancingbear.hr/kategorija-proizvoda/vinyl/page/{page}/'
    
    try:
        res = scraper.get(cat_url, timeout=15)
        
        # Ako webshop vrati 404, znači da smo prešli zadnju stranicu kataloga
        if res.status_code == 404:
            print(f"\n[INFO] Došli smo do kraja kataloga na stranici {page}.")
            break
            
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Nalazimo sve "kartice" proizvoda na trenutnoj stranici
        products = soup.find_all('li', class_='product')
        
        if not products:
            print(f"\n[INFO] Stranica {page} nema proizvoda. Završavam skeniranje.")
            break
            
        dodano_na_stranici = 0
        
        for prod in products:
            # 1. KONTROLA ZALIHE: Ako kartica ima klasu 'outofstock', apsolutno je ignoriramo!
            klase = prod.get('class', [])
            if 'outofstock' in klase:
                continue
                
            # 2. DOHVAT LINKA
            a_tag = prod.find('a', class_='woocommerce-LoopProduct-link')
            if not a_tag:
                a_tag = prod.find('a') # Fallback ako WooCommerce koristi drugačiju strukturu
                
            if not a_tag or not a_tag.has_attr('href'):
                continue
            
            link = a_tag['href']
            
            # 3. DOHVAT NASLOVA
            title_el = prod.find(class_='woocommerce-loop-product__title')
            title = title_el.text.strip() if title_el else "Nepoznat naslov"
            
            # 4. DOHVAT SLIKE
            img_el = prod.find('img')
            # Neki webshopovi koriste data-src za "lazy loading", pa provjeravamo obje opcije
            img_url = ""
            if img_el:
                if img_el.has_attr('data-src'):
                    img_url = img_el['data-src']
                elif img_el.has_attr('src'):
                    img_url = img_el['src']
            
            # 5. DOHVAT CIJENE
            price = ""
            price_wrap = prod.find(class_='price')
            if price_wrap:
                # Ako postoji <ins>, znači da je ploča na akciji. Uzimamo tu (sniženu) cijenu.
                ins = price_wrap.find('ins')
                target = ins if ins else price_wrap
                bdi = target.find('bdi')
                
                if bdi:
                    price = bdi.text.replace('€', '').replace('\xa0', '').strip()
                else:
                    price = target.text.replace('€', '').replace('\xa0', '').strip()
            
            # Ako smo uspješno izvukli osnovne podatke, dodajemo u našu "radnu" memoriju
            if title and link and price:
                # Dancing Bear prodaje isključivo nove ploče, pa unaprijed popunjavamo stanje
                konacna_baza.append([title, price, link, img_url, "Sealed", "Sealed", "Novo"])
                dodano_na_stranici += 1
                
        print(f"Stranica {page} obrađena -> Dodano aktivnih ploča: {dodano_na_stranici}")
        
        page += 1
        
        # SIGURNOSNA KOČNICA: Čekamo 1 sekundu prije iduće stranice kako nas server ne bi detektirao kao napad
        time.sleep(1)
        
    except Exception as e:
        print(f"\n[GREŠKA] Problem pri obradi stranice {page}: {e}")
        # Ne prekidamo skriptu, možda je samo privremeni pad veze. Pauziramo duže i nastavljamo na iduću.
        time.sleep(5)
        page += 1


# === SPREMANJE SVJEŽE BAZE ===
print(f"\n=== ZAVRŠENO SKENIRANJE. SPREMAM BAZU ===")
# Skripta u potpunosti pregazi stari CSV i upisuje isključivo ono što je danas na stanju
with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
    writer.writerows(konacna_baza)

print(f"Uspješno generiran {csv_filename}. Ukupno spremno za uvoz: {len(konacna_baza)} aktivnih ploča.")

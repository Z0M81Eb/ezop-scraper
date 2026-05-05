import requests
import csv
import time
import html

# --- POSTAVKE ---
API_BASE = "https://ezop-antikvarijat.hr/wp-json/wc/store"
CSV_FILENAME = "ezop_ploce.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def pretvori_ocjenu(ocjena_str):
    """Pretvara brojeve u standardne ocjene za ploče."""
    try:
        ocjena = int(ocjena_str)
        mape = {10: "M", 9: "NM", 8: "VG+", 7: "VG", 6: "G+", 5: "G"}
        return mape.get(ocjena, "F/P")
    except:
        return ""

def get_glazba_category_id(session):
    """Pronalazi ID kategorije 'Glazba' radi bržeg filtriranja."""
    print("Tražim ID kategorije 'Glazba'...", flush=True)
    try:
        res = session.get(f"{API_BASE}/products/categories", timeout=10)
        if res.status_code == 200:
            for cat in res.json():
                if cat.get('slug') == 'glazba':
                    return cat['id']
    except:
        pass
    return None

def scrape_ezop_api():
    sve_ploce = {}
    
    # 1. Učitavanje stare baze (ako postoji) radi osvježavanja
    try:
        with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 7:
                    sve_ploce[row[2]] = row
        print(f"Učitano {len(sve_ploce)} postojećih ploča iz memorije.", flush=True)
    except FileNotFoundError:
        print("CSV datoteka ne postoji, krećem ispočetka.", flush=True)

    # 2. Inicijalizacija API sesije
    session = requests.Session()
    session.headers.update(HEADERS)
    
    cat_id = get_glazba_category_id(session)
    
    page = 1
    per_page = 50 # 50 je optimalno da server ne vrati timeout grešku
    
    print("\n=== POKREĆEM API SKENIRANJE ===", flush=True)
    
    while True:
        if cat_id:
            url = f"{API_BASE}/products?category={cat_id}&page={page}&per_page={per_page}"
        else:
            url = f"{API_BASE}/products?page={page}&per_page={per_page}"
            
        print(f"Preuzimam API paket {page}...", flush=True)
        
        try:
            res = session.get(url, timeout=20)
            if res.status_code != 200:
                print(f"Kraj podataka ili greška (Kod: {res.status_code}). Završavam.", flush=True)
                break
                
            data = res.json()
            if not data:
                break
                
            for item in data:
                if not item.get('is_in_stock', False):
                    continue
                    
                is_vinyl = False
                s_omot = ""
                s_medij = ""
                
                # Izvlačenje ocjena iz varijacija
                variations = item.get('variations', [])
                for var in variations:
                    attributes = var.get('attributes', [])
                    for attr in attributes:
                        ime_attr = attr.get('name', '').lower()
                        vrijednost = attr.get('value', '')
                        
                        if ime_attr == 'omot':
                            s_omot = pretvori_ocjenu(vrijednost)
                            is_vinyl = True
                        elif ime_attr == 'medij':
                            s_medij = pretvori_ocjenu(vrijednost)
                            is_vinyl = True
                
                if not is_vinyl:
                    continue
                    
                naslov = html.unescape(item.get('name', '')).strip()
                link = item.get('permalink', '')
                
                # Formatiranje cijene
                prices = item.get('prices', {})
                raw_price = prices.get('price', '0')
                minor_unit = prices.get('currency_minor_unit', 2)
                try:
                    price_val = float(raw_price) / (10 ** minor_unit)
                    cijena = f"{price_val:.2f}"
                except:
                    cijena = "0.00"
                    
                # Formatiranje slike (API odmah daje čisti URL visoke rezolucije)
                images = item.get('images', [])
                slika_url = images[0].get('src', '') if images else ""
                
                if naslov and cijena != "0.00":
                    sve_ploce[link] = [naslov, cijena, link, slika_url, s_medij, s_omot, "Vinil"]
                    
            page += 1
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Prekid na stranici {page}: {e}", flush=True)
            break

    # 3. Zapisivanje u CSV
    if sve_ploce:
        with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
            writer.writerows(sve_ploce.values())
        print(f"\nZavršeno. U bazi je sada ukupno {len(sve_ploce)} osvježenih ploča.", flush=True)
    else:
        print("\nNema podataka za spremanje.", flush=True)

if __name__ == "__main__":
    scrape_ezop_api()

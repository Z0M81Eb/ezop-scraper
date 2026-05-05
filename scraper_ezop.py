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
    try:
        ocjena = int(ocjena_str)
        mape = {10: "M", 9: "NM", 8: "VG+", 7: "VG", 6: "G+", 5: "G"}
        return mape.get(ocjena, "F/P")
    except:
        return ""

def get_glazba_category_id(session):
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
    vidjeni_linkovi = set()
    uspjesno_skenirano = False
    
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

    session = requests.Session()
    session.headers.update(HEADERS)
    
    cat_id = get_glazba_category_id(session)
    
    page = 1
    per_page = 50 
    
    print("\n=== POKREĆEM API SKENIRANJE ===", flush=True)
    
    while True:
        if cat_id:
            url = f"{API_BASE}/products?category={cat_id}&page={page}&per_page={per_page}"
        else:
            url = f"{API_BASE}/products?page={page}&per_page={per_page}"
            
        print(f"Preuzimam API paket {page}...", end=" ", flush=True)
        
        try:
            res = session.get(url, timeout=20)
            
            # WooCommerce API vraća praznu listu [] ili 400 grešku kada prođemo zadnju stranicu
            if res.status_code == 400 and "invalid_page_number" in res.text:
                print("-> Kraj arhive dostignut.", flush=True)
                uspjesno_skenirano = True
                break
                
            if res.status_code != 200:
                print(f"\nGreška (Kod: {res.status_code}). Prekidam skeniranje.", flush=True)
                break
                
            data = res.json()
            if not data:
                print("-> Prazan paket. Kraj arhive dostignut.", flush=True)
                uspjesno_skenirano = True
                break
                
            broj_ploca_u_paketu = 0
                
            for item in data:
                if not item.get('is_in_stock', False):
                    continue
                    
                is_vinyl = False
                s_omot = ""
                s_medij = ""
                
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
                
                prices = item.get('prices', {})
                raw_price = prices.get('price', '0')
                minor_unit = prices.get('currency_minor_unit', 2)
                try:
                    price_val = float(raw_price) / (10 ** minor_unit)
                    cijena = f"{price_val:.2f}"
                except:
                    cijena = "0.00"
                    
                images = item.get('images', [])
                slika_url = images[0].get('src', '') if images else ""
                
                if naslov and cijena != "0.00":
                    sve_ploce[link] = [naslov, cijena, link, slika_url, s_medij, s_omot, "Vinil"]
                    vidjeni_linkovi.add(link)
                    broj_ploca_u_paketu += 1
            
            print(f"-> Pronađeno ploča: {broj_ploca_u_paketu}", flush=True)
            page += 1
            time.sleep(0.5)
            
        except Exception as e:
            print(f"\nPrekid na stranici {page}: {e}", flush=True)
            break

    # --- LOGIKA ZA BRISANJE PRODANIH ---
    if uspjesno_skenirano:
        pocetni_broj = len(sve_ploce)
        sve_ploce = {k: v for k, v in sve_ploce.items() if k in vidjeni_linkovi}
        obrisano = pocetni_broj - len(sve_ploce)
        print(f"\nAnaliza završena. Obrisano {obrisano} prodanih ploča koje više ne postoje na webshopu.", flush=True)
    else:
        print("\nUPOZORENJE: Skripta nije došla do kraja (moguć prekid veze). Preskačem brisanje starih ploča radi sigurnosti.", flush=True)

    if sve_ploce:
        with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Naslov', 'Cijena', 'URL_Proizvoda', 'URL_Slike', 'Stanje_Medija', 'Stanje_Omota', 'Tip_Artikla'])
            writer.writerows(sve_ploce.values())
        print(f"Završeno. U bazi je sada ukupno {len(sve_ploce)} ažurnih ploča.", flush=True)
    else:
        print("\nNema podataka za spremanje.", flush=True)

if __name__ == "__main__":
    scrape_ezop_api()

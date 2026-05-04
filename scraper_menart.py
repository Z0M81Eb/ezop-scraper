import requests
import csv
import time
import html

# --- POSTAVKE ---
STORE_API_BASE = "https://menartshop.hr/wp-json/wc/store"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
CSV_FILENAME = "menart_katalog.csv"

def get_glazba_category_id(session):
    """Pronalazi točan ID kategorije 'glazba' kako bismo u startu preskočili igračke i olovke."""
    print("🔍 Tražim ID kategorije 'Glazba'...", flush=True)
    try:
        url = f"{STORE_API_BASE}/products/categories"
        res = session.get(url, timeout=15)
        if res.status_code == 200:
            for cat in res.json():
                if cat.get('slug') == 'glazba':
                    print(f"✅ Kategorija 'Glazba' pronađena (ID: {cat['id']})", flush=True)
                    return cat['id']
    except Exception as e:
        print(f"⚠️ Nije uspjelo dohvaćanje kategorija: {e}", flush=True)
    
    print("⚠️ Nastavljam bez filtera kategorije (skenirat ću sve i filtrirati ručno).", flush=True)
    return None

def scrape_menart_api():
    all_products = []
    page = 1
    per_page = 100 # Vučemo 100 komada odjednom za maksimalnu brzinu
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    # Prvo tražimo ID glazbe da preskočimo školski pribor
    glazba_id = get_glazba_category_id(session)
    
    print("\n🚀 Pokrećem brzi API sweep za Menart...", flush=True)
    
    while True:
        # Ako imamo ID kategorije, tražimo samo nju. Ako nemamo, tražimo sve.
        if glazba_id:
            url = f"{STORE_API_BASE}/products?category={glazba_id}&page={page}&per_page={per_page}"
        else:
            url = f"{STORE_API_BASE}/products?page={page}&per_page={per_page}"
            
        try:
            print(f"📄 Preuzimam API paket {page}...", end=" ", flush=True)
            res = session.get(url, timeout=20)
            
            # Detekcija kraja baze
            if res.status_code == 400 or res.status_code == 404:
                print("-> Kraj baze dosegnut.", flush=True)
                break
            elif res.status_code != 200:
                print(f"-> [GREŠKA SERVERA: {res.status_code}]", flush=True)
                break
                
            data = res.json()
            if not data:
                print("-> Paket prazan, završavam.", flush=True)
                break
                
            dodano = 0
            
            for item in data:
                # 1. KONTROLA ZALIHE (Sada radi bez greške preko API-ja)
                if not item.get('is_in_stock', False):
                    continue
                    
                naslov = html.unescape(item.get('name', 'Nepoznat naslov')).strip()
                
                # 2. INTELIGENTNO ČITANJE ATRIBUTA (Hvata LP, 2LP, LP+BD...)
                attributes = item.get('attributes', [])
                format_ploca = ""
                je_li_vinil = False
                
                for attr in attributes:
                    attr_name = attr.get('name', '').lower()
                    if 'format' in attr_name:
                        terms = attr.get('terms', [])
                        if terms:
                            format_val = terms[0].get('name', '')
                            # Ako vrijednost sadrži LP, vinyl ili single
                            if 'lp' in format_val.lower() or 'vinyl' in format_val.lower() or 'vinil' in format_val.lower() or 'single' in format_val.lower():
                                format_ploca = format_val
                                je_li_vinil = True
                
                # Sigurnosni fallback za naslov
                if not je_li_vinil:
                    naslov_lower = f" {naslov.lower()} "
                    if ' lp ' in naslov_lower or '2lp' in naslov_lower or 'vinyl' in naslov_lower or 'vinil' in naslov_lower:
                        je_li_vinil = True
                        if not format_ploca:
                            format_ploca = "LP"
                            
                # Ako nije vinil (npr. CD, kazeta ili knjiga), ignoriramo
                if not je_li_vinil:
                    continue
                    
                if not format_ploca:
                    format_ploca = "LP"

                # 3. IZVLAČENJE PODATAKA
                link = item.get('permalink', '')
                
                prices = item.get('prices', {})
                raw_price = prices.get('price', '0')
                minor_unit = prices.get('currency_minor_unit', 2)
                try:
                    price_val = float(raw_price) / (10 ** minor_unit)
                    cijena = f"{price_val:.2f}"
                except:
                    cijena = "0.00"
                    
                if cijena == "0.00":
                    continue
                    
                images = item.get('images', [])
                slika_url = images[0].get('src', '') if images else ""
                
                all_products.append({
                    "Naslov": naslov,
                    "Cijena": cijena,
                    "URL_Proizvoda": link,
                    "URL_Slike": slika_url,
                    "Stanje_Medija": "Novo",
                    "Stanje_Omota": "Novo",
                    "Tip_Artikla": format_ploca
                })
                dodano += 1
                
            print(f"-> Pronađeno {dodano} aktivnih vinila u paketu.", flush=True)
            page += 1
            time.sleep(0.5)
            
        except Exception as e:
            print(f"\n❌ GREŠKA: Konekcija pukla na stranici {page}. Detalji: {e}", flush=True)
            break
            
    # --- ZAPISIVANJE U CSV ---
    if all_products:
        zaglavlja = ["Naslov", "Cijena", "URL_Proizvoda", "URL_Slike", "Stanje_Medija", "Stanje_Omota", "Tip_Artikla"]
        with open(CSV_FILENAME, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=zaglavlja)
            writer.writeheader()
            writer.writerows(all_products)
            
        print(f"\n🎉 GOTOVO! API je izvukao {len(all_products)} ploča.", flush=True)
    else:
        print("\n⚠️ Nije pronađena niti jedna ploča.", flush=True)

if __name__ == "__main__":
    scrape_menart_api()

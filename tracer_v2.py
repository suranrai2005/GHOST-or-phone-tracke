import phonenumbers
from phonenumbers import geocoder, carrier, timezone
import folium
from geopy.geocoders import Nominatim
import os
from datetime import datetime
import pycountry
import json
import csv

class PhoneTracker:
    """Tracker OSINT simple et stable"""
    
    def __init__(self):
        self.geocoder = Nominatim(user_agent="phone_tracker")
        self.history = []
        self.cache = {}
        self.cache_file = "phone_cache.json"
        self.load_cache()
    
    def load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
            except:
                self.cache = {}
    
    def save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)
    
    def validate(self, phone_str, region=None):
        try:
            num = phonenumbers.parse(phone_str, region)
            return num if phonenumbers.is_valid_number(num) else None
        except:
            return None
    
    def get_info(self, phone_number):
        cc = phonenumbers.region_code_for_number(phone_number)
        try:
            country = pycountry.countries.get(alpha_2=cc)
            country_name = country.name if country else cc
        except:
            country_name = cc
        
        try:
            tzs = timezone.time_zones_for_number(phone_number)
            tz = tzs[0] if tzs else "Unknown"
        except:
            tz = "Unknown"
        
        return {
            "numéro_int": phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            "numéro_nat": phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.NATIONAL),
            "e164": phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164),
            "code_pays": cc,
            "pays": country_name,
            "code_intl": f"+{phone_number.country_code}",
            "numéro_nat_code": phone_number.national_number,
            "localisation": geocoder.description_for_number(phone_number, "fr"),
            "opérateur": carrier.name_for_number(phone_number, "fr"),
            "type": self._type(phone_number),
            "valide": True,
            "possible": phonenumbers.is_possible_number(phone_number),
            "fuseau": tz,
        }
    
    def _type(self, phone_number):
        from phonenumbers import number_type
        t = number_type(phone_number)
        types = {0: "Fixe", 1: "Mobile", 2: "Fixe/Mobile", 3: "Gratuit", 4: "Surtaxé", 
                 5: "Partagé", 6: "VoIP", 7: "Personnel", 8: "Pager", 9: "UAN", -1: "Inconnu"}
        return types.get(t, "Inconnu")
    
    def coords(self, location_str):
        try:
            loc = self.geocoder.geocode(location_str, timeout=10)
            return (loc.latitude, loc.longitude) if loc else None
        except:
            return None
    
    def create_map(self, location, coords, info, output="Location.html"):
        if not coords:
            return False
        
        try:
            lat, lng = coords
            m = folium.Map(location=[lat, lng], zoom_start=10, tiles="OpenStreetMap")
            
            folium.Marker([lat, lng], popup=f"<b>{location}</b><br>{info['numéro_int']}<br>{info['opérateur']}", 
                         tooltip=f"{info['type']} - {info['pays']}", 
                         icon=folium.Icon(color='red', icon='phone', prefix='fa')).add_to(m)
            
            folium.Circle([lat, lng], 10000, color='red', fill=True, fillOpacity=0.1).add_to(m)
            folium.Circle([lat, lng], 50000, color='orange', fill=True, fillOpacity=0.05).add_to(m)
            
            m.save(output)
            return True
        except:
            return False
    
    def export_json(self, phone_str, data):
        safe = phone_str.replace('+', '').replace(' ', '_')
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"rapport_{safe}_{ts}.json"
        
        rapport = {
            "timestamp": datetime.now().isoformat(),
            "numéro": phone_str,
            "infos": data,
            "outils": ["libphonenumber", "Nominatim", "Folium"]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(rapport, f, indent=2, ensure_ascii=False)
        return filename
    
    def export_csv(self, filename="resultats.csv"):
        if not self.history:
            print("Historique vide")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.history[0].keys())
            writer.writeheader()
            writer.writerows(self.history)
        print(f"✅ CSV: {filename}")
    
    def scan_complet(self, phone_str):
        print("\n" + "="*70)
        print(f"🔍 SCAN COMPLET: {phone_str}")
        print("="*70)
        
        num = self.validate(phone_str)
        if not num:
            print("❌ Numéro invalide")
            return False
        
        info = self.get_info(num)
        
        print(f"\n📱 Numéro: {info['numéro_int']}")
        print(f"🌍 Pays: {info['pays']} ({info['code_pays']})")
        print(f"📍 Localisation: {info['localisation']}")
        print(f"🏢 Opérateur: {info['opérateur']}")
        print(f"📋 Type: {info['type']}")
        print(f"🕐 Fuseau: {info['fuseau']}")
        print(f"✓ Valide: {info['valide']}")
        
        location = info['localisation'] or info['pays']
        print(f"\n🗺️  Géolocalisation: {location}")
        
        c = self.coords(location)
        if c:
            lat, lng = c
            print(f"📌 Coords: {lat:.4f}, {lng:.4f}")
            if self.create_map(location, c, info):
                print("✅ Carte: Location.html")
        else:
            print("⚠️  Coords non trouvées")
        
        print(f"\n💾 Export...")
        json_file = self.export_json(phone_str, info)
        print(f"✅ JSON: {json_file}")
        
        self.cache[phone_str] = info
        self.save_cache()
        
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "numéro": phone_str,
            "pays": info['pays'],
            "type": info['type'],
            "opérateur": info['opérateur']
        })
        
        print("\n" + "="*70)
        return True
    
    def scan_rapide(self, phone_str):
        num = self.validate(phone_str)
        if not num:
            print("❌ Invalide")
            return
        
        info = self.get_info(num)
        print(f"\n📱 {info['numéro_int']}")
        print(f"   Pays: {info['pays']}")
        print(f"   Opérateur: {info['opérateur']}")
        print(f"   Type: {info['type']}")
        print(f"   Fuseau: {info['fuseau']}")
    
    def batch_scan(self, phones):
        print(f"\n📋 BATCH - {len(phones)} numéros\n")
        for i, phone in enumerate(phones, 1):
            print(f"[{i}/{len(phones)}]", end=" ")
            self.scan_complet(phone)
            print()


def menu():
    t = PhoneTracker()
    
    while True:
        print("\n" + "="*70)
        print("📞 PHONE TRACKER OSINT - SIMPLE & STABLE")
        print("="*70)
        print("""
1️⃣  Scan complet
2️⃣  Scan rapide
3️⃣  Batch (plusieurs)
4️⃣  Historique
5️⃣  Export CSV
6️⃣  Cache
7️⃣  Vider cache
8️⃣  Quitter
        """)
        
        c = input("Choix (1-8): ").strip()
        
        if c == "1":
            p = input("\n📞 Numéro: ")
            t.scan_complet(p)
        
        elif c == "2":
            p = input("\n📞 Numéro: ")
            t.scan_rapide(p)
        
        elif c == "3":
            try:
                n = int(input("Combien: "))
                phones = [input(f"#{i+1}: ") for i in range(n)]
                t.batch_scan(phones)
            except:
                print("❌ Erreur")
        
        elif c == "4":
            if t.history:
                print(f"\n📋 ({len(t.history)} entrées):")
                for i, e in enumerate(t.history, 1):
                    print(f"{i}. {e['numéro']} ({e['pays']}) - {e['type']}")
            else:
                print("Vide")
        
        elif c == "5":
            t.export_csv()
        
        elif c == "6":
            if t.cache:
                print(f"\n💾 ({len(t.cache)} cached):")
                for num in t.cache.keys():
                    print(f"  • {num}")
            else:
                print("Vide")
        
        elif c == "7":
            if os.path.exists(t.cache_file):
                os.remove(t.cache_file)
                t.cache = {}
                print("✅ Cache vidé")
        
        elif c == "8":
            print("👋 Bye!")
            break
        
        else:
            print("❌ Invalid")


if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        print("\n\n⛔ Interruption")
    except Exception as e:
        print(f"❌ {e}")

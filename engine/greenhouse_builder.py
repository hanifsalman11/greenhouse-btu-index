import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/greenhouse-btu-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2").strip()
CUSTOM_GREENHOUSE = os.environ.get("CUSTOM_GREENHOUSE", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_greenhouses.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

_CACHED_MODELS = None

# Format: (Greenhouse Model / Scenario, Width Ft, Length Ft, Peak Height Ft, Glazing U-Value [BTU/hr·ft²·°F], Delta-T °F, Glazing Name)
SEED_GREENHOUSES = [
    ("6×8 Ft Backyard Polycarbonate Greenhouse (4mm/6mm Twin-Wall)", 6.0, 8.0, 7.0, 0.62, 45, "6mm Twin-Wall Polycarbonate"),
    ("8×10 Ft Cedar & Polycarbonate Greenhouse (Yardistry / Palram)", 8.0, 10.0, 7.8, 0.58, 45, "6mm Twin-Wall Polycarbonate"),
    ("8×12 Ft Hobby Greenhouse (Palram Canopia Balance / Mythos)", 8.0, 12.0, 7.8, 0.58, 45, "6mm Twin-Wall Polycarbonate"),
    ("10×12 Ft Four-Season Greenhouse (8mm Twin-Wall Polycarbonate)", 10.0, 12.0, 8.2, 0.52, 50, "8mm Twin-Wall Polycarbonate"),
    ("10×16 Ft Heavy-Duty Winter Greenhouse (10mm Polycarbonate)", 10.0, 16.0, 8.5, 0.46, 50, "10mm Twin-Wall Polycarbonate"),
    ("10×20 Ft Planta Sungrow Bell-Shaped Winter Greenhouse", 10.0, 20.0, 7.5, 0.52, 50, "8mm/10mm Polycarbonate"),
    ("12×20 Ft Commercial-Style Hobby Greenhouse (8mm Twin-Wall)", 12.0, 20.0, 9.0, 0.52, 50, "8mm Twin-Wall Polycarbonate"),
    ("12×24 Ft Estate Victorian Glass Greenhouse (Single Tempered)", 12.0, 24.0, 9.5, 1.13, 45, "4mm Single Tempered Glass"),
    ("14×28 Ft High-Tunnel Quonset Hoop House (Single 6-Mil Poly)", 14.0, 28.0, 9.0, 1.15, 40, "Single 6-Mil UV Poly Film"),
    ("20×48 Ft Commercial High-Tunnel (Double-Inflated 6-Mil Poly)", 20.0, 48.0, 11.0, 0.70, 45, "Double-Inflated Poly Film"),
    ("30×72 Ft Commercial Production Greenhouse (Double Poly / 8mm)", 30.0, 72.0, 12.5, 0.65, 45, "Double-Inflated Poly + Endwalls"),
    ("Palram Canopia Harmony & Mythos 6×8 & 6×10 Heater Sizing", 6.0, 10.0, 7.0, 0.62, 45, "6mm Twin-Wall Polycarbonate"),
    ("Palram Canopia Oasis & Glory 8×12 & 8×16 Heater Sizing", 8.0, 12.0, 8.5, 0.55, 45, "8mm Twin-Wall Polycarbonate"),
    ("Costco Yardistry 6.7×7.6 & 8×10 Cedar Greenhouse Heating", 8.0, 10.0, 7.8, 0.58, 45, "6mm Polycarbonate + Cedar Knee"),
    ("Planta Sigma 20 & Sungrow 26 (10×20 & 10×26) Arctic Heating", 10.0, 26.0, 7.5, 0.48, 55, "10mm Twin-Wall Polycarbonate"),
    ("Riga XL & Janssens Royal Victorian Greenhouse BTU Sizing", 10.0, 16.0, 8.8, 0.44, 50, "10mm/16mm Triple-Wall Poly"),
    ("Bio Green Palma 2.0 (1,500W 120V) Greenhouse Coverage Limit", 8.0, 10.0, 7.5, 0.58, 35, "5,118 BTU/hr Electric Heater"),
    ("Dr. Heater DR966 (3,000W / 6,000W 240V) Greenhouse Coverage", 10.0, 16.0, 8.5, 0.52, 50, "20,472 BTU/hr 240V Heater"),
    ("Dr. Heater DR218-1500W vs 240V 4,800W Greenhouse Heater", 10.0, 12.0, 8.0, 0.55, 45, "16,380 BTU/hr 240V Heater"),
    ("Modine Hot Dawg HD30 & HD45 Propane Greenhouse Unit Heater", 16.0, 32.0, 10.0, 0.68, 50, "30,000–45,000 BTU Vented Gas"),
    ("4mm vs 6mm vs 8mm vs 10mm vs 16mm Polycarbonate U-Value", 10.0, 14.0, 8.0, 0.52, 45, "Glazing R-Value Comparison"),
    ("Single 6-Mil Poly vs Double-Layer Air-Inflated Poly Blower", 16.0, 36.0, 9.5, 0.70, 45, "38% Heat Savings w/ Air Gap"),
    ("55-Gallon Black Water Barrel Passive Solar Thermal Mass", 10.0, 14.0, 8.0, 0.52, 40, "458 BTU/°F per 55-Gal Drum"),
    ("Greenhouse Summer Exhaust Fan CFM & Intake Shutter Sizing", 10.0, 16.0, 8.5, 0.52, 45, "1-Minute Air Exchange Rule"),
    ("Bubble Wrap Insulation Lining Inside Polycarbonate Greenhouse", 8.0, 12.0, 7.8, 0.42, 50, "Cuts U-Value from 0.58 to 0.42"),
    ("Lean-To Attached Wall Greenhouse (8×12 & 8×16) BTU Sizing", 8.0, 14.0, 8.5, 0.52, 45, "Shared House Wall Heat Bonus"),
    ("Geodesic Dome Greenhouse (15-Ft & 22-Ft Diameter) BTU Sizing", 15.0, 15.0, 9.5, 0.55, 48, "Minimum Surface-to-Volume Dome"),
    ("Tropical Orchid & Citrus Winter Greenhouse (60°F Night Target)", 10.0, 14.0, 8.2, 0.50, 55, "High Delta-T Tropical Spec"),
    ("Overwintering Hardy Greens & Cactus (40°F Frost-Free Target)", 10.0, 16.0, 8.2, 0.55, 30, "Frost-Protection Thermostat"),
    ("Climate Battery / Earth-Tube Subterranean Greenhouse Heating", 12.0, 24.0, 9.5, 0.52, 45, "4-Inch Perforated Drain Pipe")
]


def load_json(filepath, default):
    """Self-healing JSON loader: otomatis pulih jika file korup atau kosong."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, type(default)) else default
        except Exception as e:
            print(f"[SELF-HEAL] Recovering {filepath} due to read notice: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=10.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def get_active_gemini_model(api_key):
    """
    LAPIS 1: Mesin Pemindai Versi Model Free Tier Otomatis berbasis Regex tanpa angka versi manual.
    Otomatis mendeteksi model Gemini Flash STABIL generasi tertinggi lintas tahun.
    """
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def discover_google_greenhouse_queries(published_slugs):
    """
    LAPIS 4: 3-Tier Infinite Keyword Supply:
    Tier A: Seed List -> Tier B: Google Suggest US -> Tier C: Combinatorial Footprint × Glazing × Delta-T Permutator.
    """
    discovered = []
    seeds = [
        "what size heater for greenhouse ",
        "greenhouse btu calculator ",
        "greenhouse exhaust fan calculator ",
        "palram greenhouse heater "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&gl=us&hl=en&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "what size" in pref or "calculator" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        dim_m = re.search(r"(\d{1,2})x(\d{1,2})", cleaned)
                        if dim_m:
                            w_v = float(dim_m.group(1))
                            l_v = float(dim_m.group(2))
                        else:
                            w_v, l_v = 8.0, 12.0
                        discovered.append((cleaned.title(), w_v, l_v, 8.0, 0.58, 45, "6mm/8mm Twin-Wall Polycarbonate"))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")

    # Tier C Fallback: Combinatorial Permutator (Anti-Habis Lintas Tahun)
    footprints = [
        (6.0, 8.0, 7.0, "6×8 Ft Greenhouse"),
        (8.0, 10.0, 7.8, "8×10 Ft Greenhouse"),
        (8.0, 12.0, 7.8, "8×12 Ft Greenhouse"),
        (10.0, 12.0, 8.2, "10×12 Ft Greenhouse"),
        (10.0, 16.0, 8.5, "10×16 Ft Greenhouse"),
        (12.0, 20.0, 9.0, "12×20 Ft Greenhouse"),
        (14.0, 24.0, 9.5, "14×24 Ft Greenhouse"),
        (20.0, 40.0, 10.5, "20×40 Ft High-Tunnel")
    ]
    glazings = [
        ("6mm Twin-Wall Polycarbonate", 0.58),
        ("8mm Twin-Wall Polycarbonate", 0.52),
        ("10mm Twin-Wall Polycarbonate", 0.46),
        ("Single Tempered Glass", 1.13),
        ("Double-Inflated 6-Mil Poly Film", 0.70)
    ]
    delta_ts = [
        (35, "35°F Delta-T (Mild Winter)"),
        (50, "50°F Delta-T (Freezing Winter)"),
        (65, "65°F Delta-T (Sub-Zero Winter)")
    ]
    for w_f, l_f, h_f, fp_desc in footprints:
        for gl_name, u_val in glazings:
            for dt_f, dt_desc in delta_ts:
                combo_title = f"{fp_desc} ({gl_name}) at {dt_desc}"
                test_slug = slugify(f"{combo_title}-btu-fan-calculator")
                if test_slug not in published_slugs:
                    discovered.append((combo_title, w_f, l_f, h_f, u_val, dt_f, gl_name))
                    if len(discovered) >= 25:
                        return discovered
    return discovered


def build_deterministic_greenhouse_data(gh_tuple):
    """
    LAPIS 3: Mesin Fisika Termodinamika Rumah Kaca ASABE EP406.4 (Q = A * U * dT * Kw) & Ventilasi (100% Bebas Gagal).
    """
    model_name, wid_ft, len_ft, peak_ft, u_val, delta_t_f, glazing_name = gh_tuple

    # 1. Geometri Luas Lantai vs Total Luas Permukaan Selubung Kaca/Polikarbonat (Exposed Glazing Surface Area):
    floor_sqft = int(round(wid_ft * len_ft))
    eave_ft = round(peak_ft * 0.68, 1)
    rafter_slope_ft = math.sqrt(((wid_ft / 2.0) ** 2) + ((peak_ft - eave_ft) ** 2))
    sidewalls_sqft = 2.0 * len_ft * eave_ft
    roof_sqft = 2.0 * len_ft * rafter_slope_ft
    endwalls_sqft = 2.0 * (wid_ft * ((eave_ft + peak_ft) / 2.0))
    total_glazing_sqft = int(round(sidewalls_sqft + roof_sqft + endwalls_sqft))
    volume_cuft = int(round(floor_sqft * ((eave_ft + peak_ft) / 2.0)))

    # 2. Rumus Kehilangan Panas Konduksi + Infiltrasi Angin ASABE EP406.4:
    # Q (BTU/hr) = Total_Glazing_Area * U_Value * Delta_T * 1.18 (18% Wind & Air-Leakage Infiltration Factor)
    required_btu_hr = int(round(total_glazing_sqft * u_val * delta_t_f * 1.18, -2))
    required_electric_kw = round(required_btu_hr / 3412.0, 1)
    required_electric_watts = int(round(required_electric_kw * 1000.0, -2))

    # Evaluasi apakah pemanas colokan 120V 1,500W (5,118 BTU/hr) cukup atau wajib 240V / Propane:
    if required_btu_hr <= 5100:
        heater_power_tier = "120V 1,500W (5,118 BTU/hr) Plug-In Heater Sufficient"
    elif required_btu_hr <= 19800:
        heater_power_tier = f"240V {max(3.0, round(required_electric_kw, 1)):g} kW Electric Heater (240V 20A/30A Circuit) Required"
    else:
        heater_power_tier = f"Vented Propane/Natural Gas Unit Heater ({required_btu_hr:,}+ BTU/hr) Required"

    # 3. Kipas Exhaust Shutter Musim Panas (ASABE 1-Minute Air Exchange + 1.25x Solar Gain Factor):
    summer_exhaust_cfm = int(round(volume_cuft * 1.25, -1))
    # Luas Bukaan Motorized Intake Shutter (agar kecepatan udara masuk <= 350 FPM):
    intake_shutter_sqft = round(summer_exhaust_cfm / 350.0, 1)
    shutter_fan_dia_in = 10 if summer_exhaust_cfm <= 700 else (12 if summer_exhaust_cfm <= 1200 else (16 if summer_exhaust_cfm <= 2200 else (20 if summer_exhaust_cfm <= 3500 else 24)))

    # 4. Drum Air Termal Pasif 55-Galon (1 galon air = 8.34 lbs -> melepaskan 8.34 BTU per 1°F penurunan suhu):
    # 1 drum 55-galon yang mendingin 10°F semalam melepaskan 4,587 BTU (~570 BTU/hr selama 8 jam)
    recommended_55gal_barrels = max(1, int(round(floor_sqft / 40.0)))

    return {
        "greenhouse_name": model_name,
        "glazing_name": glazing_name,
        "seo_title": f"{model_name} Winter BTU Heater, U-Value & Exhaust Fan CFM Calculator (2026)",
        "meta_description": f"Calculate exact winter heat loss ({required_btu_hr:,} BTU/hr / {required_electric_kw} kW across {total_glazing_sqft:,} sq ft of {glazing_name}), {summer_exhaust_cfm:,} CFM exhaust shutter fan, and passive water barrels for {model_name}.",
        "specs": {
            "width_ft": wid_ft,
            "length_ft": len_ft,
            "peak_height_ft": peak_ft,
            "floor_area_sqft": floor_sqft,
            "total_glazing_surface_sqft": total_glazing_sqft,
            "interior_volume_cuft": volume_cuft,
            "glazing_u_value": u_val,
            "glazing_r_value": round(1.0 / u_val, 2),
            "design_delta_t_f": delta_t_f,
            "winter_heat_loss_btu_hr": required_btu_hr,
            "electric_heater_kw": required_electric_kw,
            "electric_heater_watts": required_electric_watts,
            "heater_power_verdict": heater_power_tier,
            "summer_exhaust_cfm": summer_exhaust_cfm,
            "shutter_fan_diameter_in": shutter_fan_dia_in,
            "intake_shutter_area_sqft": intake_shutter_sqft,
            "passive_55gal_barrels": recommended_55gal_barrels,
            "glazing_name": glazing_name
        },
        "asabe_verdict": f"While {model_name} has a floor footprint of {floor_sqft:,} sq. ft. ({wid_ft:g}' W × {len_ft:g}' L × {peak_ft:g}' H = {volume_cuft:,} cu. ft.), conductive heat escapes through its entire {total_glazing_sqft:,} sq. ft. of exposed roof, sidewall, and gable glazing ({glazing_name}, $U = {u_val}\\text{{ BTU/hr}}\\cdot\\text{{ft}}^2\\cdot^\\circ\\text{{F}}$ / R-{round(1.0/u_val, 2)}). Holding a {delta_t_f}°F temperature rise above freezing winter air requires {required_btu_hr:,} BTU/hr ({required_electric_kw} kW / {required_electric_watts:,}W — {heater_power_tier}). For summer solar heat rejection (1 full air exchange per minute), install a {shutter_fan_dia_in}-inch ({summer_exhaust_cfm:,} CFM) aluminum shutter exhaust fan paired with {intake_shutter_sqft} sq. ft. of opposite-wall intake louvers.",
        "hardware_bundle": [
            {
                "badge": f"{required_btu_hr:,} BTU ({required_electric_kw} kW) Heater",
                "title": f"Thermostatically Controlled Greenhouse Heater ({heater_power_tier.split('(')[0].strip() if '(' in heater_power_tier else heater_power_tier})",
                "price_range": "$139 - $589",
                "amazon_query": f"Greenhouse Heater Thermostat {240 if required_btu_hr > 5500 else 120}V Bio Green Palma Dr Heater",
                "gh_note": f"IPX4 splash-proof fan heater maintains frost-free night temps across {total_glazing_sqft:,} sq. ft. of glazing."
            },
            {
                "badge": f"{glazing_name.split()[0]} Twin-Wall Panels",
                "title": f"UV-Protected Twin-Wall Polycarbonate Greenhouse Panels ({glazing_name}) + Foil/Vent Sealing Tape",
                "price_range": "$149 - $549",
                "amazon_query": "Twin Wall Polycarbonate Greenhouse Panels 6mm 8mm 10mm UV",
                "gh_note": f"Dead-air flutes cut thermal conduction to U={u_val} (saving 48% heating fuel vs. single-pane glass)."
            },
            {
                "badge": f"{shutter_fan_dia_in}\" ({summer_exhaust_cfm:,} CFM) Fan Kit",
                "title": f"{shutter_fan_dia_in}-Inch Aluminum Louver Shutter Exhaust Fan + Motorized Intake Damper & Digital Thermostat",
                "price_range": "$129 - $329",
                "amazon_query": f"{shutter_fan_dia_in} Inch Greenhouse Shutter Exhaust Fan Thermostat Intake Louver",
                "gh_note": f"Purges {volume_cuft:,} cu. ft. of superheated summer air every 48 seconds so blossoms never abort above 90°F."
            },
            {
                "badge": "Solar Wax Opener & Shade Cloth",
                "title": "Non-Electric Wax-Cylinder Automatic Roof Vent Opener + 50% UV Aluminet Shade Cloth & Heat Mats",
                "price_range": "$64 - $189",
                "amazon_query": "Automatic Greenhouse Roof Vent Opener Wax Cylinder 50% Shade Cloth",
                "gh_note": "Thermal wax piston expands automatically at 68°F–77°F to vent roof heat even during a power outage."
            }
        ],
        "grower_checklist": [
            f"Never Size a Greenhouse Heater by Floor Square Footage ({floor_sqft:,} sq. ft.) Like a Bedroom! A house has R-19 walls and R-38 ceilings, whereas a greenhouse has {total_glazing_sqft:,} sq. ft. of R-{round(1.0/u_val, 2)} glazing. Multiply Total Exposed Surface Area ({total_glazing_sqft:,} ft²) × Glazing U-Value ({u_val}) × Temperature Difference ($\\Delta T = {delta_t_f}^\\circ\\text{{F}}$) × 1.18 Wind Factor = {required_btu_hr:,} BTU/hr.",
            "Know the 5,118 BTU/hr Limit of a Standard 120V 1,500W Household Outlet: a single 120V 15A circuit maxes out at 1,500 Watts (5,118 BTU/hr). If your winter heat loss exceeds 5,100 BTU/hr, you MUST run a 240V electric heater (3,000W–6,000W = 10,236–20,472 BTU/hr), two separate 120V circuits, or a vented propane heater.",
            "Seal the Top & Bottom Flutes of Twin-Wall Polycarbonate Panels Properly: apply solid aluminum foil tape to the TOP edge of every panel (to keep rain out) and breathable micro-perforated anti-dust vent tape to the BOTTOM edge (so condensation drains out without letting algae or spiders inside the flutes).",
            f"Line the North Wall with {recommended_55gal_barrels}× Black 55-Gallon Water Barrels and Bubble-Wrap the Interior in January: each 55-gallon drum stores ~4,580 BTU of free daytime solar heat (for a 10°F swing), and 1-inch horticultural bubble wrap cuts your glazing U-value by 28%."
        ],
        "faqs": [
            {
                "q": f"How many BTU or Watts do I need to heat {model_name} in winter?",
                "a": f"With {total_glazing_sqft:,} sq. ft. of exposed surface area ({glazing_name}, $U = {u_val}$) and a {delta_t_f}°F temperature differential ($\\text{{Inside Temp}} - \\text{{Coldest Outside Night Temp}}$), ASABE heat-loss equations require {required_btu_hr:,} BTU/hr ({required_electric_kw} kW / {required_electric_watts:,} Watts)."
            },
            {
                "q": f"How much heat does 8mm or 10mm twin-wall polycarbonate save compared to single glass?",
                "a": f"Single-pane 4mm glass has a U-value of 1.13 BTU/hr·ft²·°F (R-0.88). Upgrading to 6mm twin-wall polycarbonate ($U = 0.58$), 8mm twin-wall ($U = 0.52$), or 10mm twin-wall ($U = 0.46$) cuts winter heating bills by 49% to 59%."
            },
            {
                "q": f"What size exhaust fan CFM and intake shutter do I need for {model_name}?",
                "a": f"To prevent summer overheating, your exhaust fan must exchange the entire {volume_cuft:,} cu. ft. interior air volume once every minute with a 1.25x solar load factor = {summer_exhaust_cfm:,} CFM ({shutter_fan_dia_in}-inch shutter fan), paired with {intake_shutter_sqft} sq. ft. of motorized intake shutters on the opposite gable end."
            }
        ]
    }


def generate_greenhouse_data(gh_tuple):
    """
    LAPIS 2: Memanggil model Gemini stabil dengan proteksi Cooldown HTTP 429 & Fallback Otomatis.
    """
    if not GEMINI_API_KEY:
        return build_deterministic_greenhouse_data(gh_tuple)

    model_name, wid_ft, len_ft, peak_ft, u_val, delta_t_f, glazing_name = gh_tuple
    det_fallback = build_deterministic_greenhouse_data(gh_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Certified ASABE Agricultural Structures Engineer (ASABE EP406.4 Greenhouse Heating & Ventilation Specialist). Create an accurate 2026 greenhouse winter heat-loss BTU/kW, glazing U-value comparison, 1-minute summer shutter exhaust fan CFM, and passive solar water barrel guide for: "{model_name}".
Baseline specs: Footprint={wid_ft}' W x {len_ft}' L x {peak_ft}' H ({sp['floor_area_sqft']} sq ft floor, {sp['total_glazing_surface_sqft']} sq ft exposed glazing, {sp['interior_volume_cuft']} cu ft volume), Glazing={glazing_name} (U={u_val} / R-{sp['glazing_r_value']}), Design Delta-T={delta_t_f}F, Winter Heat Loss={sp['winter_heat_loss_btu_hr']} BTU/hr ({sp['electric_heater_kw']} kW / {sp['electric_heater_watts']}W -> {sp['heater_power_verdict']}), Summer Exhaust Fan={sp['summer_exhaust_cfm']} CFM ({sp['shutter_fan_diameter_in']}" Fan + {sp['intake_shutter_area_sqft']} sq ft Intake Shutter), Passive Thermal Mass={sp['passive_55gal_barrels']}x 55-Gal Drums.
Return ONLY a valid JSON object matching this exact schema:
{{
  "greenhouse_name": "{model_name}",
  "glazing_name": "{glazing_name}",
  "seo_title": "{model_name} Winter BTU Heater, U-Value & Exhaust Fan CFM Calculator (2026)",
  "meta_description": "Calculate exact greenhouse winter heat loss (BTU/hr and kW), glazing U-value savings, and summer shutter exhaust fan CFM for {model_name}.",
  "specs": {{
    "width_ft": {wid_ft},
    "length_ft": {len_ft},
    "peak_height_ft": {peak_ft},
    "floor_area_sqft": {sp['floor_area_sqft']},
    "total_glazing_surface_sqft": {sp['total_glazing_surface_sqft']},
    "interior_volume_cuft": {sp['interior_volume_cuft']},
    "glazing_u_value": {u_val},
    "glazing_r_value": {sp['glazing_r_value']},
    "design_delta_t_f": {delta_t_f},
    "winter_heat_loss_btu_hr": {sp['winter_heat_loss_btu_hr']},
    "electric_heater_kw": {sp['electric_heater_kw']},
    "electric_heater_watts": {sp['electric_heater_watts']},
    "heater_power_verdict": "{sp['heater_power_verdict']}",
    "summer_exhaust_cfm": {sp['summer_exhaust_cfm']},
    "shutter_fan_diameter_in": {sp['shutter_fan_diameter_in']},
    "intake_shutter_area_sqft": {sp['intake_shutter_area_sqft']},
    "passive_55gal_barrels": {sp['passive_55gal_barrels']},
    "glazing_name": "{glazing_name}"
  }},
  "asabe_verdict": "3-sentence technical summary stating exposed glazing surface area vs floor area, U-value heat loss at {delta_t_f}F Delta-T in BTU/hr and kW, and required summer exhaust fan CFM.",
  "hardware_bundle": [
    {{
      "badge": "{sp['winter_heat_loss_btu_hr']:,} BTU ({sp['electric_heater_kw']} kW) Heater",
      "title": "Thermostatically Controlled Greenhouse Heater (240V / 120V / Propane)",
      "price_range": "$139 - $589",
      "amazon_query": "Greenhouse Heater Thermostat Bio Green Palma Dr Heater",
      "gh_note": "1-sentence IPX4 splash resistance and frost protection note"
    }},
    {{
      "badge": "Twin-Wall Polycarbonate",
      "title": "UV-Protected Twin-Wall Polycarbonate Greenhouse Panels ({glazing_name}) + Vent Tape",
      "price_range": "$149 - $549",
      "amazon_query": "Twin Wall Polycarbonate Greenhouse Panels 6mm 8mm 10mm UV",
      "gh_note": "1-sentence U-value thermal insulation and light diffusion note"
    }},
    {{
      "badge": "{sp['shutter_fan_diameter_in']}\" ({sp['summer_exhaust_cfm']:,} CFM) Fan Kit",
      "title": "{sp['shutter_fan_diameter_in']}-Inch Aluminum Louver Shutter Exhaust Fan + Intake Damper & Thermostat",
      "price_range": "$129 - $329",
      "amazon_query": "{sp['shutter_fan_diameter_in']} Inch Greenhouse Shutter Exhaust Fan Thermostat",
      "gh_note": "1-sentence 1-minute air exchange and blossom pollination protection note"
    }},
    {{
      "badge": "Wax Vent Opener & Shade",
      "title": "Automatic Solar Wax-Cylinder Roof Vent Opener + 50% UV Aluminet Shade Cloth",
      "price_range": "$64 - $189",
      "amazon_query": "Automatic Greenhouse Roof Vent Opener Wax Cylinder Shade Cloth",
      "gh_note": "1-sentence zero-electricity thermal expansion roof venting note"
    }}
  ],
  "grower_checklist": [
    "Step 1 regarding calculating heat loss by Total Exposed Glazing Surface Area ({sp['total_glazing_surface_sqft']} sq ft), not floor area",
    "Step 2 regarding the 5,118 BTU/hr limit of a 120V 1,500W outlet vs 240V / Propane heaters",
    "Step 3 regarding sealing polycarbonate top flutes with solid foil tape and bottom flutes with breather tape",
    "Step 4 regarding {sp['passive_55gal_barrels']}x 55-gallon black water drums and winter bubble-wrap lining"
  ],
  "faqs": [
    {{"q": "How many BTU or Watts do I need to heat {model_name}?", "a": "Exact Surface Area x U-Value x Delta-T x 1.18 calculation in BTU/hr and kW."}},
    {{"q": "Can a single 1,500W 120V electric heater heat {model_name} in winter?", "a": "Direct comparison of 5,118 BTU/hr output vs {sp['winter_heat_loss_btu_hr']} BTU/hr heat loss."}},
    {{"q": "What size exhaust fan and intake louver do I need for {model_name} in summer?", "a": "Exact cubic volume, 1.25x solar multiplier, CFM, fan diameter, and intake shutter sq ft."}}
  ]
}}
"""

    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id} for '{model_name}': {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice for '{model_name}': {e}")
                break

    return det_fallback


def build_greenhouse_html_page(data, slug, mon_cfg):
    gh_name = data.get("greenhouse_name", "Polycarbonate & Glass Greenhouse")
    sp = data.get("specs", {})
    wid_ft = round(safe_float(sp.get("width_ft", 10.0), 10.0), 1)
    len_ft = round(safe_float(sp.get("length_ft", 12.0), 12.0), 1)
    peak_ft = round(safe_float(sp.get("peak_height_ft", 8.2), 8.2), 1)
    fl_sqft = int(safe_float(sp.get("floor_area_sqft", 120), 120))
    surf_sqft = int(safe_float(sp.get("total_glazing_surface_sqft", 425), 425))
    u_val = round(safe_float(sp.get("glazing_u_value", 0.52), 0.52), 2)
    dt_f = int(safe_float(sp.get("design_delta_t_f", 50), 50))
    btu_hr = int(safe_float(sp.get("winter_heat_loss_btu_hr", 13000), 13000))
    kw = round(safe_float(sp.get("electric_heater_kw", 3.8), 3.8), 1)
    fan_cfm = int(safe_float(sp.get("summer_exhaust_cfm", 1020), 1020))
    fan_in = int(safe_float(sp.get("shutter_fan_diameter_in", 12), 12))
    gl_name = sp.get("glazing_name", "8mm Twin-Wall Polycarbonate")

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Greenhouse+Heater+Thermostat+Twin+Wall+Polycarbonate+Shutter+Fan"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{gh_name} Winter BTU Heater & Exhaust Fan CFM Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Greenhouse Heater Thermostat")), mon_cfg)
        bundle_html += f"""
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-emerald-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Greenhouse Gear')}</span>
              <span class="text-sm font-bold text-amber-400">{item.get('price_range', '$64+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">🌿 {item.get('gh_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Glazing Material vs U-Value, R-Value & Heat Loss Comparison Matrix Table
    glazing_tiers = [
        ("Single 6-Mil UV Poly Film", "U = 1.15", "R-0.87", "100% Baseline Loss", "Seasonal Hoop House"),
        ("Single 4mm Tempered Glass", "U = 1.13", "R-0.88", "-2% Heat Savings", "Victorian Display House"),
        ("Double Air-Inflated 6-Mil Poly", "U = 0.70", "R-1.43", "-39% Heat Savings", "Commercial High-Tunnel"),
        ("4mm Twin-Wall Polycarbonate", "U = 0.68", "R-1.47", "-41% Heat Savings", "3-Season Starter Kit"),
        ("6mm Twin-Wall Polycarbonate", "U = 0.58", "R-1.72", "-50% Heat Savings", "Standard Hobby Greenhouse"),
        ("8mm Twin-Wall Polycarbonate", "U = 0.52", "R-1.92", "-55% Heat Savings", "4-Season Winter Greenhouse"),
        ("10mm / 16mm Multi-Wall Poly", "U = 0.44", "R-2.27", "-62% Heat Savings", "Arctic / Tropical Overwinter")
    ]
    matrix_rows_html = ""
    for g_lbl, u_lbl, r_lbl, s_lbl, a_lbl in glazing_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-slate-800 hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">{g_lbl}</td>
          <td class="py-3 px-4 font-bold text-emerald-400">{u_lbl}</td>
          <td class="py-3 px-4 text-amber-400 font-semibold">{r_lbl}</td>
          <td class="py-3 px-4 text-slate-300">{s_lbl}</td>
          <td class="py-3 px-4 text-xs text-slate-300">{a_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("grower_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-slate-900 border border-slate-800 rounded-xl p-4 cursor-pointer hover:border-slate-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-emerald-500 rounded cursor-pointer gh-check">
          <span class="text-sm text-slate-200 leading-relaxed"><strong>ASABE Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-slate-900 border border-slate-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-slate-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', gh_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', gh_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-emerald-500 text-slate-950 px-2 py-0.5 rounded font-black">GREENHOUSE</span>BTUIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Greenhouse Heaters & Fans →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-emerald-500 text-slate-950 px-3 py-1 rounded-full">{btu_hr:,} BTU/hr ({kw} kW Heater)</span>
        <span class="text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 px-3 py-1 rounded-full">Glazing: {surf_sqft:,} ft² (U={u_val})</span>
        <span class="text-xs font-semibold bg-slate-800 text-slate-300 px-3 py-1 rounded-full">Exhaust Fan: {fan_cfm:,} CFM ({fan_in}" Shutter)</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', gh_name)}</h1>
      <div class="mt-4 bg-slate-900 border-l-4 border-emerald-500 p-4 rounded-r-xl text-sm text-slate-200 leading-relaxed">
        <strong>ASABE EP406.4 Thermal & Ventilation Verdict:</strong> {data.get('asabe_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE GREENHOUSE WINTER BTU/KW, U-VALUE & SUMMER EXHAUST FAN CALCULATOR -->
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {gh_name} Winter BTU & Fan CFM Calculator</h2>
      <p class="text-xs text-slate-400 mb-6">Adjust your greenhouse dimensions, glazing material (U-value), and winter temperature rise ($\Delta T = \text{{Target Inside Temp}} - \text{{Coldest Outside Temp}}$) to calculate exact BTU/hr & kW heating power and summer shutter exhaust fan CFM.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <div class="flex justify-between text-xs font-medium mb-1">
                <label for="widSlider" class="text-slate-300">Width (Ft)</label>
                <span class="text-emerald-400 font-bold"><span id="widVal">{wid_ft:g}</span> ft</span>
              </div>
              <input id="widSlider" type="range" min="6" max="30" step="2" value="{int(wid_ft)}" class="w-full accent-emerald-500 cursor-pointer">
            </div>
            <div>
              <div class="flex justify-between text-xs font-medium mb-1">
                <label for="lenSlider" class="text-slate-300">Length (Ft)</label>
                <span class="text-emerald-400 font-bold"><span id="lenVal">{len_ft:g}</span> ft</span>
              </div>
              <input id="lenSlider" type="range" min="6" max="72" step="2" value="{int(len_ft)}" class="w-full accent-emerald-500 cursor-pointer">
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="glazeSelect" class="block text-xs font-medium text-slate-400 mb-1">Glazing Material & U-Value</label>
              <select id="glazeSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500">
                <option value="1.13" {"selected" if u_val >= 1.0 else ""}>Single Glass / 6-Mil Poly (U=1.13)</option>
                <option value="0.70" {"selected" if 0.65 <= u_val < 1.0 else ""}>Double Air-Inflated Poly (U=0.70)</option>
                <option value="0.58" {"selected" if 0.55 <= u_val < 0.65 else ""}>6mm Twin-Wall Polycarbonate (U=0.58)</option>
                <option value="0.52" {"selected" if 0.49 <= u_val < 0.55 else ""}>8mm Twin-Wall Polycarbonate (U=0.52)</option>
                <option value="0.45" {"selected" if u_val < 0.49 else ""}>10mm/16mm Polycarbonate (U=0.45)</option>
              </select>
            </div>
            <div>
              <label for="dtSlider" class="block text-xs font-medium text-slate-400 mb-1">Temp Rise ($\Delta T$): <span id="dtVal" class="text-emerald-400 font-bold">{dt_f}°F</span></label>
              <input id="dtSlider" type="range" min="15" max="75" step="5" value="{dt_f}" class="w-full accent-emerald-500 cursor-pointer mt-1.5">
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Winter Heater Needed</span>
            <div class="text-xl sm:text-2xl font-black text-white mt-1"><span id="btuOut">{btu_hr:,}</span> <span class="text-xs font-normal text-slate-400">BTU/hr</span></div>
            <p id="kwNoteOut" class="text-xs text-emerald-400 font-semibold mt-1">{kw} kW ({surf_sqft:,} ft² Glazing)</p>
          </div>

          <div class="bg-slate-950 border border-amber-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-amber-400 font-bold">Summer Shutter Fan</span>
            <div class="text-xl sm:text-2xl font-black text-amber-400 mt-1"><span id="cfmOut">{fan_cfm:,}</span> <span class="text-xs font-normal text-slate-400">CFM</span></div>
            <p id="fanDiaOut" class="text-xs text-slate-300 font-semibold mt-1">{fan_in}" Exhaust + Intake Shutter</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-emerald-950/40 border border-emerald-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="ghAdviceBanner" class="text-sm text-emerald-100 font-medium"></div>
        <a id="dynamicGhBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Heater & Shutter Fan on Amazon →
        </a>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {gh_name} Heater, Polycarbonate & Fan Bundle</h2>
        <span class="text-xs text-slate-400">ASABE EP406.4 & IPX4 Splash-Proof Rated</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Greenhouse Glazing Material U-Value, R-Value & Winter Heat-Savings Chart</h2>
      <div class="overflow-x-auto bg-slate-900 border border-slate-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-slate-800 bg-slate-950/60 text-slate-400 uppercase text-xs">
              <th class="py-3.5 px-4">Glazing Material</th>
              <th class="py-3.5 px-4 text-emerald-400">U-Value (BTU/hr·ft²·°F)</th>
              <th class="py-3.5 px-4 text-amber-400">Insulation R-Value</th>
              <th class="py-3.5 px-4">Fuel Savings vs. Poly</th>
              <th class="py-3.5 px-4">Best Application</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Master Grower Surface-Area BTU, Flute Tape & Thermal Barrel Checklist</h2>
        <span id="ghBadge" class="text-xs font-bold bg-slate-800 text-emerald-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({gh_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500 px-4">
    <p>© {datetime.now(timezone.utc).year} GreenhouseBTUIndex. Independent ASABE Greenhouse Thermodynamics, Glazing U-Value & Ventilation Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const widSlider = document.getElementById('widSlider');
    const lenSlider = document.getElementById('lenSlider');
    const glazeSelect = document.getElementById('glazeSelect');
    const dtSlider = document.getElementById('dtSlider');
    const widVal = document.getElementById('widVal');
    const lenVal = document.getElementById('lenVal');
    const dtVal = document.getElementById('dtVal');
    const btuOut = document.getElementById('btuOut');
    const kwNoteOut = document.getElementById('kwNoteOut');
    const cfmOut = document.getElementById('cfmOut');
    const fanDiaOut = document.getElementById('fanDiaOut');
    const ghAdviceBanner = document.getElementById('ghAdviceBanner');
    const dynamicGhBtn = document.getElementById('dynamicGhBtn');

    function recalculateGreenhouse() {{
      const wFt = parseFloat(widSlider.value);
      const lFt = parseFloat(lenSlider.value);
      const uVal = parseFloat(glazeSelect.value);
      const dtF = parseInt(dtSlider.value, 10);

      widVal.textContent = wFt;
      lenVal.textContent = lFt;
      dtVal.textContent = `${{dtF}}°F`;

      const peakFt = wFt <= 8 ? 7.8 : (wFt <= 12 ? 8.8 : 10.5);
      const eaveFt = peakFt * 0.68;
      const rafterFt = Math.sqrt(Math.pow(wFt / 2.0, 2) + Math.pow(peakFt - eaveFt, 2));
      const surfSqft = Math.round((2.0 * lFt * eaveFt) + (2.0 * lFt * rafterFt) + (2.0 * wFt * ((eaveFt + peakFt) / 2.0)));
      const volCuft = Math.round(wFt * lFt * ((eaveFt + peakFt) / 2.0));

      const btuHr = Math.ceil((surfSqft * uVal * dtF * 1.18) / 100) * 100;
      const kw = (btuHr / 3412.0).toFixed(1);

      const fanCfm = Math.ceil((volCuft * 1.25) / 10) * 10;
      let fanIn = 10;
      if (fanCfm <= 700) fanIn = 10;
      else if (fanCfm <= 1200) fanIn = 12;
      else if (fanCfm <= 2200) fanIn = 16;
      else if (fanCfm <= 3500) fanIn = 20;
      else fanIn = 24;

      const htrTier = btuHr <= 5100 ? "120V 1,500W (Bio Green Palma)" : (btuHr <= 20500 ? `240V ${{Math.max(3, Math.ceil(parseFloat(kw)) )}}kW Electric Heater (Dr. Heater)` : "30k–45k BTU Vented Propane Heater");

      btuOut.textContent = btuHr.toLocaleString();
      kwNoteOut.textContent = `${{kw}} kW (${{surfSqft.toLocaleString()}} ft² Glazing)`;
      cfmOut.textContent = fanCfm.toLocaleString();
      fanDiaOut.textContent = `${{fanIn}}" Exhaust + Intake Shutter`;

      ghAdviceBanner.innerHTML = `🌿 <strong>ASABE Thermal Spec:</strong> Holding a ${{dtF}}°F temperature rise across ${{surfSqft.toLocaleString()}} sq ft of glazing requires <strong>${{btuHr.toLocaleString()}} BTU/hr (${{kw}} kW — ${{htrTier}})</strong> in winter, and a <strong>${{fanIn}}-Inch (${{fanCfm.toLocaleString()}} CFM) Aluminum Shutter Exhaust Fan</strong> in summer.`;
      dynamicGhBtn.href = `https://${{amzDomain}}/s?k=Greenhouse+Heater+Thermostat+${{fanIn}}+Inch+Shutter+Exhaust+Fan&tag=${{amzTag}}`;
    }}

    widSlider.addEventListener('input', recalculateGreenhouse);
    lenSlider.addEventListener('input', recalculateGreenhouse);
    glazeSelect.addEventListener('change', recalculateGreenhouse);
    dtSlider.addEventListener('input', recalculateGreenhouse);
    recalculateGreenhouse();

    const checks = document.querySelectorAll('.gh-check');
    const badge = document.getElementById('ghBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Greenhouse+Heater+Thermostat+Twin+Wall+Polycarbonate+Shutter+Fan"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-slate-900 border border-slate-800 hover:border-emerald-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-emerald-500 text-slate-950 px-2.5 py-0.5 rounded">{item.get('btu', 13000):,} BTU ({item.get('kw', 3.8)} kW)</span>
            <span class="text-xs text-slate-400">U={item.get('u_val', 0.52)} | {item.get('cfm', 1020):,} CFM Fan</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-emerald-400 transition">{item['greenhouse_name']}</h2>
          <p class="text-xs text-slate-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-emerald-400">Calculate Winter BTU, U-Value & Fan CFM →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GreenhouseBTUIndex — Greenhouse Winter Heater BTU/kW, Glazing U-Value & Exhaust Fan CFM Calculator (2026)</title>
  <meta name="description" content="Calculate exact greenhouse winter heat-loss BTU/hr and kW, twin-wall polycarbonate vs glass U-value savings, 1-minute summer shutter exhaust fan CFM, and passive water barrel thermal mass for Palram, Yardistry, Planta, and hoop houses.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="GreenhouseBTUIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-emerald-500 text-slate-950 px-2 py-0.5 rounded font-black">GREENHOUSE</span>BTUIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Greenhouse Heaters & Fans →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Greenhouse Winter BTU Heater, Glazing U-Value & Exhaust Fan Database</h1>
      <p class="text-slate-400 mt-3 text-base sm:text-lg">Select your greenhouse dimensions or polycarbonate/glass glazing below to calculate ASABE surface-area winter heat loss (BTU/hr & kW), summer shutter exhaust fan CFM, and 55-gallon thermal water barrels.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search greenhouse size or model (e.g. 8x12 Polycarbonate, 10x16, Palram Canopia, Yardistry, Planta, Bio Green Palma, 8mm...)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-emerald-500">
      </div>
    </div>

    <div id="ghGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500">
    <p>© {datetime.now(timezone.utc).year} GreenhouseBTUIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('ghGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>GreenhouseBTUIndex Greenhouse Winter Heating & Ventilation Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Greenhouse Winter Heat-Loss BTU/kW, Glazing U-Value & Shutter Exhaust Fan CFM Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    """Multi-Endpoint Search Engine Pinger (IndexNow Global + Bing + Google WebSub)."""
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    for idx_endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            req = urllib.request.Request(
                idx_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[INDEXNOW] Pushed {len(new_urls)} URLs to {idx_endpoint} (HTTP {resp.status})")
                break
        except Exception as e:
            print(f"[WARN] IndexNow ({idx_endpoint}) notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published if "slug" in item}

    candidates = []
    if CUSTOM_GREENHOUSE:
        candidates.append((CUSTOM_GREENHOUSE.strip(), 10.0, 12.0, 8.2, 0.52, 50, "8mm Twin-Wall Polycarbonate"))
    candidates.extend(SEED_GREENHOUSES)
    candidates.extend(discover_google_greenhouse_queries(published_slugs))

    new_urls = []
    count = 0

    for gh_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        g_name = gh_tuple[0]
        slug = slugify(f"{g_name}-btu-fan-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating greenhouse winter BTU & exhaust fan calculator for: {g_name}...")
        try:
            data = generate_greenhouse_data(gh_tuple)
            build_greenhouse_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "greenhouse_name": data.get("greenhouse_name", g_name),
                "slug": slug,
                "title": data.get("seo_title", f"{g_name} Greenhouse Calculator"),
                "description": data.get("meta_description", ""),
                "btu": int(safe_float(sp.get("winter_heat_loss_btu_hr", 13000), 13000)),
                "kw": round(safe_float(sp.get("electric_heater_kw", 3.8), 3.8), 1),
                "u_val": round(safe_float(sp.get("glazing_u_value", gh_tuple[4]), gh_tuple[4]), 2),
                "cfm": int(safe_float(sp.get("summer_exhaust_cfm", 1020), 1020)),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            if count < PAGES_PER_RUN:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {g_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new greenhouse BTU & exhaust fan calculator pages.")


if __name__ == "__main__":
    main()

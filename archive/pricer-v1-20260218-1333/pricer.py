"""Pricing CLI and web dashboard for SIGN and GARMENT products."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse


PriceBucket = Dict[str, Dict[str, float | str]]
PriceData = Dict[str, PriceBucket]
PricingPolicy = Dict[str, Any]


DEFAULT_PRICES: PriceData = {
    "MATERIAL": {
        "alum_040": {"label": "040 Aluminum", "price": 3.91},
        "alum_080": {"label": "080 Aluminum", "price": 6.57},
        "banner_13oz": {"label": "13oz Banner", "price": 0.22},
        "acm_3mm": {"label": "3mm ACM", "price": 1.85},
        "decal": {"label": "Decal", "price": 0.00},
    },
    "PRINT": {
        "eco": {"label": "Eco-Solvent Print", "price": 4.00},
        "uv": {"label": "UV Print", "price": 5.00},
    },
    "PLOT": {
        "cast_vinyl": {"label": "Cast Vinyl", "price": 1.16},
        "calendar_vinyl": {"label": "Calendar Vinyl", "price": 0.43},
    },
    "SHIRT": {
        "g2000": {"label": "Gildan 2000 (blank)", "base": 4.00, "each": 0.00},
        "htv_basic": {"label": "HTV Basic (per shirt)", "base": 0.00, "each": 6.00},
    },
    "GARMENT": {
        "shirt_eco": {"label": "Shirt Eco", "product_type": "shirt", "tier": "eco", "price": 10.00},
        "shirt_premium": {"label": "Shirt Premium", "product_type": "shirt", "tier": "premium", "price": 14.00},
        "hoodie_eco": {"label": "Hoodie Eco", "product_type": "hoodie", "tier": "eco", "price": 22.00},
        "hoodie_premium": {"label": "Hoodie Premium", "product_type": "hoodie", "tier": "premium", "price": 29.00},
    },
    "GARMENT_GRAPHICS": {
        "front_full": {
            "label": "Front Full",
            "placement": "front",
            "price_1": 2.58,
            "price_2": 5.06,
            "price_3": 7.29,
            "price_dtf": 2.95,
        },
        "front_left_breast": {
            "label": "Front Left Breast",
            "placement": "front",
            "price_1": 1.72,
            "price_2": 3.43,
            "price_3": 5.08,
            "price_dtf": 0.61,
        },
        "front_none": {
            "label": "Front None",
            "placement": "front",
            "price_1": 0.00,
            "price_2": 0.00,
            "price_3": 0.00,
            "price_dtf": 0.00,
        },
        "back_full": {
            "label": "Back Full",
            "placement": "back",
            "price_1": 2.58,
            "price_2": 5.06,
            "price_3": 7.29,
            "price_dtf": 2.95,
        },
        "back_none": {
            "label": "Back None",
            "placement": "back",
            "price_1": 0.00,
            "price_2": 0.00,
            "price_3": 0.00,
            "price_dtf": 0.00,
        },
    },
    "LED_MODS": {
        "mods_white": {"label": "Modules White", "color_mode": "white", "voltage": 12.0, "watts_per_ft": 2.2, "price_per_ft": 6.0},
        "mods_color": {"label": "Modules Color", "color_mode": "color", "voltage": 12.0, "watts_per_ft": 2.8, "price_per_ft": 7.5},
        "mods_rgb": {"label": "Modules RGB", "color_mode": "rgb", "voltage": 12.0, "watts_per_ft": 3.8, "price_per_ft": 9.0},
    },
    "LED_RIBBON": {
        "ribbon_std_white_5v": {"label": "Ribbon Std White 5V", "density": "standard", "color_mode": "white", "voltage": 5.0, "watts_per_ft": 1.5, "price_per_ft": 4.2},
        "ribbon_std_color_12v": {"label": "Ribbon Std Color 12V", "density": "standard", "color_mode": "color", "voltage": 12.0, "watts_per_ft": 2.0, "price_per_ft": 5.5},
        "ribbon_high_rgb_12v": {"label": "Ribbon High RGB 12V", "density": "high", "color_mode": "rgb", "voltage": 12.0, "watts_per_ft": 3.6, "price_per_ft": 8.0},
        "ribbon_high_argb_5v": {"label": "Ribbon High ARGB 5V", "density": "high", "color_mode": "argb", "voltage": 5.0, "watts_per_ft": 4.4, "price_per_ft": 9.0},
        "ribbon_high_rgb_24v": {"label": "Ribbon High RGB 24V", "density": "high", "color_mode": "rgb", "voltage": 24.0, "watts_per_ft": 3.2, "price_per_ft": 8.8},
    },
    "CONTROLLER": {
        "eco": {"label": "Eco Controller", "price": 15.0},
        "premium": {"label": "Premium Controller", "price": 28.0},
        "remote": {"label": "Remote Controller", "price": 35.0},
        "app": {"label": "App Support Controller", "price": 45.0},
    },
    "WHOLESALE_SUBOUT": {
        "banner_std_13oz_raw": {"label": "Standard 13oz Matte Scrim (Raw)", "unit": "sqft", "price": 1.50, "group": "Banner"},
        "banner_std_13oz_trimmed": {"label": "Standard 13oz Matte Scrim (Trimmed)", "unit": "sqft", "price": 2.00, "group": "Banner"},
        "banner_std_13oz_finished": {"label": "Standard 13oz Matte Scrim (Hem/Grom/Pole)", "unit": "sqft", "price": 2.50, "group": "Banner"},
        "banner_premium_15oz": {"label": "Premium 15oz Smooth (Hem/Grom/Pole)", "unit": "sqft", "price": 3.00, "group": "Banner"},
        "banner_blockout_18oz_finished": {"label": "Heavy 18oz Blockout (Finished)", "unit": "sqft", "price": 3.50, "group": "Banner"},
        "banner_blockout_18oz_true_ds": {"label": "Heavy 18oz Blockout (True Double Sided)", "unit": "sqft", "price": 4.50, "group": "Banner"},
        "banner_blockout_18oz_hd_ds": {"label": "Heavy 18oz Blockout (HD Double Sided)", "unit": "sqft", "price": 5.50, "group": "Banner"},
        "banner_backlit_vinyl": {"label": "Backlit Vinyl (Flex Face Double-Density)", "unit": "sqft", "price": 5.00, "group": "Banner"},
        "banner_liquid_lam": {"label": "Liquid Lamination (Matte/Gloss UV)", "unit": "sqft", "price": 1.50, "group": "Banner"},
        "banner_mesh_finished": {"label": "Mesh Banner (Hem/Grom/Pole)", "unit": "sqft", "price": 2.65, "group": "Banner"},
        "banner_reinforced_hems": {"label": "Reinforced 3rd Layer Hems", "unit": "linft", "price": 1.25, "group": "Banner"},
        "misc_poster_10pt": {"label": "Poster Paper 10pt", "unit": "sqft", "price": 1.50, "group": "Misc"},
        "misc_static_cling": {"label": "Static Cling (White/Clear CMYK)", "unit": "sqft", "price": 3.50, "group": "Misc"},
        "misc_interior_glass_2nd_surface": {"label": "Interior Glass (2nd Surface White Ink)", "unit": "sqft", "price": 5.00, "group": "Misc"},
        "misc_floor_graphic_indoor": {"label": "Floor Graphic Indoor", "unit": "sqft", "price": 4.50, "group": "Misc"},
        "misc_floor_graphic_outdoor_hightac": {"label": "Floor Graphic Outdoor High Tac", "unit": "sqft", "price": 6.00, "group": "Misc"},
        "misc_wall_graphic_low_tac": {"label": "Low-Tac Air-Egress Wall Graphic", "unit": "sqft", "price": 3.95, "group": "Misc"},
        "misc_magnet_standard": {"label": "Standard Magnet (Direct, No Lam)", "unit": "sqft", "price": 5.00, "group": "Misc"},
        "misc_magnet_020_030": {"label": "Magnet (.020/.030)", "unit": "sqft", "price": 6.00, "group": "Misc"},
        "misc_artist_canvas": {"label": "Artist Canvas (Digital)", "unit": "sqft", "price": 5.50, "group": "Misc"},
        "misc_polypropylene_8mil": {"label": "Non-Curling 8mil Polypropylene", "unit": "sqft", "price": 4.00, "group": "Misc"},
        "misc_duratrans_8mil": {"label": "Duratrans Backlit Film 8mil", "unit": "sqft", "price": 5.00, "group": "Misc"},
        "psa_standard_self_adhesive": {"label": "Standard Self-Adhesive Vinyl + Lam", "unit": "sqft", "price": 4.00, "group": "PSA"},
        "psa_hi_tack_self_adhesive": {"label": "Self-Adhesive Hi-Tack Vinyl + Lam", "unit": "sqft", "price": 4.50, "group": "PSA"},
        "psa_wrap_cast_lam": {"label": "Premium Wrap Self-Adhesive + Cast Gloss Lam", "unit": "sqft", "price": 5.00, "group": "PSA"},
        "psa_backlit_clear_white": {"label": "Backlit Self-Adhesive (Clear/White)", "unit": "sqft", "price": 6.00, "group": "PSA"},
        "psa_backlit_day_night": {"label": "Backlit Self-Adhesive (Day-Night)", "unit": "sqft", "price": 7.00, "group": "PSA"},
        "psa_reflective": {"label": "Reflective Self-Adhesive + Lam", "unit": "sqft", "price": 8.00, "group": "PSA"},
        "psa_window_perf_economy": {"label": "Economy Window Perf", "unit": "sqft", "price": 3.50, "group": "PSA"},
        "psa_window_perf_premium": {"label": "Premium Window Perf", "unit": "sqft", "price": 5.00, "group": "PSA"},
        "psa_window_perf_optical_lam": {"label": "Window Perf + Optically Clear Lam", "unit": "sqft", "price": 6.50, "group": "PSA"},
        "psa_window_perf_2nd_surface": {"label": "2nd Surface Window Perf", "unit": "sqft", "price": 7.50, "group": "PSA"},
        "psa_uv_inhibitive_lam": {"label": "UV Inhibitive Film Lamination", "unit": "sqft", "price": 1.00, "group": "PSA"},
        "psa_dry_erase_lam": {"label": "Dry-Erase Lamination", "unit": "sqft", "price": 1.50, "group": "PSA"},
        "rigid_coroplast_4mm": {"label": "Coroplast 4mm", "unit": "sqft", "price": 2.50, "group": "Rigid"},
        "rigid_coroplast_6mm": {"label": "Coroplast 6mm", "unit": "sqft", "price": 3.50, "group": "Rigid"},
        "rigid_coroplast_10mm": {"label": "Coroplast 10mm", "unit": "sqft", "price": 5.00, "group": "Rigid"},
        "rigid_coroplast_18x24_ds_10_18": {"label": "Coroplast 4mm 18x24 DS (10-18 Qty)", "unit": "each", "price": 10.00, "group": "Rigid"},
        "rigid_coroplast_18x24_ds_20_90": {"label": "Coroplast 4mm 18x24 DS (20-90 Qty)", "unit": "each", "price": 8.00, "group": "Rigid"},
        "rigid_coroplast_18x24_ds_100_plus": {"label": "Coroplast 4mm 18x24 DS (100+ Qty)", "unit": "each", "price": 7.50, "group": "Rigid"},
        "rigid_foamboard_3_16": {"label": "Standard 3/16 Foamboard", "unit": "sqft", "price": 3.00, "group": "Rigid"},
        "rigid_ultraboard_3_16": {"label": "Ultraboard 3/16 Rigidboard", "unit": "sqft", "price": 4.00, "group": "Rigid"},
        "rigid_ultraboard_half_inch": {"label": "Ultraboard 1/2 Rigidboard", "unit": "sqft", "price": 5.50, "group": "Rigid"},
        "rigid_ultraboard_one_inch": {"label": "Ultraboard 1 Rigidboard", "unit": "sqft", "price": 7.50, "group": "Rigid"},
        "rigid_aluminum_040": {"label": "Aluminum .040", "unit": "sqft", "price": 8.00, "group": "Rigid"},
        "rigid_aluminum_060": {"label": "Aluminum .060", "unit": "sqft", "price": 10.00, "group": "Rigid"},
        "rigid_acm_3mm": {"label": "3mm Aluminum Composite Sheet", "unit": "sqft", "price": 6.00, "group": "Rigid"},
        "rigid_acm_3mm_lam": {"label": "3mm Aluminum Composite Sheet (Laminated)", "unit": "sqft", "price": 7.00, "group": "Rigid"},
        "rigid_styrene_020": {"label": "Styrene .020", "unit": "sqft", "price": 2.75, "group": "Rigid"},
        "rigid_styrene_040": {"label": "Styrene .040", "unit": "sqft", "price": 3.50, "group": "Rigid"},
        "rigid_styrene_060": {"label": "Styrene .060", "unit": "sqft", "price": 4.50, "group": "Rigid"},
        "rigid_pvc_3mm": {"label": "PVC Board 3mm", "unit": "sqft", "price": 3.00, "group": "Rigid"},
        "rigid_pvc_6mm": {"label": "PVC Board 6mm", "unit": "sqft", "price": 6.50, "group": "Rigid"},
        "rigid_pvc_13mm": {"label": "PVC Board 13mm", "unit": "sqft", "price": 8.00, "group": "Rigid"},
        "addon_second_side_print": {"label": "2nd Side Printing Add-On", "unit": "sqft", "price": 1.25, "group": "Add-On"},
    },
    "HARBOR_FREQUENT": {},
}


ALL_CATEGORIES = list(DEFAULT_PRICES.keys())

DEFAULT_PRICING_POLICY: PricingPolicy = {
    "profiles": {
        "conservative": {
            "sign_markup_multiplier": 1.7,
            "led_markup_multiplier": 1.5,
            "garment_markup_multiplier": 2.0,
        },
        "standard": {
            "sign_markup_multiplier": 2.0,
            "led_markup_multiplier": 1.8,
            "garment_markup_multiplier": 2.4,
        },
        "aggressive": {
            "sign_markup_multiplier": 2.4,
            "led_markup_multiplier": 2.2,
            "garment_markup_multiplier": 3.0,
        }
    },
    "active_profile": "standard",
    "default_discount_percent": 0.0,
    "discount_options_percent": [0, 5, 10, 15],
    "minimum_charge": 35.0,
    "cost_model": {
        "sign": {
            "labor_rate_per_hour": 65.0,
            "default_waste_percent": 10.0,
            "labor_minutes_per_sqft_print": 0.0,
            "labor_minutes_per_sqft_plot": 0.0,
            "led_labor_minutes_per_ft": 0.0,
            "setup_fee": 0.0,
            "proof_fee": 0.0,
            "waste_percent_material": 0.0,
            "waste_percent_process": 0.0,
            "waste_percent_led": 0.0,
        },
        "garment": {
            "labor_rate_per_hour": 65.0,
            "default_waste_percent": 10.0,
            "labor_minutes_per_item": 0.0,
            "setup_fee": 0.0,
            "proof_fee": 0.0,
            "waste_percent_hard_cost": 0.0,
        },
    },
}


def _copy_default_prices() -> PriceData:
    copied: PriceData = {}
    for category, entries in DEFAULT_PRICES.items():
        copied[category] = {k: dict(v) for k, v in entries.items()}
    return copied


def parse_prices_lines(lines: List[str]) -> Tuple[PriceData, List[str]]:
    data: PriceData = {category: {} for category in ALL_CATEGORIES}
    warnings: List[str] = []

    for idx, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split(",")]
        category = parts[0].upper() if parts else ""

        try:
            if category in {"MATERIAL", "PRINT", "PLOT"}:
                if len(parts) != 4:
                    raise ValueError("expected 4 fields")
                _, key, label, price = parts
                data[category][key] = {"label": label, "price": float(price)}
            elif category == "SHIRT":
                if len(parts) != 5:
                    raise ValueError("expected 5 fields")
                _, key, label, base, each = parts
                data["SHIRT"][key] = {"label": label, "base": float(base), "each": float(each)}
            elif category == "GARMENT":
                if len(parts) != 6:
                    raise ValueError("expected 6 fields")
                _, key, label, product_type, tier, price = parts
                data["GARMENT"][key] = {
                    "label": label,
                    "product_type": product_type.lower(),
                    "tier": tier.lower(),
                    "price": float(price),
                }
            elif category == "GARMENT_GRAPHICS":
                if len(parts) != 8:
                    raise ValueError("expected 8 fields")
                _, key, label, placement, price_1, price_2, price_3, price_dtf = parts
                data["GARMENT_GRAPHICS"][key] = {
                    "label": label,
                    "placement": placement.lower(),
                    "price_1": float(price_1),
                    "price_2": float(price_2),
                    "price_3": float(price_3),
                    "price_dtf": float(price_dtf),
                }
            elif category == "LED_MODS":
                if len(parts) != 7:
                    raise ValueError("expected 7 fields")
                _, key, label, color_mode, voltage, watts_per_ft, price_per_ft = parts
                data["LED_MODS"][key] = {
                    "label": label,
                    "color_mode": color_mode.lower(),
                    "voltage": float(voltage),
                    "watts_per_ft": float(watts_per_ft),
                    "price_per_ft": float(price_per_ft),
                }
            elif category == "LED_RIBBON":
                if len(parts) != 8:
                    raise ValueError("expected 8 fields")
                _, key, label, density, color_mode, voltage, watts_per_ft, price_per_ft = parts
                data["LED_RIBBON"][key] = {
                    "label": label,
                    "density": density.lower(),
                    "color_mode": color_mode.lower(),
                    "voltage": float(voltage),
                    "watts_per_ft": float(watts_per_ft),
                    "price_per_ft": float(price_per_ft),
                }
            elif category == "CONTROLLER":
                if len(parts) != 4:
                    raise ValueError("expected 4 fields")
                _, key, label, price = parts
                data["CONTROLLER"][key] = {"label": label, "price": float(price)}
            elif category == "WHOLESALE_SUBOUT":
                if len(parts) != 6:
                    raise ValueError("expected 6 fields")
                _, key, label, unit, price, group = parts
                unit_clean = unit.lower()
                if unit_clean not in {"sqft", "linft", "each"}:
                    raise ValueError("unit must be sqft, linft, or each")
                data["WHOLESALE_SUBOUT"][key] = {
                    "label": label,
                    "unit": unit_clean,
                    "price": float(price),
                    "group": group,
                }
            elif category == "HARBOR_FREQUENT":
                if len(parts) != 6:
                    raise ValueError("expected 6 fields")
                _, key, label, product_type, code, price = parts
                data["HARBOR_FREQUENT"][key] = {
                    "label": label,
                    "product_type": product_type,
                    "code": code,
                    "price": float(price),
                }
            else:
                warnings.append(f"Line {idx} skipped (unknown category): {line}")
        except Exception as exc:  # pylint: disable=broad-except
            warnings.append(f"Line {idx} skipped ({exc}): {line}")

    if not data["MATERIAL"] or (not data["PRINT"] and not data["PLOT"]) or not data["GARMENT"]:
        warnings.append("prices.txt missing required records; using built-in defaults.")
        return _copy_default_prices(), warnings

    for category in {
        "LED_MODS",
        "LED_RIBBON",
        "CONTROLLER",
        "SHIRT",
        "GARMENT_GRAPHICS",
        "WHOLESALE_SUBOUT",
        "HARBOR_FREQUENT",
    }:
        if not data[category]:
            data[category] = {k: dict(v) for k, v in DEFAULT_PRICES[category].items()}
            if category != "HARBOR_FREQUENT":
                warnings.append(f"{category} missing in prices.txt; using defaults for it.")

    return data, warnings


def load_prices(path: str = "prices.txt") -> Tuple[PriceData, List[str]]:
    price_path = Path(path)
    if not price_path.exists():
        return _copy_default_prices(), [f"{path} not found; using built-in defaults."]
    try:
        lines = price_path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:  # pylint: disable=broad-except
        return _copy_default_prices(), [f"Could not read {path} ({exc}); using defaults."]
    data, warnings = parse_prices_lines(lines)
    _inject_harbor_frequents_into_sign_menus(data, warnings)
    return data, warnings


def _parse_harbor_area_sqft(label: str) -> float | None:
    """Parse common Harbor size patterns and return total sqft."""
    text = label.lower()
    # examples:
    # 4' x 8'
    # 54" x 164'
    # 24" x 10 yd
    m = re.search(r"(\d+(?:\.\d+)?)\s*(\"|')\s*x\s*(\d+(?:\.\d+)?)\s*(yd|'|\")", text)
    if not m:
        return None

    w = float(m.group(1))
    wu = m.group(2)
    h = float(m.group(3))
    hu = m.group(4)

    width_ft = w / 12.0 if wu == '"' else w
    if hu == "yd":
        height_ft = h * 3.0
    elif hu == '"':
        height_ft = h / 12.0
    else:
        height_ft = h

    area = width_ft * height_ft
    return area if area > 0 else None


def _extract_mm_value(label: str) -> str | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*mm", label.lower())
    return match.group(1) if match else None


def _classify_harbor_entry(
    label: str, product_type: str, code: str, price_per_sqft: float
) -> Tuple[str, str, str] | None:
    ptype = product_type.lower()
    l = label.lower()
    c = code.upper().strip()

    if "plotter cut films" in ptype:
        if c == "32223K":
            return ("PLOT", "calendar_vinyl", "Calendar Vinyl")
        if c == "92664K":
            return ("PLOT", "cast_vinyl", "Cast Vinyl")
        return ("PLOT", f"vinyl_{re.sub(r'[^a-z0-9]+', '_', c.lower()).strip('_')}", f"Vinyl {c}")

    if "aluminum sheets" in ptype:
        if ".040" in l:
            return ("MATERIAL", "alum_040", "040 Aluminum")
        if ".080" in l:
            return ("MATERIAL", "alum_080", "080 Aluminum")

    if "metal faced panels" in ptype:
        mm = _extract_mm_value(label) or "3"
        return ("MATERIAL", f"acm_{mm.replace('.', '_')}mm", f"{mm}mm ACM")

    if "corrugated plastic" in ptype:
        mm = _extract_mm_value(label)
        if mm:
            return ("MATERIAL", f"coro_{mm.replace('.', '_')}mm", f"{mm}mm Coro")

    if "banner and film media" in ptype and "13 oz" in l:
        return ("MATERIAL", "banner_13oz", "13oz Banner")

    if "pvc sheet" in ptype:
        mm = _extract_mm_value(label) or "6"
        return ("MATERIAL", f"pvc_{mm.replace('.', '_')}mm", f"{mm}mm PVC")

    if "acrylic sheet" in ptype:
        if "3/16" in l:
            return ("MATERIAL", "acrylic_3_16", "3/16 Acrylic")
        return ("MATERIAL", f"acrylic_{re.sub(r'[^a-z0-9]+', '_', c.lower()).strip('_')}", "Acrylic")

    # Keep other material-like types available when they can be converted.
    if price_per_sqft > 0:
        return (
            "MATERIAL",
            f"mat_{re.sub(r'[^a-z0-9]+', '_', c.lower()).strip('_')}",
            code,
        )
    return None


def _inject_harbor_frequents_into_sign_menus(
    data: PriceData, warnings: List[str]
) -> None:
    frequents = data.get("HARBOR_FREQUENT", {})
    if not frequents:
        return

    # Remove previously injected fallback keys if present in the loaded file.
    for bucket in ("MATERIAL", "PLOT"):
        stale = [k for k in data[bucket].keys() if k.startswith("hf_")]
        for key in stale:
            del data[bucket][key]

    added_material = 0
    added_plot = 0
    updated_existing = 0
    for entry in frequents.values():
        label = str(entry.get("label", "")).strip()
        ptype = str(entry.get("product_type", "")).lower()
        code = str(entry.get("code", "")).strip()
        price_each = float(entry.get("price", 0))
        if not label or not code or price_each <= 0:
            continue

        area_sqft = _parse_harbor_area_sqft(label)
        if area_sqft is None:
            continue

        price_per_sqft = price_each / area_sqft
        mapped = _classify_harbor_entry(label, ptype, code, price_per_sqft)
        if not mapped:
            continue

        target, key, simple_label = mapped
        existed = key in data[target]
        data[target][key] = {
            "label": simple_label,
            "price": round(price_per_sqft, 2),
        }
        if existed:
            updated_existing += 1
        else:
            if target == "MATERIAL":
                added_material += 1
            else:
                added_plot += 1

    if added_material or added_plot or updated_existing:
        warnings.append(
            "Injected Harbor frequents into menus: "
            f"{added_material} new MATERIAL, {added_plot} new VINYL, {updated_existing} refreshed."
        )


def load_pricing_policy(path: str = "pricing_policy.json") -> Tuple[PricingPolicy, List[str]]:
    warnings: List[str] = []
    policy = json.loads(json.dumps(DEFAULT_PRICING_POLICY))
    policy_path = Path(path)
    if not policy_path.exists():
        warnings.append(f"{path} not found; using built-in pricing policy.")
        return policy, warnings
    try:
        raw = json.loads(policy_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            policy.update({k: v for k, v in raw.items() if k in policy})
    except Exception as exc:  # pylint: disable=broad-except
        warnings.append(f"Could not parse {path} ({exc}); using built-in pricing policy.")
    return policy, warnings


def _resolve_markup(
    policy: PricingPolicy,
    quote_type: str,
    override: float | None = None,
    profile_name: str | None = None,
) -> float:
    if override is not None:
        if override < 1.0:
            raise ValueError("markup_multiplier must be >= 1.0")
        return float(override)
    selected_profile = profile_name or str(policy.get("active_profile", "standard"))
    profiles = policy.get("profiles", {})
    profile = profiles.get(selected_profile, {}) if isinstance(profiles, dict) else {}
    if not profile and isinstance(profiles, dict):
        fallback_name = str(policy.get("active_profile", "standard"))
        profile = profiles.get(fallback_name, {})
    key = f"{quote_type}_markup_multiplier"
    value = profile.get(key, 1.0)
    return float(value) if float(value) >= 1.0 else 1.0


def _resolve_discount(policy: PricingPolicy, override: float | None = None) -> float:
    discount = float(policy.get("default_discount_percent", 0.0)) if override is None else float(override)
    if discount < 0 or discount >= 100:
        raise ValueError("discount_percent must be between 0 and 99.99")
    return discount


def _resolve_minimum_charge(policy: PricingPolicy, override: float | None = None) -> float:
    minimum = float(policy.get("minimum_charge", 0.0)) if override is None else float(override)
    if minimum < 0:
        raise ValueError("minimum_charge must be >= 0")
    return minimum


def _round_half_hours(hours: float) -> float:
    return round(hours * 2.0) / 2.0


def _round_whole_dollars(value: float) -> float:
    return float(math.floor(value + 0.5))


def _resolve_waste_percent(
    policy: PricingPolicy,
    quote_type: str,
    override: float | None = None,
) -> float:
    if override is not None:
        waste = float(override)
    else:
        model = _cost_model(policy, quote_type)
        waste = float(model.get("default_waste_percent", 10.0))
    if waste < 0 or waste > 100:
        raise ValueError("waste_percent must be between 0 and 100")
    return waste


def _cost_model(policy: PricingPolicy, quote_type: str) -> Dict[str, float]:
    raw = policy.get("cost_model", {})
    if not isinstance(raw, dict):
        return {}
    model = raw.get(quote_type, {})
    if not isinstance(model, dict):
        return {}
    out: Dict[str, float] = {}
    for k, v in model.items():
        try:
            out[k] = float(v)
        except Exception:  # pylint: disable=broad-except
            continue
    return out


def _financials(
    cost: float, markup_multiplier: float, discount_percent: float, minimum_charge: float
) -> Dict[str, float]:
    customer_before_discount = cost * markup_multiplier
    discount_amount = customer_before_discount * (discount_percent / 100.0)
    customer_after_discount = customer_before_discount - discount_amount
    minimum_charge_applied = max(0.0, minimum_charge - customer_after_discount)
    customer_price = customer_after_discount + minimum_charge_applied
    profit = customer_price - cost
    return {
        "my_cost": cost,
        "markup_multiplier": markup_multiplier,
        "markup_percent": (markup_multiplier - 1.0) * 100.0,
        "customer_price_before_discount": customer_before_discount,
        "discount_percent": discount_percent,
        "discount_amount": discount_amount,
        "minimum_charge": minimum_charge,
        "minimum_charge_applied": minimum_charge_applied,
        "customer_price": customer_price,
        "profit": profit,
    }


def build_garment_matrix(data: PriceData) -> Dict[str, Dict[str, Dict[str, float | str]]]:
    matrix: Dict[str, Dict[str, Dict[str, float | str]]] = {}
    for key, entry in data["GARMENT"].items():
        product_type = str(entry.get("product_type", "")).lower()
        tier = str(entry.get("tier", "")).lower()
        if not product_type or not tier:
            continue
        matrix.setdefault(product_type, {})
        matrix[product_type][tier] = {"key": key, "label": str(entry.get("label", key)), "price": float(entry.get("price", 0))}
    return matrix


def build_garment_graphics_options(data: PriceData) -> Dict[str, Any]:
    front: Dict[str, Dict[str, Any]] = {}
    back: Dict[str, Dict[str, Any]] = {}
    for key, entry in data["GARMENT_GRAPHICS"].items():
        placement = str(entry.get("placement", "")).lower()
        target = front if placement == "front" else back if placement == "back" else None
        if target is None:
            continue
        target[key] = {
            "label": str(entry.get("label", key)),
            "price_1": float(entry.get("price_1", 0)),
            "price_2": float(entry.get("price_2", 0)),
            "price_3": float(entry.get("price_3", 0)),
            "price_dtf": float(entry.get("price_dtf", 0)),
        }
    return {"front": front, "back": back, "colors": ["1", "2", "3", "DTF"]}


def _graphics_price(entry: Dict[str, Any], colors: str) -> float:
    c = colors.strip().upper()
    if c == "1":
        return float(entry.get("price_1", 0))
    if c == "2":
        return float(entry.get("price_2", 0))
    if c == "3":
        return float(entry.get("price_3", 0))
    if c == "DTF":
        return float(entry.get("price_dtf", 0))
    raise ValueError("Graphics colors must be 1, 2, 3, or DTF.")


def suggest_power_supply_wattage(required_watts: float) -> float:
    target = required_watts * 1.2
    standard_sizes = [30, 60, 100, 150, 200, 300, 400, 600]
    for size in standard_sizes:
        if target <= size:
            return float(size)
    return float(int(math.ceil(target / 100.0) * 100))


def quote_led_addon(
    data: PriceData,
    led_type: str,
    linear_ft: float,
    color_mode: str,
    density: str = "",
    voltage: float = 0.0,
    controller_key: str = "",
) -> Dict[str, float | str]:
    led_type = led_type.lower().strip()
    color_mode = color_mode.lower().strip()
    density = density.lower().strip()

    if linear_ft <= 0:
        raise ValueError("LED linear feet must be greater than zero.")

    if led_type == "mods":
        candidates = [entry for entry in data["LED_MODS"].values() if str(entry.get("color_mode", "")).lower() == color_mode]
    elif led_type == "ribbon":
        candidates = [
            entry
            for entry in data["LED_RIBBON"].values()
            if str(entry.get("density", "")).lower() == density
            and str(entry.get("color_mode", "")).lower() == color_mode
            and int(float(entry.get("voltage", 0))) == int(voltage)
        ]
    else:
        raise ValueError("LED type must be mods or ribbon.")

    if not candidates:
        raise ValueError("No LED pricing configured for this LED option combination.")

    picked = min(candidates, key=lambda x: float(x.get("price_per_ft", 0)))
    price_per_ft = float(picked["price_per_ft"])
    watts_per_ft = float(picked["watts_per_ft"])
    led_voltage = float(picked["voltage"])
    led_cost = price_per_ft * linear_ft
    required_watts = watts_per_ft * linear_ft
    suggested_watts = suggest_power_supply_wattage(required_watts)

    controller_price = 0.0
    controller_label = "None"
    if color_mode in {"rgb", "argb"}:
        if controller_key not in data["CONTROLLER"]:
            raise ValueError("Controller is required for RGB/ARGB LED options.")
        controller_entry = data["CONTROLLER"][controller_key]
        controller_label = str(controller_entry["label"])
        controller_price = float(controller_entry["price"])

    total = led_cost + controller_price
    return {
        "led_type": led_type,
        "led_label": str(picked["label"]),
        "color_mode": color_mode,
        "density": density if led_type == "ribbon" else "",
        "voltage": led_voltage,
        "linear_ft": linear_ft,
        "price_per_ft": price_per_ft,
        "watts_per_ft": watts_per_ft,
        "required_watts": required_watts,
        "suggested_power_supply_watts": suggested_watts,
        "controller_label": controller_label,
        "controller_price": controller_price,
        "led_cost": led_cost,
        "total": total,
    }


def quote_sign(
    data: PriceData,
    material_key: str,
    process_type: str,
    process_key: str,
    width_in: float,
    height_in: float,
    quantity: int,
    led: Dict[str, Any] | None = None,
    pricing_policy: PricingPolicy | None = None,
    pricing_profile: str | None = None,
    markup_multiplier: float | None = None,
    discount_percent: float | None = None,
    labor_hours: float | None = None,
    labor_minutes: float | None = None,
    labor_rate_per_hour: float | None = None,
    waste_percent: float | None = None,
) -> Dict[str, Any]:
    process_type = process_type.upper()
    if process_type not in {"PRINT", "PLOT"}:
        raise ValueError("process_type must be PRINT or PLOT")
    if material_key not in data["MATERIAL"]:
        raise ValueError(f"Unknown material key: {material_key}")
    if process_key not in data[process_type]:
        raise ValueError(f"Unknown {process_type} key: {process_key}")
    if width_in <= 0 or height_in <= 0:
        raise ValueError("Width and height must be positive.")
    if quantity <= 0:
        raise ValueError("Quantity must be a positive integer.")

    material_price = float(data["MATERIAL"][material_key]["price"])
    process_price = float(data[process_type][process_key]["price"])
    sqft = (width_in * height_in) / 144.0
    material_hard_cost = material_price * sqft * quantity
    process_hard_cost = process_price * sqft * quantity
    base_total = material_hard_cost + process_hard_cost

    response: Dict[str, Any] = {
        "sqft": sqft,
        "material_price": material_price,
        "process_price": process_price,
        "per_sqft": material_price + process_price,
        "quantity": float(quantity),
        "base_total": base_total,
        "led_included": False,
        "led_total": 0.0,
        "cost_total": base_total,
        "pricing_profile": pricing_profile or str(
            (pricing_policy or DEFAULT_PRICING_POLICY).get("active_profile", "standard")
        ),
    }

    if led and bool(led.get("enabled")):
        led_quote = quote_led_addon(
            data,
            led_type=str(led.get("led_type", "")),
            linear_ft=float(led.get("linear_ft", 0)),
            color_mode=str(led.get("color_mode", "")),
            density=str(led.get("density", "")),
            voltage=float(led.get("voltage", 0)),
            controller_key=str(led.get("controller_key", "")),
        )
        response["led_included"] = True
        response["led"] = led_quote
        response["led_total"] = float(led_quote["total"])
        response["cost_total"] = base_total + float(led_quote["total"])

    policy = pricing_policy or DEFAULT_PRICING_POLICY
    sign_cost_model = _cost_model(policy, "sign")
    discount = _resolve_discount(policy, override=discount_percent)
    minimum_charge = _resolve_minimum_charge(policy)
    waste_percent_effective = _resolve_waste_percent(
        policy, "sign", override=waste_percent
    )

    led_hard_cost = float(response.get("led_total", 0.0))
    labor_rate = (
        float(labor_rate_per_hour)
        if labor_rate_per_hour is not None
        else float(sign_cost_model.get("labor_rate_per_hour", 65.0))
    )
    labor_rate = _round_whole_dollars(labor_rate)
    if labor_rate < 0:
        raise ValueError("labor_rate_per_hour must be >= 0")
    labor_minutes_sqft = float(
        sign_cost_model.get(
            "labor_minutes_per_sqft_print" if process_type == "PRINT" else "labor_minutes_per_sqft_plot",
            0.0,
        )
    )
    labor_minutes_led = float(sign_cost_model.get("led_labor_minutes_per_ft", 0.0))
    led_linear_ft = (
        float(response["led"]["linear_ft"])
        if bool(response.get("led_included")) and isinstance(response.get("led"), dict)
        else 0.0
    )
    model_labor = (
        ((labor_minutes_sqft * sqft * quantity) + (labor_minutes_led * led_linear_ft))
        / 60.0
    ) * labor_rate
    manual_hours_raw = max(0.0, float(labor_hours or 0.0)) + (
        max(0.0, float(labor_minutes or 0.0)) / 60.0
    )
    manual_hours_rounded = _round_half_hours(manual_hours_raw)
    manual_labor = manual_hours_rounded * labor_rate
    variable_labor = model_labor + manual_labor
    fixed_adders = float(sign_cost_model.get("setup_fee", 0.0)) + float(
        sign_cost_model.get("proof_fee", 0.0)
    )
    waste_adjustment = (
        (material_hard_cost + process_hard_cost + led_hard_cost)
        * (waste_percent_effective / 100.0)
    )
    hard_costs = material_hard_cost + process_hard_cost + led_hard_cost
    true_cost = hard_costs + variable_labor + fixed_adders + waste_adjustment
    response.update(
        {
            "cost_breakdown": {
                "hard_costs": hard_costs,
                "material_hard_cost": material_hard_cost,
                "process_hard_cost": process_hard_cost,
                "led_hard_cost": led_hard_cost,
                "variable_labor": variable_labor,
                "model_labor": model_labor,
                "manual_labor": manual_labor,
                "manual_labor_hours_raw": manual_hours_raw,
                "manual_labor_hours_rounded": manual_hours_rounded,
                "labor_rate_per_hour": labor_rate,
                "fixed_adders": fixed_adders,
                "waste_percent": waste_percent_effective,
                "waste_adjustment": waste_adjustment,
                "true_cost": true_cost,
            }
        }
    )
    response["cost_total"] = true_cost

    cost_total = float(response["cost_total"])
    if markup_multiplier is None and bool(response.get("led_included")):
        sign_markup = _resolve_markup(policy, "sign", profile_name=pricing_profile)
        led_markup = _resolve_markup(policy, "led", profile_name=pricing_profile)
        customer_before_discount = (
            (hard_costs - led_hard_cost + variable_labor + fixed_adders + waste_adjustment)
            * sign_markup
        ) + (
            led_hard_cost * led_markup
        )
        discount_amount = customer_before_discount * (discount / 100.0)
        customer_after_discount = customer_before_discount - discount_amount
        minimum_charge_applied = max(0.0, minimum_charge - customer_after_discount)
        customer_price = customer_after_discount + minimum_charge_applied
        response.update(
            {
                "my_cost": true_cost,
                "markup_multiplier": sign_markup,
                "markup_percent": (sign_markup - 1.0) * 100.0,
                "customer_price_before_discount": customer_before_discount,
                "discount_percent": discount,
                "discount_amount": discount_amount,
                "minimum_charge": minimum_charge,
                "minimum_charge_applied": minimum_charge_applied,
                "customer_price": customer_price,
                "profit": customer_price - true_cost,
                "sign_markup_multiplier": sign_markup,
                "led_markup_multiplier": led_markup,
            }
        )
    else:
        sign_markup = _resolve_markup(policy, "sign", override=markup_multiplier)
        financials = _financials(true_cost, sign_markup, discount, minimum_charge)
        response.update(financials)
    response["total"] = response["customer_price"]

    return response


def quote_shirt(data: PriceData, blank_key: str, decoration_key: str, quantity: int) -> Dict[str, float]:
    shirts = data["SHIRT"]
    if blank_key not in shirts or decoration_key not in shirts:
        raise ValueError("Unknown shirt key.")
    if quantity <= 0:
        raise ValueError("Quantity must be a positive integer.")
    blank_base = float(shirts[blank_key].get("base", 0))
    decoration_each = float(shirts[decoration_key].get("each", 0))
    per_shirt = blank_base + decoration_each
    total = per_shirt * quantity
    return {"blank_base": blank_base, "decoration_each": decoration_each, "per_shirt": per_shirt, "quantity": float(quantity), "total": total}


def quote_wholesale_subout(
    data: PriceData,
    item_key: str,
    quantity: int,
    width_in: float | None = None,
    height_in: float | None = None,
    linear_ft: float | None = None,
) -> Dict[str, float | str]:
    items = data["WHOLESALE_SUBOUT"]
    if item_key not in items:
        raise ValueError(f"Unknown wholesale subout key: {item_key}")
    if quantity <= 0:
        raise ValueError("Quantity must be a positive integer.")

    entry = items[item_key]
    unit = str(entry.get("unit", "")).lower()
    price = float(entry.get("price", 0.0))
    label = str(entry.get("label", item_key))
    group = str(entry.get("group", "Wholesale"))

    multiplier = float(quantity)
    sqft = 0.0
    linft_total = 0.0
    if unit == "sqft":
        if width_in is None or height_in is None or width_in <= 0 or height_in <= 0:
            raise ValueError("Width and height are required for sqft wholesale items.")
        sqft = (float(width_in) * float(height_in)) / 144.0
        multiplier = sqft * quantity
    elif unit == "linft":
        if linear_ft is None or linear_ft <= 0:
            raise ValueError("Linear ft is required for linft wholesale items.")
        linft_total = float(linear_ft) * quantity
        multiplier = linft_total
    elif unit == "each":
        multiplier = float(quantity)
    else:
        raise ValueError(f"Unsupported unit '{unit}' for wholesale item.")

    total = price * multiplier
    return {
        "item_key": item_key,
        "item_label": label,
        "group": group,
        "unit": unit,
        "price": price,
        "quantity": float(quantity),
        "width_in": float(width_in or 0.0),
        "height_in": float(height_in or 0.0),
        "sqft_each": sqft,
        "linear_ft_each": float(linear_ft or 0.0),
        "billable_units_total": multiplier,
        "total": total,
    }


def quote_garment(
    data: PriceData,
    product_type: str,
    tier: str,
    quantity: int,
    pricing_policy: PricingPolicy | None = None,
    pricing_profile: str | None = None,
    markup_multiplier: float | None = None,
    discount_percent: float | None = None,
    graphics: Dict[str, Any] | None = None,
    labor_hours: float | None = None,
    labor_minutes: float | None = None,
    labor_rate_per_hour: float | None = None,
    waste_percent: float | None = None,
) -> Dict[str, float | str]:
    product_type = product_type.lower().strip()
    tier = tier.lower().strip()
    if quantity <= 0:
        raise ValueError("Quantity must be a positive integer.")

    matrix = build_garment_matrix(data)
    if product_type not in matrix:
        raise ValueError(f"Unknown garment type: {product_type}")
    if tier not in matrix[product_type]:
        raise ValueError(f"Unknown tier '{tier}' for garment type '{product_type}'")

    choice = matrix[product_type][tier]
    price_each = float(choice["price"])
    graphics_cost_each = 0.0
    graphics_detail: Dict[str, Any] = {
        "enabled": False,
        "front_key": "front_none",
        "back_key": "back_none",
        "colors": "1",
        "front_cost_each": 0.0,
        "back_cost_each": 0.0,
    }
    if graphics and bool(graphics.get("enabled")):
        front_key = str(graphics.get("front_key", "")).strip()
        back_key = str(graphics.get("back_key", "")).strip()
        colors = str(graphics.get("colors", "1")).strip()
        graphics_options = data["GARMENT_GRAPHICS"]
        if front_key not in graphics_options:
            raise ValueError(f"Unknown front graphics key: {front_key}")
        if back_key not in graphics_options:
            raise ValueError(f"Unknown back graphics key: {back_key}")
        if str(graphics_options[front_key].get("placement", "")).lower() != "front":
            raise ValueError("Selected front graphics option is not a front placement.")
        if str(graphics_options[back_key].get("placement", "")).lower() != "back":
            raise ValueError("Selected back graphics option is not a back placement.")
        front_cost = _graphics_price(graphics_options[front_key], colors)
        back_cost = _graphics_price(graphics_options[back_key], colors)
        graphics_cost_each = front_cost + back_cost
        graphics_detail = {
            "enabled": True,
            "front_key": front_key,
            "front_label": str(graphics_options[front_key].get("label", front_key)),
            "back_key": back_key,
            "back_label": str(graphics_options[back_key].get("label", back_key)),
            "colors": colors.upper(),
            "front_cost_each": front_cost,
            "back_cost_each": back_cost,
            "graphics_cost_each": graphics_cost_each,
        }

    base_cost_total = price_each * quantity
    graphics_cost_total = graphics_cost_each * quantity
    hard_costs = base_cost_total + graphics_cost_total
    policy = pricing_policy or DEFAULT_PRICING_POLICY
    garment_cost_model = _cost_model(policy, "garment")
    garment_markup = _resolve_markup(
        policy, "garment", override=markup_multiplier, profile_name=pricing_profile
    )
    discount = _resolve_discount(policy, override=discount_percent)
    minimum_charge = _resolve_minimum_charge(policy)
    waste_percent_effective = _resolve_waste_percent(
        policy, "garment", override=waste_percent
    )
    labor_rate = (
        float(labor_rate_per_hour)
        if labor_rate_per_hour is not None
        else float(garment_cost_model.get("labor_rate_per_hour", 65.0))
    )
    labor_rate = _round_whole_dollars(labor_rate)
    if labor_rate < 0:
        raise ValueError("labor_rate_per_hour must be >= 0")
    labor_minutes_per_item = float(garment_cost_model.get("labor_minutes_per_item", 0.0))
    model_labor = ((labor_minutes_per_item * quantity) / 60.0) * labor_rate
    manual_hours_raw = max(0.0, float(labor_hours or 0.0)) + (
        max(0.0, float(labor_minutes or 0.0)) / 60.0
    )
    manual_hours_rounded = _round_half_hours(manual_hours_raw)
    manual_labor = manual_hours_rounded * labor_rate
    variable_labor = model_labor + manual_labor
    fixed_adders = float(garment_cost_model.get("setup_fee", 0.0)) + float(
        garment_cost_model.get("proof_fee", 0.0)
    )
    waste_adjustment = hard_costs * (waste_percent_effective / 100.0)
    true_cost = hard_costs + variable_labor + fixed_adders + waste_adjustment
    financials = _financials(true_cost, garment_markup, discount, minimum_charge)
    customer_price_each = financials["customer_price"] / quantity
    return {
        "product_type": product_type,
        "tier": tier,
        "label": str(choice["label"]),
        "price_each": price_each,
        "quantity": float(quantity),
        "base_cost_total": base_cost_total,
        "graphics_cost_total": graphics_cost_total,
        "graphics": graphics_detail,
        "cost_total": true_cost,
        "cost_breakdown": {
            "hard_costs": hard_costs,
            "base_hard_cost": base_cost_total,
            "graphics_hard_cost": graphics_cost_total,
            "variable_labor": variable_labor,
            "model_labor": model_labor,
            "manual_labor": manual_labor,
            "manual_labor_hours_raw": manual_hours_raw,
            "manual_labor_hours_rounded": manual_hours_rounded,
            "labor_rate_per_hour": labor_rate,
            "fixed_adders": fixed_adders,
            "waste_percent": waste_percent_effective,
            "waste_adjustment": waste_adjustment,
            "true_cost": true_cost,
        },
        "pricing_profile": pricing_profile
        or str(policy.get("active_profile", "standard")),
        "customer_price_each": customer_price_each,
        **financials,
        "total": financials["customer_price"],
    }


def build_led_ui_options(data: PriceData) -> Dict[str, Any]:
    mods_colors = sorted({str(v["color_mode"]) for v in data["LED_MODS"].values()})
    ribbon_densities = sorted({str(v["density"]) for v in data["LED_RIBBON"].values()})
    ribbon_colors = sorted({str(v["color_mode"]) for v in data["LED_RIBBON"].values()})
    ribbon_voltages = sorted({int(float(v["voltage"])) for v in data["LED_RIBBON"].values()})
    return {
        "mods_colors": mods_colors,
        "ribbon_densities": ribbon_densities,
        "ribbon_colors": ribbon_colors,
        "ribbon_voltages": ribbon_voltages,
        "controllers": data["CONTROLLER"],
    }


def build_wholesale_subout_options(data: PriceData) -> Dict[str, Dict[str, Any]]:
    entries = data.get("WHOLESALE_SUBOUT", {})
    sorted_items = sorted(
        entries.items(),
        key=lambda kv: (
            str(kv[1].get("group", "")).lower(),
            str(kv[1].get("label", "")).lower(),
        ),
    )
    return {k: dict(v) for k, v in sorted_items}


def build_options_payload(
    data: PriceData, warnings: List[str], pricing_policy: PricingPolicy | None = None
) -> Dict[str, Any]:
    policy = pricing_policy or DEFAULT_PRICING_POLICY
    profile_name = str(policy.get("active_profile", "standard"))
    profile = {}
    if isinstance(policy.get("profiles"), dict):
        profile = policy["profiles"].get(profile_name, {})
    return {
        "warnings": warnings,
        "material": data["MATERIAL"],
        "print": data["PRINT"],
        "plot": data["PLOT"],
        "garment": build_garment_matrix(data),
        "garment_graphics": build_garment_graphics_options(data),
        "led_ui": build_led_ui_options(data),
        "wholesale_subout": build_wholesale_subout_options(data),
        "harbor_frequent": data["HARBOR_FREQUENT"],
        "pricing_policy": {
            "active_profile": profile_name,
            "profile": profile,
            "profiles": policy.get("profiles", {}),
            "default_discount_percent": float(policy.get("default_discount_percent", 0.0)),
            "discount_options_percent": policy.get("discount_options_percent", [0, 5, 10, 15]),
            "minimum_charge": float(policy.get("minimum_charge", 0.0)),
            "cost_model": policy.get("cost_model", {}),
        },
    }


def _print_options(title: str, options: PriceBucket, price_field: str) -> None:
    print(f"\n{title}")
    for key, entry in options.items():
        print(f"  {key:12} | {entry['label']} (${float(entry[price_field]):.2f})")


def _prompt_key(prompt: str, options: PriceBucket) -> str:
    while True:
        value = input(prompt).strip()
        if value in options:
            return value
        print("Invalid key. Choose one from the list above.")


def _prompt_positive_float(prompt: str) -> float:
    while True:
        value = input(prompt).strip()
        try:
            num = float(value)
            if num <= 0:
                print("Please enter a number greater than zero.")
                continue
            return num
        except ValueError:
            print("Invalid number. Please try again.")


def _prompt_positive_int(prompt: str) -> int:
    while True:
        value = input(prompt).strip()
        try:
            num = int(value)
            if num <= 0:
                print("Please enter an integer greater than zero.")
                continue
            return num
        except ValueError:
            print("Invalid integer. Please try again.")


def run_sign_flow(data: PriceData) -> None:
    print("\nSIGN pricing selected.")
    _print_options("MATERIAL options:", data["MATERIAL"], "price")
    _print_options("PRINT options:", data["PRINT"], "price")
    _print_options("PLOT options:", data["PLOT"], "price")
    material_key = _prompt_key("Material key: ", data["MATERIAL"])
    process_type = ""
    while process_type not in {"PRINT", "PLOT"}:
        process_type = input("Process type (PRINT/PLOT): ").strip().upper()
        if process_type not in {"PRINT", "PLOT"}:
            print("Please enter PRINT or PLOT.")
    process_key = _prompt_key(f"{process_type} key: ", data[process_type])
    width_in = _prompt_positive_float("Width (inches): ")
    height_in = _prompt_positive_float("Height (inches): ")
    quantity = _prompt_positive_int("Quantity: ")
    quote = quote_sign(data, material_key, process_type, process_key, width_in, height_in, quantity)
    print(f"\nTotal: ${quote['total']:.2f}")


def run_cli_menu(data: PriceData, warnings: List[str]) -> None:
    for warning in warnings:
        print(f"[notice] {warning}")
    print("\nMenu")
    print("  SIGN")
    print("  GARMENT")
    choice = input("Choose product type: ").strip().upper()
    if choice == "SIGN":
        run_sign_flow(data)
    else:
        print("CLI GARMENT flow is not implemented; use --web for full workflow.")


class PricerHandler(BaseHTTPRequestHandler):
    price_data: PriceData = {}
    warnings: List[str] = []
    pricing_policy: PricingPolicy = DEFAULT_PRICING_POLICY
    dashboard_path = Path(__file__).with_name("dashboard.html")
    prices_page_path = Path(__file__).with_name("price_sheet.html")

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: int = 200) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise ValueError("Missing JSON body.")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON body.") from exc
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object.")
        return payload

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"/", "/dashboard.html"}:
            if self.dashboard_path.exists():
                html = self.dashboard_path.read_text(encoding="utf-8")
            else:
                html = "<h1>dashboard.html not found</h1>"
            self._send_html(html)
            return
        if path in {"/prices", "/price_sheet.html"}:
            if self.prices_page_path.exists():
                html = self.prices_page_path.read_text(encoding="utf-8")
            else:
                html = "<h1>price_sheet.html not found</h1>"
            self._send_html(html)
            return
        if path == "/api/options":
            self._send_json(
                200,
                build_options_payload(
                    self.price_data, list(self.warnings), self.pricing_policy
                ),
            )
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._read_json_body()
            if path == "/api/quote/sign":
                process_type = str(payload.get("process_type", "")).upper()
                result = quote_sign(
                    self.price_data,
                    material_key=str(payload.get("material_key", "")),
                    process_type=process_type,
                    process_key=str(payload.get("process_key", "")),
                    width_in=float(payload.get("width_in", 0)),
                    height_in=float(payload.get("height_in", 0)),
                    quantity=int(payload.get("quantity", 0)),
                    led=payload.get("led") if isinstance(payload.get("led"), dict) else None,
                    pricing_policy=self.pricing_policy,
                    pricing_profile=str(payload.get("pricing_profile", "")).strip() or None,
                    markup_multiplier=float(payload["markup_multiplier"]) if "markup_multiplier" in payload else None,
                    discount_percent=float(payload["discount_percent"]) if "discount_percent" in payload else None,
                    labor_hours=float(payload["labor_hours"]) if "labor_hours" in payload else None,
                    labor_minutes=float(payload["labor_minutes"]) if "labor_minutes" in payload else None,
                    labor_rate_per_hour=float(payload["labor_rate_per_hour"]) if "labor_rate_per_hour" in payload else None,
                    waste_percent=float(payload["waste_percent"]) if "waste_percent" in payload else None,
                )
                result["material_label"] = str(self.price_data["MATERIAL"][str(payload.get("material_key", ""))]["label"])
                result["process_label"] = str(self.price_data[process_type][str(payload.get("process_key", ""))]["label"])
                result["process_type"] = process_type
                self._send_json(200, result)
                return

            if path == "/api/quote/garment":
                result = quote_garment(
                    self.price_data,
                    product_type=str(payload.get("product_type", "")),
                    tier=str(payload.get("tier", "")),
                    quantity=int(payload.get("quantity", 0)),
                    pricing_policy=self.pricing_policy,
                    pricing_profile=str(payload.get("pricing_profile", "")).strip() or None,
                    markup_multiplier=float(payload["markup_multiplier"]) if "markup_multiplier" in payload else None,
                    discount_percent=float(payload["discount_percent"]) if "discount_percent" in payload else None,
                    graphics=payload.get("graphics") if isinstance(payload.get("graphics"), dict) else None,
                    labor_hours=float(payload["labor_hours"]) if "labor_hours" in payload else None,
                    labor_minutes=float(payload["labor_minutes"]) if "labor_minutes" in payload else None,
                    labor_rate_per_hour=float(payload["labor_rate_per_hour"]) if "labor_rate_per_hour" in payload else None,
                    waste_percent=float(payload["waste_percent"]) if "waste_percent" in payload else None,
                )
                self._send_json(200, result)
                return

            if path == "/api/quote/wholesale-subout":
                result = quote_wholesale_subout(
                    self.price_data,
                    item_key=str(payload.get("item_key", "")),
                    quantity=int(payload.get("quantity", 0)),
                    width_in=float(payload["width_in"]) if "width_in" in payload else None,
                    height_in=float(payload["height_in"]) if "height_in" in payload else None,
                    linear_ft=float(payload["linear_ft"]) if "linear_ft" in payload else None,
                )
                self._send_json(200, result)
                return

            self._send_json(404, {"error": "Not found"})
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:  # pylint: disable=broad-except
            self._send_json(500, {"error": f"Unexpected server error: {exc}"})


def run_web_dashboard(
    data: PriceData,
    warnings: List[str],
    pricing_policy: PricingPolicy,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    PricerHandler.price_data = data
    PricerHandler.warnings = warnings
    PricerHandler.pricing_policy = pricing_policy
    server = ThreadingHTTPServer((host, port), PricerHandler)
    print(f"Dashboard running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Pricer CLI and web dashboard")
    parser.add_argument("--web", action="store_true", help="Run the HTML dashboard server")
    parser.add_argument("--host", default="127.0.0.1", help="Web host (default localhost)")
    parser.add_argument("--port", type=int, default=8000, help="Web port (default 8000)")
    parser.add_argument("--sync-harbor", action="store_true", help="Sync prices.txt from Harbor mapping before start")
    parser.add_argument("--sync-only", action="store_true", help="Run sync and exit")
    parser.add_argument("--harbor-mapping", default="harbor_mapping.json", help="Mapping file for Harbor sync")
    args = parser.parse_args()

    if args.sync_harbor:
        from supplier_harbor import sync_harbor_to_prices

        result = sync_harbor_to_prices(
            mapping_path=args.harbor_mapping,
            prices_path="prices.txt",
            username=os.getenv("HARBOR_USERNAME"),
            password=os.getenv("HARBOR_PASSWORD"),
        )
        print(
            "Harbor sync complete. "
            f"Updated: {result['updated_count']} | "
            f"Frequents: {result.get('frequents_count', 0)} | "
            f"Errors: {result['error_count']}"
        )
        for err in result["errors"]:
            print(f"[sync-error] {err}")
        if args.sync_only:
            return

    data, warnings = load_prices("prices.txt")
    policy, policy_warnings = load_pricing_policy("pricing_policy.json")
    warnings.extend(policy_warnings)
    if args.web:
        run_web_dashboard(data, warnings, policy, host=args.host, port=args.port)
    else:
        run_cli_menu(data, warnings)


if __name__ == "__main__":
    main()

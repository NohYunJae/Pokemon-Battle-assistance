import csv
import os
import numpy as np

from .utils.nature_chart import nature_chart
DATA_DIR = os.path.join(os.path.expanduser("~"), "PokemonDATA")

def get_nature_modifiers(nature):
    return [1.0] + nature_chart.get(nature, [1.0]*5)

def calculate_stats(base_stats, IVs, SPs, lv, nature_mods):
    hp = int(base_stats[0] + SPs[0] + 75)
    other_stats = [
        int(np.floor((base + sp + 20) * nature))
        for base, sp, nature in zip(base_stats[1:], SPs[1:], nature_mods[1:])
    ]
    return [hp] + other_stats

def _safe_int(val, default=0):
    """빈 값이거나 숫자가 아닐 경우 안전하게 정수로 변환하는 헬퍼 함수"""
    try:
        if val is None:
            return default
        val_str = str(val).strip()
        val_str = val_str.replace("—", "0").replace("–", "0").replace("*", "")
        return int(val_str) if val_str != "" else default
    except (ValueError, TypeError):
        return default

# --- 포켓몬 데이터 메모리 캐시 ---
_POKEDEX_CACHE = None

def _load_pokedex_cache():
    global _POKEDEX_CACHE
    if _POKEDEX_CACHE is not None:
        return _POKEDEX_CACHE
    
    _POKEDEX_CACHE = {}
    data_path = os.path.join(DATA_DIR, "data")
    os.makedirs(data_path, exist_ok=True)
    csv_path = os.path.join(data_path, 'Pokedex.csv')
    
    if os.path.exists(csv_path):
        with open(csv_path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pkm_name = row.get("포켓몬", "").strip()
                if not pkm_name:
                    continue
                
                base_stats = [
                    _safe_int(row.get("체력")),
                    _safe_int(row.get("공격")),
                    _safe_int(row.get("방어")),
                    _safe_int(row.get("특수공격")),
                    _safe_int(row.get("특수방어")),
                    _safe_int(row.get("스피드"))
                ]
                type1 = row.get("타입1", "").strip()
                type2 = row.get("타입2", "").strip()
                _POKEDEX_CACHE[pkm_name] = {
                    "base_stats": base_stats,
                    "types": [type1, type2] if type2 else [type1]
                }
    return _POKEDEX_CACHE

def get_pokemon_stats(pokemon_name, nature, SPs, IVs=None, lv=50):
    cache = _load_pokedex_cache()
    pkm_data = cache.get(pokemon_name)
    
    if pkm_data is None:
        raise ValueError(f"{pokemon_name} 을(를) 찾을 수 없습니다.")
        
    base_stats = pkm_data["base_stats"]
    types = pkm_data["types"]
    type1 = types[0] if len(types) > 0 else ""
    type2 = types[1] if len(types) > 1 else ""

    IVs = IVs or [31] * 6
    nature_mods = get_nature_modifiers(nature)

    return calculate_stats(base_stats, IVs, SPs, lv, nature_mods), [type1, type2]
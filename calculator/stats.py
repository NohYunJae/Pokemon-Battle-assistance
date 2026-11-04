import numpy as np

from loader.data_loader import load_pokedex_cache
from .utils.nature_chart import nature_chart

pokedex_cache = load_pokedex_cache()

def get_nature_modifiers(nature):
  return [1.0] + nature_chart.get(nature, [1.0] * 5)


def calculate_stats(base_stats, IVs, SPs, lv, nature_mods):
  hp = int(base_stats[0] + SPs[0] + 75)
  other_stats = [
      int(np.floor((base + sp + 20) * nature))
      for base, sp, nature in zip(base_stats[1:], SPs[1:], nature_mods[1:])
  ]
  return [hp] + other_stats


def get_pokemon_stats(pokemon_name, nature, SPs, IVs=None, lv=50):
  pkm_data = pokedex_cache.get(pokemon_name)

  if pkm_data is None:
    raise ValueError(f"{pokemon_name} 을(를) 찾을 수 없습니다.")

  base_stats = pkm_data["base_stats"]
  types = pkm_data["types"]
  type1 = types[0] if len(types) > 0 else ""
  type2 = types[1] if len(types) > 1 else ""

  IVs = IVs or [31] * 6
  nature_mods = get_nature_modifiers(nature)

  return calculate_stats(base_stats, IVs, SPs, lv, nature_mods), [type1, type2]
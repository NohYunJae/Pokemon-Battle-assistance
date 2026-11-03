import csv
import os

DATA_DIR = os.path.join(os.path.expanduser("~"), "PokemonDATA", "data")


def _clean(val):
  """문자열의 앞뒤 공백 및 특수 공백(\xa0)을 제거합니다."""
  if isinstance(val, str):
    return val.replace("\xa0", "").strip()
  return val


class GameDataCache:
  _pokedex_cache = None
  _move_cache = None

  @classmethod
  def get_pokedex(cls):
    """포켓몬 도감 데이터 캐시 로드 및 반환"""
    if cls._pokedex_cache is not None:
      return cls._pokedex_cache

    cls._pokedex_cache = {}
    csv_path = os.path.join(DATA_DIR, "Pokedex.csv")

    if os.path.exists(csv_path):
      with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
          # 읽어온 행의 모든 키와 값에 공백 및 \xa0 제거 적용
          row = {_clean(k): _clean(v) for k, v in raw_row.items() if k is not None}

          name = row.get("포켓몬", "")
          if not name:
            continue

          base_stats = [
              cls._safe_int(row.get("체력")),
              cls._safe_int(row.get("공격")),
              cls._safe_int(row.get("방어")),
              cls._safe_int(row.get("특수공격")),
              cls._safe_int(row.get("특수방어")),
              cls._safe_int(row.get("스피드")),
          ]
          type1 = row.get("타입1", "")
          type2 = row.get("타입2", "")
          types = [t for t in [type1, type2] if t]

          cls._pokedex_cache[name] = {
              "base_stats": base_stats,
              "stats": base_stats,  # 호환성 유지용
              "types": types,
          }
    return cls._pokedex_cache

  @classmethod
  def get_move_dict(cls):
    """기술 데이터 딕셔너리 캐시 로드 및 반환"""
    if cls._move_cache is not None:
      return cls._move_cache

    cls._move_cache = {}
    csv_path = os.path.join(DATA_DIR, "PokeMove.csv")

    if os.path.exists(csv_path):
      with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
          # 읽어온 행의 모든 키와 값에 공백 및 \xa0 제거 적용
          row = {_clean(k): _clean(v) for k, v in raw_row.items() if k is not None}

          name = row.get("이름", "")
          if not name:
            continue

          try:
            power_raw = row.get("위력", "")
            power_raw = (
                power_raw.replace("—", "0").replace("–", "0").replace("*", "")
            )
            power = int(power_raw) if power_raw != "" else 0
          except (ValueError, TypeError, AttributeError):
            power = 0

          cls._move_cache[name] = {
              "name": name,
              "type": row.get("타입", "노말"),
              "power": power,
              "category": row.get("분류", "물리"),
              "contact": row.get("접촉여부", ""),
          }
    return cls._move_cache

  @classmethod
  def get_pokedex_names(cls):
    """포켓몬 이름 리스트 반환"""
    return list(cls.get_pokedex().keys())

  @classmethod
  def get_move_names(cls):
    """기술 이름 리스트 반환"""
    return list(cls.get_move_dict().keys())

  @classmethod
  def clear_cache(cls):
    """데이터가 변경되었을 때 캐시를 초기화하고 다시 로드"""
    cls._pokedex_cache = None
    cls._move_cache = None

  @staticmethod
  def _safe_int(val, default=0):
    try:
      if val is None:
        return default
      cleaned = _clean(val)
      val_str = (
          str(cleaned).replace("—", "0").replace("–", "0").replace("*", "")
      )
      return int(val_str) if val_str != "" else default
    except (ValueError, TypeError):
      return default
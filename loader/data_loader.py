import csv
import os

DATA_DIR = os.path.join(os.path.expanduser("~"), "PokemonDATA")


def _clean(val):
  """문자열의 앞뒤 공백 및 특수 공백(\xa0)을 제거합니다."""
  if isinstance(val, str):
    return val.replace("\xa0", "").strip()
  return val


class PokemonCSVLoader:
  """샘플 CSV 파일로부터 포켓몬 데이터를 불러오는 클래스"""
  """Data list : 포켓몬, 타입, 성격, SPs, IVs, 기술, 종족치, 실수치, 지닌도구, 특성"""

  @staticmethod
  def load_pokemon_data(file_path):
    data = {}

    if not file_path.endswith(".csv"):
      file_path += ".csv"

    file_path = os.path.join(DATA_DIR, file_path)

    if not os.path.exists(file_path):
      raise FileNotFoundError(f"샘플 파일이 없습니다: {file_path}")

    with open(file_path, encoding="utf-8-sig") as f:
      reader = csv.reader(f)
      for row in reader:
        if not row:
          continue

        # 행 전체의 값들에 공백 및 \xa0 제거 적용
        row = [_clean(cell) for cell in row]
        key = row[0]

        if key == "포켓몬":
          data["포켓몬"] = row[1]
        elif key == "타입":
          data["타입"] = row[1:]
        elif key == "날씨":
          data["날씨"] = row[1]
        elif key == "필드":
          data["필드"] = row[1]
        elif key == "노트":
          data["노트"] = row[1]
        elif key == "지닌도구":
          data["지닌도구"] = row[1]
        elif key == "특성":
          data["특성"] = row[1]
        elif key == "성격":
          data["성격"] = row[1]
        elif key == "LV":
          data["LV"] = int(row[1])
        elif key == "SPs":
          data["SPs"] = list(map(int, row[1:]))
        elif key == "IVs":
          data["IVs"] = list(map(int, row[1:]))
        elif key == "기술":
          data["기술"] = row[1:]
        elif key == "종족치":
          data["종족치"] = list(map(lambda x: int(float(x)), row[1:]))
        elif key == "실수치":
          data["실수치"] = list(map(int, row[1:]))

    return data


class Move:
  """CSV 파일로부터 기술 데이터를 불러와 딕셔너리로 반환"""
  """기술이름, 파워, 카테고리, 타입, 접촉여부"""

  def __init__(self, name, type_, power, category, contact):
    self.name = name
    self.type = type_
    self.power = power
    self.category = category
    self.contact = contact

  @staticmethod
  def load_move_dict(csv_path=None):
    if csv_path is None:
      csv_path = os.path.join(DATA_DIR, "data", "PokeMove.csv")

    if not os.path.isfile(csv_path):
      raise FileNotFoundError(f"기술 CSV 파일을 찾을 수 없습니다: {csv_path}")

    move_dict = {}

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
      reader = csv.DictReader(f)

      for row in reader:
        # DictReader의 키와 값 모두 공백 및 \xa0 제거
        row = {_clean(k): _clean(v) for k, v in row.items() if k is not None}

        name = row.get("이름", "")

        try:
          power_raw = row.get("위력", "")
          power_raw = (
              power_raw.replace("—", "0").replace("–", "0").replace("*", "")
          )
          power = int(power_raw) if power_raw != "" else 0
        except (ValueError, TypeError, AttributeError):
          power = 0

        move = Move(
            name=name,
            type_=row.get("타입", ""),
            power=power,
            category=row.get("분류", ""),
            contact=row.get("접촉여부", ""),
        )

        move_dict[name] = move

    return move_dict
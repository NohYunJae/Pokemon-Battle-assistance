import os
import csv
import math

from pokemon import Pokemon
from battle import Simulator
DATA_DIR = os.path.join(os.path.expanduser("~"), "PokemonDATA")

def load_pokedex(name, pokedex_csv):
    with open(pokedex_csv, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row["포켓몬"] == name:
                stats = [
                    int(row["체력"]),
                    int(row["공격"]),
                    int(row["방어"]),
                    int(row["특수공격"]),
                    int(row["특수방어"]),
                    int(row["스피드"])
                ]
                type1 = row.get("타입1", "")
                type2 = row.get("타입2", "")
                
                return {
                    "stats": stats,
                    "types": [t for t in [type1, type2] if t]
                }

    raise ValueError(f"'{name}' 포켓몬이 Pokedex.csv에 없습니다.")

class SampleCSVbuilder:
    @staticmethod
    def make_sample_csv(
        filename,
        name,
        note,
        item,
        ability,
        nature,
        level,
        SPs,
        IVs,
        moves,
        weather,
        field,
        pokedex_csv="Pokedex.csv"
    ):
        sample_path = os.path.join(DATA_DIR, 'data', 'samples')
        os.makedirs(sample_path, exist_ok=True)
        if not filename.endswith(".csv"):
            filename += ".csv"
        file_path = os.path.join(sample_path, filename)

        if os.path.exists(file_path):
            base_path, ext = os.path.splitext(file_path)
            counter = 1
            while True:
                file_path = f"{base_path}({counter}){ext}"
                if not os.path.exists(file_path):
                    break
                counter += 1

        pokedex_csv = os.path.join(DATA_DIR, "data", 'Pokedex.csv')
        pokemon_data = load_pokedex(name, pokedex_csv)
        base_stats = pokemon_data["stats"]
        types = pokemon_data["types"]

        pkm = Pokemon(name, nature, SPs, IVs, level, item, ability)

        damages = []
        for move_name in moves:
            move = Pokemon.move_dict.get(move_name, {"type": "노말", "category": "물리", "power": 0})
            fpower = pkm.calculate_DMG_output(move, field, weather)
            damages.append(fpower)

        bulk = pkm.calculate_bulk(weather)
        if pkm.item == "구애스카프":
            spd = pkm.stats[5] * 3 // 2
        elif pkm.ability == "곡예":
            spd = pkm.stats[5] * 2
        else:
            spd = pkm.stats[5]

        def calculate_speed(base: int, nature_mod: float = 1.0, is_scarf: bool = False) -> int:
            base_calc = base + 52
            speed = math.floor(base_calc * nature_mod)
            return math.floor(speed * 1.5) if is_scarf else speed

        def find_out_run(target_actual_speed: int) -> list:
            results = []
            for nature_mod, is_scarf in [(1.0, False), (1.1, False), (1.0, True), (1.1, True)]:
                max_base = None
                for base in range(1, 201):
                    if calculate_speed(base, nature_mod, is_scarf) < target_actual_speed:
                        if max_base is None or base > max_base:
                            max_base = base
                results.append(max_base)
            return results
        
        weather = weather or ""
        field = field or ""
        with open(file_path, mode="w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["포켓몬", name])
            writer.writerow(["타입"] + types)
            writer.writerow(["노트", note])
            writer.writerow(["지닌도구", item])
            writer.writerow(["특성", ability])
            writer.writerow(["LV", level])
            writer.writerow(["성격", nature])
            writer.writerow([""] + ["HP","A","B","C","D","SPD"])
            writer.writerow(["종족치"] + base_stats)
            writer.writerow(["SPs"] + SPs)
            writer.writerow(["IVs"] + IVs)
            writer.writerow(["실수치"] + pkm.stats)
            writer.writerow(["날씨", weather])
            writer.writerow(["필드", field])
            writer.writerow(["기술"] + moves)
            writer.writerow(["DMG"] + damages)
            writer.writerow(["", "물리", "특수"])
            writer.writerow(["BULK", bulk[0], bulk[1]])
            writer.writerow([""] + ["무보정", "준속", "최속", "준속 스카프", "최속스카프"])
            writer.writerow(["속도 추월 라인"] + [spd-21] + find_out_run(spd))

        return file_path
        
class BattleCSVbuilder:
    def __init__(self, sample1, sample2):
        self.simulator = Simulator(sample1, sample2)
        self.output_path = "result_path"

    def write_battle_sheet(self, result_file):
        output_dir = os.path.join(DATA_DIR, 'data', 'Battle_Results')
        os.makedirs(output_dir, exist_ok=True)
        if not result_file.endswith(".csv"):
            result_file += ".csv"

        file_path = os.path.join(output_dir, result_file)

        if os.path.exists(file_path):
            base_name, ext = os.path.splitext(result_file)
            counter = 1
            while True:
                new_filename = f"{base_name}({counter}){ext}"
                file_path = os.path.join(output_dir, new_filename)
                if not os.path.exists(file_path):
                    break
                counter += 1

        self.output_path = file_path

        pkm1_data, pkm2_data, damage_table1, damage_table2 = self.simulator.make_battle_table()

        def pad_list(lst, target_len, default=""):
            """리스트가 지정된 길이보다 짧으면 default 값으로 채워서 반환합니다."""
            return list(map(str, lst)) + [default] * (target_len - len(lst))


        # 1. 기본 정보 행 정의 (라벨, pkm1 키, pkm2 키)
        simple_fields = [
            ("포켓몬", "포켓몬", "포켓몬"),
            ("날씨", "날씨", "날씨"),
            ("필드", "필드", "필드"),
            ("노트", "노트", "노트"),
            ("지닌도구", "지닌도구", "지닌도구"),
            ("특성", "특성", "특성"),
            ("LV", "LV", "LV"),
            ("성격", "성격", "성격"),
        ]

        battle_result = []
        battle_result.append(["포켓몬1", pkm1_data["포켓몬"], "", "", "", "", "", "", "포켓몬2", pkm2_data["포켓몬"], "", "", "", ""])
        battle_result.append(
            ["타입"] + pad_list(pkm1_data["타입"], 6) + [""] + 
            ["타입"] + pad_list(pkm2_data["타입"], 7)
        )

        # 단일 값 필드들 생성
        for label, k1, k2 in simple_fields:
            if label == "포켓몬": 
                continue
            v1 = pkm1_data.get(k1, "")
            v2 = pkm2_data.get(k2, "")
            battle_result.append([label, v1] + [""] * 6 + [label, v2] + [""] * 6)

        list_fields = ["종족치", "SPs", "IVs", "실수치"]
        for field in list_fields:
            p1_padded = pad_list(pkm1_data[field], 6)
            p2_padded = pad_list(pkm2_data[field], 6)
            
            battle_result.append([field] + p1_padded + [""] + [field] + p2_padded)

        battle_result.append(["기술"] + [""] * 7 + ["기술"])
        max_len = max(len(damage_table1), len(damage_table2))

        for i in range(max_len):
            row = []

            # Pokemon1
            if i < len(damage_table1):
                move1 = damage_table1[i]
                row += [move1[0], "Damage"] + [f"{v}%" for v in move1[2:]] + [""] * 2
            else:
                row += [""] * 8

            # Pokemon2
            if i < len(damage_table2):
                move2 = damage_table2[i]
                row += [move2[0], "Damage"] + [f"{v}%" for v in move2[2:]]
            else:
                row += [""] * 7

            battle_result.append(row)

            rand_row = ["", "난수"] + ["85", "90", "95", "100"] + [""] * 2
            rand_row += ["", "난수"] + ["85", "90", "95", "100"]
            battle_result.append(rand_row)

            battle_result.append([""] * 14)

        with open(self.output_path, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerows(battle_result)
        print(f"배틀 시트가 {self.output_path}에 저장되었습니다.")


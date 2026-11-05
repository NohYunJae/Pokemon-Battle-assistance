import os

from pochamps_list import pochamps_pokemon_list
from loader.data_loader import PokemonCSVLoader, Move, load_pokedex_cache
from pokemon import Pokemon
from calculator.utils.type_chart import type_chart

DATA_DIR = os.path.join(os.path.expanduser("~"), "PokemonDATA", "data")
pokedex_cache = load_pokedex_cache()

class TeamAnalyzer:
    """포켓몬 파티 분석 클래스"""
    def __init__(self, sample_names, move_csv="PokeMove.csv"):
        """sample_names: 분석할 6마리의 샘플 파일 이름 리스트"""
        self.move_dict = Move.load_move_dict(os.path.join(DATA_DIR, move_csv))
        self.party = []

        for poke_sample in sample_names:
            data = PokemonCSVLoader.load_pokemon_data(os.path.join(DATA_DIR, "samples", poke_sample))
            self.party.append(data)

    def get_main_moves(self, sample):
        """결정력 계산 및 주력기/보조기 선정 로직"""
        pkm = Pokemon(sample["포켓몬"], sample["성격"], sample["SPs"], sample["IVs"], 
                    lv = 50, item=sample.get("지닌도구"), ability=sample.get("특성"))

        main_list = []
        sub_list = []
        for move_name in sample["기술"]:
            if not move_name or move_name not in self.move_dict:
                continue

            move_obj = self.move_dict[move_name]
            power = move_obj.power

            if power == 0:
                continue
            
            dmg_output = pkm.calculate_DMG_output(move_obj, sample["필드"], sample["날씨"])

            main_moves = {}
            sub_moves = {}

            if dmg_output >= 32000:
                main_moves[move_obj.name] = (move_obj.type, dmg_output, move_obj.category)
            else:
                sub_moves[move_obj.name] = (move_obj.type, dmg_output, move_obj.category)

            main_list.append([
                {"기술명": name, "기술타입": info[0], "데미지": info[1], "카테고리": info[2]}
                for name, info in main_moves.items()
            ])

            sub_list.append([
                {"기술명": name, "기술타입": info[0], "데미지": info[1], "카테고리": info[2]}
                for name, info in sub_moves.items()
            ])

        return {"주력기목록": main_list, "보조기목록": sub_list}

    def _get_type_multiplier(self, atk_type, def_types):
        """공격 타입과 방어 포켓몬의 타입들(복합 타입 포함)을 받아 최종 상성 배율을 계산"""
        multiplier = 1.0
        for def_type in def_types:
            if def_type and atk_type in type_chart:
                mult = type_chart[atk_type].get(def_type, 1.0)
                multiplier *= mult
        return multiplier

    def analyze_party_offense(self):
        """주력기 및 보조기 결정력 검증, 1배 결정력 4만 이상 고려 약점 타격 불가 조합 분석"""
        main_types = set()
        sub_types = set()
        category_counts = {"물리": 0, "특수": 0, "변화": 0}
        
        all_party_moves = []

        for i in range(len(self.party)):
            mvs = self.get_main_moves(self.party[i])
            
            for item_list in mvs["주력기목록"]:
                for move in item_list:
                    main_types.add(move["기술타입"])
                    cat = move["카테고리"]
                    if cat in category_counts:
                        category_counts[cat] += 1
                    all_party_moves.append({
                        "기술명": move["기술명"],
                        "기술타입": move["기술타입"],
                        "데미지": move["데미지"]
                    })

            for item_list in mvs["보조기목록"]:
                for move in item_list:
                    sub_types.add(move["기술타입"])
                    cat = move["카테고리"]
                    if cat in category_counts:
                        category_counts[cat] += 1
                    all_party_moves.append({
                        "기술명": move["기술명"],
                        "기술타입": move["기술타입"],
                        "데미지": move["데미지"]
                    })

        type_to_moves = {}
        for sample in self.party:
            mvs = self.get_main_moves(sample)
            for item_list in mvs["주력기목록"]:
                for move in item_list:
                    t = move["기술타입"]
                    name = move["기술명"]
                    if t not in type_to_moves:
                        type_to_moves[t] = set()
                    type_to_moves[t].add(name)
            for item_list in mvs["보조기목록"]:
                for move in item_list:
                    t = move["기술타입"]
                    name = move["기술명"]
                    if t not in type_to_moves:
                        type_to_moves[t] = set()
                    type_to_moves[t].add(f"(보조){name}")

        formatted_type_to_moves = {atk_type: list(names) for atk_type, names in type_to_moves.items()}

        total_moves = sum(category_counts.values())
        category_ratios = {}
        if total_moves > 0:
            for cat, count in category_counts.items():
                if count > 0:
                    category_ratios[cat] = {
                        "개수": count,
                        "비율(%)": round((count / total_moves) * 100, 1)
                    }
        
        all_types = list(type_chart.keys())
        unweakened_combinations = []
        checked_combinations = set()

        for t1 in all_types:
            comb = (t1,)
            if self._is_completely_unweakened(comb, all_party_moves):
                unweakened_combinations.append(comb)

            for t2 in all_types:
                if t1 != t2:
                    comb = tuple(sorted([t1, t2]))
                    if comb not in checked_combinations:
                        checked_combinations.add(comb)
                        if self._is_completely_unweakened(comb, all_party_moves):
                            unweakened_combinations.append(comb)

        return {
            "type_to_moves": formatted_type_to_moves,
            "category_ratios": category_ratios,
            "unweakened_combinations": unweakened_combinations
        }
    
    def _is_completely_unweakened(self, def_combo, all_party_moves):
        """방어 타입 조합에 대한 파티 기술 대처 여부 확인"""
        if not all_party_moves:
            return True

        for move in all_party_moves:
            atk_type = move["기술타입"]
            dmg = move["데미지"]
            mult = self._get_type_multiplier(atk_type, def_combo)

            if mult >= 2.0 and dmg > 26500:
                return False
            
            if mult == 1.0 and dmg >= 43000:
                return False
        
        return True

    def analyze_party_defense(self):
        """파티 방어 상성 분석: 파티원 절반 초과 기준 약점 및 반감 불가 타입 분석"""
        total_party_size = len(self.party)
        threshold = total_party_size / 2

        all_attack_types = list(type_chart.keys())
        
        weakness_counts = {}
        not_resisted_counts = {} 

        for idx, sample in enumerate(self.party):
            def_types = sample.get("타입", [])

            for atk_type in all_attack_types:
                mult = self._get_type_multiplier(atk_type, def_types)
                
                if mult >= 2.0:
                    weakness_counts[atk_type] = weakness_counts.get(atk_type, 0) + 1
                
                if mult >= 1.0:
                    not_resisted_counts[atk_type] = not_resisted_counts.get(atk_type, 0) + 1

        common_weaknesses = {k: v for k, v in weakness_counts.items() if v >= threshold}
        sorted_weaknesses = sorted(common_weaknesses.items(), key=lambda x: x[1], reverse=True)

        common_not_resisted = {k: v for k, v in not_resisted_counts.items() if v > threshold}
        sorted_not_resisted = sorted(common_not_resisted.items(), key=lambda x: x[1], reverse=True)

        return {
            "common_weaknesses": dict(sorted_weaknesses),
            "common_not_resisted": dict(sorted_not_resisted)
        }

class PokemonSelector:
    """파티 보완 포켓몬 추천 클래스"""
    def __init__(self):
        self.pochampslst = pochamps_pokemon_list

    def recommend_pokemon(self, party_samples):
        """파티 보완 포켓몬 추천 로직 (파티원 전원이 반감하지 못하는 타입을 약점으로 갖는 포켓몬 제외)"""
        analyzer = TeamAnalyzer(party_samples)
        defense_result = analyzer.analyze_party_defense()
        common_weaknesses = defense_result["common_weaknesses"]
        common_not_resisted = defense_result["common_not_resisted"]
        
        existing_party_types = [sample.get("타입", []) for sample in analyzer.party]
        new_party_size = len(analyzer.party) + 1
        new_threshold = new_party_size / 2
        all_attack_types = list(type_chart.keys())

        # 💡 핵심 추가: 현재 파티원 '그 누구도' 반감(1배 미만)시키지 못하는 타입들을 파악
        # (즉, 파티 내 모든 포켓몬의 상성 배율이 1.0 이상인 타입들)
        completely_unresisted_types = set()
        for atk_type in all_attack_types:
            all_fail_to_resist = all(
                analyzer._get_type_multiplier(atk_type, def_types) >= 1.0
                for def_types in existing_party_types
            )
            if all_fail_to_resist:
                completely_unresisted_types.add(atk_type)

        general_recommendations = []
        mega_recommendations = []
        
        for poke_name in self.pochampslst:
            if poke_name not in pokedex_cache:
                continue
            
            poke_data = pokedex_cache[poke_name]
            poke_types = poke_data.get("types", [])

            # 1. 기존 공통 약점 타입에 대해 후보 포켓몬이 2배 이상(약점) 찔리는지 확인 -> 제외
            has_common_weakness = any(
                analyzer._get_type_multiplier(atk_type, poke_types) >= 2.0
                for atk_type in common_weaknesses.keys()
            )
            if has_common_weakness:
                continue

            # 2. 후보 포켓몬을 포함했을 때 새로운 과반수 이상의 공통 약점이 생기는지 확인 -> 제외
            introduces_new_common_weakness = False
            for atk_type in all_attack_types:
                weak_count = sum(
                    1 for def_types in existing_party_types 
                    if analyzer._get_type_multiplier(atk_type, def_types) >= 2.0
                )
                if analyzer._get_type_multiplier(atk_type, poke_types) >= 2.0:
                    weak_count += 1
                
                if weak_count >= new_threshold:
                    introduces_new_common_weakness = True
                    break
            
            if introduces_new_common_weakness:
                continue

            # 🚨 3. 추가 조건: 파티원 전원이 반감하지 못하는 타입(completely_unresisted_types)을
            # 후보 포켓몬이 약점(2배 이상)으로 잡히는 경우 -> 제외
            has_fatal_blindspot_weakness = any(
                analyzer._get_type_multiplier(atk_type, poke_types) >= 2.0
                for atk_type in completely_unresisted_types
            )
            if has_fatal_blindspot_weakness:
                continue

            # 4. 1순위와 2순위 보완 능력 개수(점수) 계산
            covered_weaknesses = [
                atk_type for atk_type in common_weaknesses.keys()
                if analyzer._get_type_multiplier(atk_type, poke_types) < 1.0
            ]
            
            covered_not_resisted = [
                atk_type for atk_type in common_not_resisted.keys()
                if atk_type not in common_weaknesses and analyzer._get_type_multiplier(atk_type, poke_types) < 1.0
            ]

            total_covered = covered_weaknesses + covered_not_resisted
            if total_covered:
                item = {
                    "name": poke_name,
                    "types": poke_types,
                    "covered_types": total_covered,
                    "weakness_score": len(covered_weaknesses),      
                    "not_resisted_score": len(covered_not_resisted) 
                }

                if poke_name.startswith("메가") and poke_name != "메가니움":
                    mega_recommendations.append(item)
                else:
                    general_recommendations.append(item)

        sort_key = lambda x: (x["weakness_score"], x["not_resisted_score"], x["name"])
        
        general_recommendations.sort(key=sort_key, reverse=True)
        mega_recommendations.sort(key=sort_key, reverse=True)
        
        return general_recommendations[:50], mega_recommendations[:50], common_weaknesses, common_not_resisted


if __name__ == "__main__":
    test_samples = [
        "트릭룸카디나르마", 
        "스카프에써르", 
        "트릭룸메갑주",
        "HD하마돈샘플",
        "배북마릴리",
        "조심특수만다"
    ]
    
    print("=== [방어 보완 포켓몬 추천 및 파티 취약 타입 분석] ===")
    try:
        selector = PokemonSelector()
        general_top50, mega_top50, common_weaknesses, common_not_resisted = selector.recommend_pokemon(test_samples)
        
        print("\n[파티 방어 취약 타입 분석 현황]")
        print("  • 공통 약점 타입 (1순위 보완 대상):")
        if common_weaknesses:
            for w_type, cnt in common_weaknesses.items():
                print(f"    - {w_type}: {cnt}마리")
        else:
            print("    - 없음")
            
        print("  • 반감 불가 타입 (2순위 보완 대상):")
        if common_not_resisted:
            for nr_type, cnt in common_not_resisted.items():
                print(f"    - {nr_type}: {cnt}마리")
        else:
            print("    - 없음")

        print(f"\n✨ [일반 포켓몬] 방어 보완 추천 상위 {len(general_top50)}마리:\n")
        if general_top50:
            for idx, item in enumerate(general_top50, 1):
                p_name = item["name"]
                p_types = '/'.join(item["types"])
                c_types = ', '.join(item["covered_types"])
                print(f"  {idx:2d}. [{p_name}] (방어 타입: {p_types})")
                print(      f"      🛡️ 보완한 취약 타입: {c_types} (공통약점 보완: {item['weakness_score']}개 / 반감불가 보완: {item['not_resisted_score']}개)")
                print("-" * 75)
        else:
            print("  - 조건을 만족하는 일반 포켓몬이 없습니다.")

        print(f"\n✨ [메가진화 포켓몬] 방어 보완 추천 상위 {len(mega_top50)}마리:\n")
        if mega_top50:
            for idx, item in enumerate(mega_top50, 1):
                p_name = item["name"]
                p_types = '/'.join(item["types"])
                c_types = ', '.join(item["covered_types"])
                print(f"  {idx:2d}. [{p_name}] (방어 타입: {p_types})")
                print(      f"      🛡️ 보완한 취약 타입: {c_types} (공통약점 보완: {item['weakness_score']}개 / 반감불가 보완: {item['not_resisted_score']}개)")
                print("-" * 75)
        else:
            print("  - 조건을 만족하는 메가진화 포켓몬이 없습니다.")
            
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        print("'PokemonDATA/data/samples/' 경로에 해당 샘플 파일들이 정상적으로 위치해 있는지 확인해 주세요.")
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
                weakness_types = [
                    atk for atk in all_types 
                    if self._get_type_multiplier(atk, comb) >= 2.0
                ]
                unweakened_combinations.append({
                    "combination": comb,
                    "weakness_types": weakness_types
                })

            for t2 in all_types:
                if t1 != t2:
                    comb = tuple(sorted([t1, t2]))
                    if comb not in checked_combinations:
                        checked_combinations.add(comb)
                        if self._is_completely_unweakened(comb, all_party_moves):
                            weakness_types = [
                                atk for atk in all_types 
                                if self._get_type_multiplier(atk, comb) >= 2.0
                            ]
                            unweakened_combinations.append({
                                "combination": comb,
                                "weakness_types": weakness_types
                            })

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
    """파티 보완 포켓몬 추천 클래스 (필터 함수화 및 점수 부여 방식)"""
    def __init__(self):
        self.pochampslst = pochamps_pokemon_list

    def recommend_pokemon(self, party_samples):
        analyzer = TeamAnalyzer(party_samples)
        defense_result = analyzer.analyze_party_defense()
        common_weaknesses = defense_result["common_weaknesses"]
        common_not_resisted = defense_result["common_not_resisted"]
        
        existing_party_types = [sample.get("타입", []) for sample in analyzer.party]
        new_party_size = len(analyzer.party) + 1
        new_threshold = new_party_size / 2
        all_attack_types = list(type_chart.keys())

        completely_unresisted_types = set()
        for atk_type in all_attack_types:
            all_fail_to_resist = all(
                analyzer._get_type_multiplier(atk_type, def_types) >= 1.0
                for def_types in existing_party_types
            )
            if all_fail_to_resist:
                completely_unresisted_types.add(atk_type)

        # 1단계 필터 함수: 기존 공통 약점 보유 여부 확인 (True면 안전)
        def eval_filter_1(poke_types):
            has_weakness = any(
                analyzer._get_type_multiplier(atk_type, poke_types) >= 2.0 
                for atk_type in common_weaknesses.keys()
            )
            return not has_weakness

        # 2단계 필터 함수: 새로운 공통 약점 유발 여부 확인 (True면 안전)
        def eval_filter_2(poke_types):
            for atk_type in all_attack_types:
                weak_count = sum(
                    1 for def_types in existing_party_types 
                    if analyzer._get_type_multiplier(atk_type, def_types) >= 2.0
                )
                if analyzer._get_type_multiplier(atk_type, poke_types) >= 2.0:
                    weak_count += 1
                if weak_count >= new_threshold:
                    return False
            return True

        # 3단계 필터 함수: 치명적 사각지대 약점 보유 여부 확인 (True면 안전)
        def eval_filter_3(poke_types):
            has_blindspot_weakness = any(
                analyzer._get_type_multiplier(atk_type, poke_types) >= 2.0 
                for atk_type in completely_unresisted_types
            )
            return not has_blindspot_weakness

        general_recommendations = []
        mega_recommendations = []
        
        # 가중치 설정 (필터 통과 점수 및 커버 점수)
        FILTER_PASS_SCORE = 5.0    # 필터 조건을 만족했을 때 주는 안전성 가산점
        WEIGHT_WEAKNESS = 2.0      # 공통 약점 커버 가중치
        WEIGHT_NOT_RESISTED = 1.0  # 반감 불가 타입 커버 가중치

        for poke_name in self.pochampslst:
            if poke_name not in pokedex_cache:
                continue
            
            poke_data = pokedex_cache[poke_name]
            poke_types = poke_data.get("types", [])

            # 각 필터 단계별 통과 여부 확인 (True/False)
            pass_f1 = eval_filter_1(poke_types)
            pass_f2 = eval_filter_2(poke_types)
            pass_f3 = eval_filter_3(poke_types)

            # 안전성 필터 점수 산정 (많이 만족할수록 높은 점수)
            safety_score = 0
            if pass_f1: safety_score += FILTER_PASS_SCORE
            if pass_f2: safety_score += FILTER_PASS_SCORE
            if pass_f3: safety_score += FILTER_PASS_SCORE

            # 커버리지 계산
            covered_weaknesses = [
                atk_type for atk_type in common_weaknesses.keys()
                if analyzer._get_type_multiplier(atk_type, poke_types) < 1.0
            ]
            
            covered_not_resisted = [
                atk_type for atk_type in common_not_resisted.keys()
                if atk_type not in common_weaknesses and analyzer._get_type_multiplier(atk_type, poke_types) < 1.0
            ]

            total_covered = covered_weaknesses + covered_not_resisted
            
            # 파티에 조금이라도 기여할 수 있는 포켓몬인 경우에만 후보에 추가
            if total_covered or safety_score > 0:
                weakness_count = len(covered_weaknesses)
                not_resisted_count = len(covered_not_resisted)
                
                # 최종 종합 점수 = 안전성 점수 + (약점 커버 점수) + (반감 불가 커버 점수)
                total_score = safety_score + (weakness_count * WEIGHT_WEAKNESS) + (not_resisted_count * WEIGHT_NOT_RESISTED)

                item = {
                    "name": poke_name,
                    "types": poke_types,
                    "covered_types": total_covered,
                    "safety_score": safety_score,
                    "weakness_score": weakness_count,      
                    "not_resisted_score": not_resisted_count,
                    "total_score": total_score
                }

                if poke_name.startswith("메가") and poke_name != "메가니움":
                    mega_recommendations.append(item)
                else:
                    general_recommendations.append(item)

        # 정렬 기준: 1순위 종합 점수, 2순위 안전성 점수, 3순위 이름
        sort_key = lambda x: (x["total_score"], x["safety_score"], x["name"])
        
        general_recommendations.sort(key=sort_key, reverse=True)
        mega_recommendations.sort(key=sort_key, reverse=True)
        
        return general_recommendations[:10], mega_recommendations, common_weaknesses, common_not_resisted


def test_recommend(test_samples):
    """방어 보완 포켓몬 추천 테스트 함수 (소프트 스코어링 점수 반영)"""
    print("=== [방어 보완 포켓몬 추천 및 파티 취약 타입 분석 테스트] ===")
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
                c_types = ', '.join(item["covered_types"]) if item["covered_types"] else "없음"
                print(f"  {idx:2d}. [{p_name}] (방어 타입: {p_types})")
                print(      f"      🛡️ 보완한 취약 타입: {c_types}")
                print(      f"      📊 점수 내역: 종합 총점: {item['total_score']:.1f}점 (안전성 점수: {item['safety_score']}점 / 공통약점 커버: {item['weakness_score']}개 / 반감불가 커버: {item['not_resisted_score']}개)")
                print("-" * 75)
        else:
            print("  - 조건을 만족하는 일반 포켓몬이 없습니다.")

        print(f"\n✨ [메가진화 포켓몬] 방어 보완 추천 상위 {len(mega_top50)}마리:\n")
        if mega_top50:
            for idx, item in enumerate(mega_top50, 1):
                p_name = item["name"]
                p_types = '/'.join(item["types"])
                c_types = ', '.join(item["covered_types"]) if item["covered_types"] else "없음"
                print(f"  {idx:2d}. [{p_name}] (방어 타입: {p_types})")
                print(      f"      🛡️ 보완한 취약 타입: {c_types}")
                print(      f"      📊 점수 내역: 종합 총점: {item['total_score']:.1f}점 (안전성 점수: {item['safety_score']}점 / 공통약점 커버: {item['weakness_score']}개 / 반감불가 커버: {item['not_resisted_score']}개)")
                print("-" * 75)
        else:
            print("  - 조건을 만족하는 메가진화 포켓몬이 없습니다.")
            
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")

def test_offense(test_samples):
    """공격 상성 분석 테스트 함수"""
    print("=== [TeamAnalyzer: 공격 상성 및 파훼 불가 조합 분석 테스트] ===")
    try:
        analyzer = TeamAnalyzer(test_samples)
        offense_results = analyzer.analyze_party_offense()
        
        print("\n[파티 공격 상성 분석 결과]")
        
        type_to_moves = offense_results.get("type_to_moves", {})
        print("  • 타입별 보유 기술 목록 (주력기/보조기 포함):")
        if type_to_moves:
            for atk_type, move_names in type_to_moves.items():
                print(f"    - {atk_type}: {', '.join(move_names)}")
        else:
            print("    - 등록된 공격 기술이 없습니다.")
            
        category_ratios = offense_results.get("category_ratios", {})
        print("\n  • 기술 카테고리 비율:")
        if category_ratios:
            for cat, info in category_ratios.items():
                print(f"    - {cat}: {info['개수']}개 ({info['비율(%)']}%)")
        else:
            print("    - 집계된 공격 기술이 없습니다.")
            
        unweakened_combinations = offense_results.get("unweakened_combinations", [])
        print(f"\n  • 파티의 기술로 약점을 못 찌르며 고화력(4.3만 이상) 1배 타격도 불가능한 방어 타입 조합 (총 {len(unweakened_combinations)}개):")
        if unweakened_combinations:
            for item in unweakened_combinations:
                def_combo = item["combination"]
                weakness_types = item["weakness_types"]
                w_str = ', '.join(weakness_types) if weakness_types else "없음"
                print(f"    - {'/'.join(def_combo)} (약점 찌를 수 있는 타입: {w_str})")
        else:
            print("    - 없음 (모든 방어 타입 조합에 대해 효과적인 타격이 가능합니다)")
            
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")


if __name__ == "__main__":
    test_samples = [
        "트릭룸카디나르마",
        "트릭룸메갑주",
        "스카프삼삼드래",
        "조심누리레느",
        "HD하마돈샘플"
    ]
    # test_recommend(test_samples)
    test_offense(test_samples)
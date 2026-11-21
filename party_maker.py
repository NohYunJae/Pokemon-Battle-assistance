import os
import traceback

from utils.pochamps_list import pochamps_pokemon_list
from loader.data_loader import PokemonCSVLoader, Move, load_pokedex_cache
from pokemon import Pokemon
from calculator.utils.type_chart import type_chart
from utils.special_ability import ABILITY_TO_POKEMON

DATA_DIR = os.path.join(os.path.expanduser("~"), "PokemonDATA", "data")
pokedex_cache = load_pokedex_cache()

WEATHER_ABILITY_MAP = {
    "가뭄": "쾌청",
    "진홍빛고동": "쾌청",
    "잔비": "비",
}


def get_weather_state(value):
    """특성 또는 샘플 날씨 값을 '쾌청', '비', None으로 반환"""
    if not value:
        return None
    val = str(value).strip()
    if val in WEATHER_ABILITY_MAP:
        return WEATHER_ABILITY_MAP[val]
    if val in ("쾌청", "비"):
        return val
    return None


def get_weather_multiplier(atk_type, weather):
    """날씨 상태('쾌청', '비')에 따른 공격 위력 배율 반환"""
    if weather == "쾌청":
        if atk_type == "불꽃":
            return 1.5
        if atk_type == "물":
            return 0.5
    elif weather == "비":
        if atk_type == "물":
            return 1.5
        if atk_type == "불꽃":
            return 0.5
    return 1.0


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
                    lv=50, item=sample.get("지닌도구"), ability=sample.get("특성"))

        main_list = []
        sub_list = []
        for move_name in sample["기술"]:
            if not move_name or move_name not in self.move_dict:
                continue

            move_obj = self.move_dict[move_name]
            power = move_obj.power

            if power == 0:
                continue

            dmg_output = pkm.calculate_DMG_output(move_obj, sample["필드"], sample["날씨"], sample["상태이상"])

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

    def get_party_weather(self):
        """기존 파티에 설정된 날씨('쾌청', '비', None) 반환"""
        for sample in self.party:
            w = get_weather_state(sample.get("날씨"))
            if w:
                return w
        return None

    def analyze_party_offense(self):
        """주력기 및 보조기 결정력 검증, 1배 결정력 4만 이상 고려 약점 타격 불가 조합 분석 및 필요한 공격 타입 순위 반환"""
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
        unweakened_combinations_raw = []
        checked_combinations = set()

        for t1 in all_types:
            comb = (t1,)
            if self._is_completely_unweakened(comb, all_party_moves):
                weakness_types = [
                    atk for atk in all_types
                    if self._get_type_multiplier(atk, comb) >= 2.0
                ]
                unweakened_combinations_raw.append({
                    "combination": comb,
                    "raw_weakness_types": weakness_types
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
                            unweakened_combinations_raw.append({
                                "combination": comb,
                                "raw_weakness_types": weakness_types
                            })

        type_coverage_count = {}
        for item in unweakened_combinations_raw:
            for atk in item["raw_weakness_types"]:
                type_coverage_count[atk] = type_coverage_count.get(atk, 0) + 1

        unweakened_combinations = []
        for item in unweakened_combinations_raw:
            sorted_weakness_types = sorted(
                item["raw_weakness_types"],
                key=lambda atk: (-type_coverage_count.get(atk, 0), atk)
            )
            unweakened_combinations.append({
                "combination": item["combination"],
                "weakness_types": sorted_weakness_types
            })

        recommended_attack_types = sorted(
            [{"타입": t, "커버가능조합수": c} for t, c in type_coverage_count.items()],
            key=lambda x: (-x["커버가능조합수"], x["타입"])
        )

        return {
            "type_to_moves": formatted_type_to_moves,
            "category_ratios": category_ratios,
            "unweakened_combinations": unweakened_combinations,
            "recommended_attack_types": recommended_attack_types
        }

    def _is_completely_unweakened(self, def_combo, all_party_moves):
        """방어 타입 조합에 대한 파티 기술 대처 여부 확인"""
        if not all_party_moves:
            return True

        for move in all_party_moves:
            atk_type = move["기술타입"]
            dmg = move["데미지"]
            mult = self._get_type_multiplier(atk_type, def_combo)

            if mult >= 2.0 and dmg > 23000:
                return False

            if mult == 1.0 and dmg >= 40000:
                return False

        return True

    def analyze_party_defense(self):
        """파티 방어 상성 분석: 기존 파티 날씨를 반영해 약점 및 반감 불가 타입 재계산"""
        total_party_size = len(self.party)
        threshold = total_party_size / 2
        party_weather = self.get_party_weather()

        all_attack_types = list(type_chart.keys())

        weakness_counts = {}
        not_resisted_counts = {}

        for idx, sample in enumerate(self.party):
            def_types = sample.get("타입", [])
            member_weather = get_weather_state(sample.get("날씨")) or party_weather

            for atk_type in all_attack_types:
                mult = (
                    self._get_type_multiplier(atk_type, def_types)
                    * get_weather_multiplier(atk_type, member_weather)
                )

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
    """파티 보완 포켓몬 추천 클래스 (방어/공격 분리 및 종합)"""
    def __init__(self):
        self.pochampslst = pochamps_pokemon_list
        self.poke_to_abilities = {}
        for ability, pokes in ABILITY_TO_POKEMON.items():
            for p in pokes:
                if p not in self.poke_to_abilities:
                    self.poke_to_abilities[p] = []
                self.poke_to_abilities[p].append(ability)

    def _get_effective_weather(self, analyzer, ability):
        """후보 특성이 만드는 날씨('쾌청', '비') 우선, 없으면 기존 파티 날씨 반환"""
        ability_weather = get_weather_state(ability)
        if ability_weather:
            return ability_weather
        return analyzer.get_party_weather()

    def _get_party_multiplier_with_weather(self, analyzer, atk_type, def_types, ability):
        """후보 특성이 만드는 날씨를 반영한 기존 파티원 방어 배율 계산"""
        weather = self._get_effective_weather(analyzer, ability)
        return (
            analyzer._get_type_multiplier(atk_type, def_types)
            * get_weather_multiplier(atk_type, weather)
        )

    def _get_type_multiplier_with_ability(self, analyzer, atk_type, def_types, ability):
        multiplier = analyzer._get_type_multiplier(atk_type, def_types)

        if ability:
            if ability in ["부유", "흙먹기"] and atk_type == "땅":
                return 0.0
            elif ability == "타오르는불꽃" and atk_type == "불꽃":
                return 0.0
            elif ability in ["저수", "마중물", "건조피부"] and atk_type == "물":
                return 0.0
            elif ability in ["축전", "피뢰침", "전기엔진"] and atk_type == "전기":
                return 0.0
            elif ability == "초식" and atk_type == "풀":
                return 0.0

        weather = self._get_effective_weather(analyzer, ability)
        multiplier *= get_weather_multiplier(atk_type, weather)

        if ability == "건조피부" and atk_type == "불꽃":
            if multiplier < 1.0:
                return 1.0
            elif multiplier == 1.0:
                return 2.0
            else:
                return multiplier * 1.25

        return multiplier

    def recommend_pokemon_defense(self, analyzer):
        """방어 상성 기반 추천 점수 계산 함수"""
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

        defense_scores = {}
        FILTER_PASS_SCORE = 5.0
        WEIGHT_WEAKNESS = 2.0
        WEIGHT_NOT_RESISTED = 1.0

        for poke_name in self.pochampslst:
            if poke_name not in pokedex_cache:
                continue

            poke_data = pokedex_cache[poke_name]
            poke_types = poke_data.get("types", [])
            candidate_abilities = self.poke_to_abilities.get(poke_name, [None])

            for ability in candidate_abilities:
                display_name = f"{poke_name}({ability})" if ability else poke_name

                party_mults = {
                    atk_type: [
                        self._get_party_multiplier_with_weather(analyzer, atk_type, def_types, ability)
                        for def_types in existing_party_types
                    ]
                    for atk_type in all_attack_types
                }

                def eval_filter_1(poke_types):
                    has_weakness = any(
                        self._get_type_multiplier_with_ability(analyzer, atk_type, poke_types, ability) >= 2.0
                        for atk_type in common_weaknesses.keys()
                    )
                    return not has_weakness

                def eval_filter_2(poke_types):
                    for atk_type in all_attack_types:
                        weak_count = sum(
                            1 for mult in party_mults[atk_type]
                            if mult >= 2.0
                        )
                        if self._get_type_multiplier_with_ability(analyzer, atk_type, poke_types, ability) >= 2.0:
                            weak_count += 1
                        if weak_count >= new_threshold:
                            return False
                    return True

                def eval_filter_3(poke_types):
                    has_blindspot_weakness = any(
                        self._get_type_multiplier_with_ability(analyzer, atk_type, poke_types, ability) >= 2.0
                        for atk_type in completely_unresisted_types
                    )
                    return not has_blindspot_weakness

                pass_f1 = eval_filter_1(poke_types)
                pass_f2 = eval_filter_2(poke_types)
                pass_f3 = eval_filter_3(poke_types)

                safety_score = 0
                if pass_f1:
                    safety_score += FILTER_PASS_SCORE
                if pass_f2:
                    safety_score += FILTER_PASS_SCORE
                if pass_f3:
                    safety_score += FILTER_PASS_SCORE

                def is_type_covered(atk_type):
                    cand_mult = self._get_type_multiplier_with_ability(analyzer, atk_type, poke_types, ability)
                    if cand_mult < 1.0:
                        return True
                    return any(mult < 1.0 for mult in party_mults[atk_type])

                covered_weaknesses = [
                    atk_type for atk_type in common_weaknesses.keys()
                    if is_type_covered(atk_type)
                ]

                covered_not_resisted = [
                    atk_type for atk_type in common_not_resisted.keys()
                    if atk_type not in common_weaknesses and is_type_covered(atk_type)
                ]

                total_covered = covered_weaknesses + covered_not_resisted

                if total_covered or safety_score > 0:
                    weakness_count = len(covered_weaknesses)
                    not_resisted_count = len(covered_not_resisted)
                    score = (
                        safety_score
                        + (weakness_count * WEIGHT_WEAKNESS)
                        + (not_resisted_count * WEIGHT_NOT_RESISTED)
                    )

                    defense_scores[display_name] = {
                        "types": poke_types,
                        "covered_types": total_covered,
                        "safety_score": safety_score,
                        "weakness_score": weakness_count,
                        "not_resisted_score": not_resisted_count,
                        "defense_score": score
                    }

        return defense_scores, common_weaknesses, common_not_resisted

    def recommend_pokemon_offense(self, analyzer, top_n_offense=3):
        """공격 상성(필요한 공격 타입을 자속으로 가짐) 기반 추천 점수 계산 함수"""
        offense_result = analyzer.analyze_party_offense()
        recommended_attack_types = offense_result.get("recommended_attack_types", [])
        top_offense_types = {item["타입"] for item in recommended_attack_types[:top_n_offense]}

        offense_scores = {}
        WEIGHT_OFFENSE = 5.0

        for poke_name in self.pochampslst:
            if poke_name not in pokedex_cache:
                continue

            poke_data = pokedex_cache[poke_name]
            poke_types = poke_data.get("types", [])
            candidate_abilities = self.poke_to_abilities.get(poke_name, [None])

            for ability in candidate_abilities:
                display_name = f"{poke_name}({ability})" if ability else poke_name
                matched_offense_types = [t for t in poke_types if t in top_offense_types]

                if matched_offense_types:
                    offense_score = len(matched_offense_types) * WEIGHT_OFFENSE
                    offense_scores[display_name] = {
                        "types": poke_types,
                        "matched_offense_types": matched_offense_types,
                        "offense_score": offense_score
                    }

        return offense_scores, recommended_attack_types

    def recommend_pokemon_combined(self, party_samples, top_n_offense=3):
        """종합 함수: 방어 상성 함수와 공격 상성 함수를 각각 호출하여 결과를 합산 및 정렬"""
        analyzer = TeamAnalyzer(party_samples)

        defense_scores, common_weaknesses, common_not_resisted = self.recommend_pokemon_defense(analyzer)
        offense_scores, recommended_attack_types = self.recommend_pokemon_offense(analyzer, top_n_offense)

        all_candidates = set(list(defense_scores.keys()) + list(offense_scores.keys()))

        general_recommendations = []
        mega_recommendations = []

        for name in all_candidates:
            def_data = defense_scores.get(name, {})
            off_data = offense_scores.get(name, {})

            poke_types = def_data.get("types") or off_data.get("types", [])

            safety_score = def_data.get("safety_score", 0.0)
            weakness_score = def_data.get("weakness_score", 0)
            not_resisted_score = def_data.get("not_resisted_score", 0)
            defense_score = def_data.get("defense_score", 0.0)

            offense_score = off_data.get("offense_score", 0.0)
            matched_offense_types = off_data.get("matched_offense_types", [])
            covered_types = def_data.get("covered_types", [])

            total_score = defense_score + offense_score

            item = {
                "name": name,
                "types": poke_types,
                "covered_types": covered_types,
                "matched_offense_types": matched_offense_types,
                "safety_score": safety_score,
                "weakness_score": weakness_score,
                "not_resisted_score": not_resisted_score,
                "offense_score": len(matched_offense_types),
                "total_score": total_score
            }

            if name.startswith("메가") and not name.startswith("메가니움"):
                mega_recommendations.append(item)
            else:
                general_recommendations.append(item)

        sort_key = lambda x: (x["total_score"], x["safety_score"], x["name"])
        general_recommendations.sort(key=sort_key, reverse=True)
        mega_recommendations.sort(key=sort_key, reverse=True)

        return general_recommendations[:100], mega_recommendations, common_weaknesses, common_not_resisted, recommended_attack_types
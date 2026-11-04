import os
from loader.data_loader import PokemonCSVLoader, Move
from pokemon import Pokemon
from calculator.utils.type_chart import type_chart

DATA_DIR = os.path.join(os.path.expanduser("~"), "PokemonDATA", "data")

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

            # 값을 (기술타입, 데미지, 카테고리) 튜플 형태로 저장합니다.
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
        print("\n=== [파티 공격 상성, 복합 타입 약점 타격 및 물리/특수 비율 분석] ===")
        
        main_types = set()
        sub_types = set()
        category_counts = {"물리": 0, "특수": 0, "변화": 0}
        
        # 파티 전체의 모든 공격 기술(주력기 + 보조기) 정보를 담을 리스트
        all_party_moves = []

        for i in range(len(self.party)):
            mvs = self.get_main_moves(self.party[i])
            
            # 주력기 타입 수집 및 카테고리 집계, 상세 기술 정보 저장
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

            # 보조기 타입 수집 및 카테고리 집계, 상세 기술 정보 저장
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

        # 타입별 기술 목록 출력
        print("\n[파티 보유 기술 타입별 목록 (주력기 및 보조기 포함)]")
        if type_to_moves:
            for atk_type, names in type_to_moves.items():
                print(f"- {atk_type}: {', '.join(names)}")
        else:
            print("- 등록된 공격 기술이 없습니다.")

        # 물리/특수 비율 계산 출력
        total_moves = sum(category_counts.values())
        print("\n[기술 카테고리(물리/특수) 비율]")
        if total_moves > 0:
            for cat, count in category_counts.items():
                if count > 0:
                    percent = (count / total_moves) * 100
                    print(f"- {cat}: {count}개 ({percent:.1f}%)")
        else:
            print("집계된 공격 기술이 없습니다.")
        
        # 모든 타입 리스트 (type_chart의 키 기준)
        all_types = list(type_chart.keys())
        
        # 조건에 맞는 방어 타입 조합 도출 (약점을 못 찌르며, 1배라도 결정력 4만 이상인 기술이 없는 경우)
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

        print("\n[🛡️ 경고: 파티의 기술로 약점을 못 찌르며, 1배 타격 시에도 결정력 4만 이상을 내지 못하는 방어 타입 조합]")
        print("(이 방어 타입을 가진 상대 앞에서는 고화력 1배 타격이나 약점 찌르기가 모두 불가능하여 돌파하기 매우 까다롭습니다)")
        if unweakened_combinations:
            for def_combo in unweakened_combinations:
                print(f"  - {'/'.join(def_combo)} 타입 조합")
        else:
            print("  - 없음 (모든 방어 타입 조합에 대해 약점을 찌르거나 1배로 4만 이상의 결정력을 낼 수 있는 기술이 존재합니다)")

    def _is_completely_unweakened(self, def_combo, all_party_moves):
        """
        주어진 방어 타입 조합(def_combo)에 대해, 파티의 모든 기술(주력기+보조기) 중
        1. 약점(2배 이상)을 찌르는 기술이 있거나,
        2. 1배 이상(1.0 이상 2.0 미만)이면서 결정력(dmg_output)이 43,000 이상인 기술이
        단 하나라도 존재하면 대처 가능하다고 판단하여 False를 반환합니다.
        어떤 기술도 위 조건을 만족하지 못할 때만 True(대처 불가)를 반환합니다.
        """
        if not all_party_moves:
            return True

        for move in all_party_moves:
            atk_type = move["기술타입"]
            dmg = move["데미지"]
            mult = self._get_type_multiplier(atk_type, def_combo)

            # 조건 1: 약점을 찌르는 경우 (2배 이상)
            if mult >= 2.0 and dmg > 26000:
                return False
            
            # 조건 2: 1배 결정력이 45,000 이상인 경우
            if mult == 1.0 and dmg >= 43000:
                return False
        
        return True

    def analyze_party_defense(self):
        """파티 방어 상성 분석: 파티원 절반 초과 기준 약점 및 반감 불가(1배 이상) 타입 분석"""
        print("\n=== [파티 방어 상성 및 공통 약점 분석] ===")

        total_party_size = len(self.party)
        threshold = total_party_size / 2

        all_attack_types = list(type_chart.keys())
        
        weakness_counts = {}
        not_resisted_counts = {} 

        print(f"• 파티원 수: {total_party_size}마리 (공통 취약 기준: {threshold}마리 초과)\n")

        for idx, sample in enumerate(self.party):
            poke_name = sample.get("포켓몬", f"포켓몬{idx+1}")
            def_types = sample.get("타입", [])
            print(f"  - [{poke_name}] (방어 타입: {'/'.join(def_types)})")

            for atk_type in all_attack_types:
                mult = self._get_type_multiplier(atk_type, def_types)
                
                # 약점 체크 (2배 이상)
                if mult >= 2.0:
                    weakness_counts[atk_type] = weakness_counts.get(atk_type, 0) + 1
                
                # 반감하지 못하는지 체크 (1배 이상인 경우, 즉 반감 0.5/0.25나 무효 0이 아닌 경우)
                if mult >= 1.0:
                    not_resisted_counts[atk_type] = not_resisted_counts.get(atk_type, 0) + 1

        print("\n--- [파티 공통 약점 분석 (절반 초과)] ---")
        common_weaknesses = {k: v for k, v in weakness_counts.items() if v > threshold}
        if common_weaknesses:
            sorted_weaknesses = sorted(common_weaknesses.items(), key=lambda x: x[1], reverse=True)
            for atk_type, count in sorted_weaknesses:
                print(f"⚠️ {atk_type} 타입 공격: 파티 내 {count}마리가 약점(2배 이상)을 찔림 (기준 초과)")
        else:
            print("- 파티원 절반을 초과하여 약점을 찔리는 공통 약점 타입이 없습니다.")

        print("\n--- [파티 반감 불가(1배 이상) 타입 분석 (절반 초과)] ---")
        common_not_resisted = {k: v for k, v in not_resisted_counts.items() if v > threshold}
        if common_not_resisted:
            sorted_not_resisted = sorted(common_not_resisted.items(), key=lambda x: x[1], reverse=True)
            for atk_type, count in sorted_not_resisted:
                print(f"🛡️ {atk_type} 타입 공격: 파티 내 {count}마리가 반감하지 못함(1배 이상 데미지) (기준 초과)")
        else:
            print("- 파티원 절반 초과가 반감하지 못하는 타입이 없습니다.")


if __name__ == "__main__":
    test_samples = [
        "배북마릴리", 
        "철벽바프메메타", 
        "트릭룸카디나르마", 
        "한카리아스", 
        "스카프에써르", 
        "트릭룸메갑주"
    ]
    
    print("=== [팀 분석기(TeamAnalyzer) 테스트 시작] ===")
    try:
        analyzer = TeamAnalyzer(test_samples)
        
        analyzer.analyze_party_offense()
        
        analyzer.analyze_party_defense()
        
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        print("'PokemonDATA/data/samples/' 경로에 해당 샘플 파일들이 정상적으로 위치해 있는지 확인해 주세요.")
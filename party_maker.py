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
        """결정력 계산 및 주력기 선정 로직"""
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
                # type_chart에 명시된 상성이 있으면 곱하고, 없으면 기본 1.0배[cite: 2]
                mult = type_chart[atk_type].get(def_type, 1.0)
                multiplier *= mult
        return multiplier

    def analyze_party_offense(self):
        """주력기 결정력 검증 및 복합 타입 고려 반감/무효/1/4배 분석"""
        print("\n=== [파티 공격 상성, 복합 타입 반감/무효 및 물리/특수 비율 분석] ===")
        
        main_types = set()
        category_counts = {"물리": 0, "특수": 0, "변화": 0}

        for i in range(len(self.party)):
            mvs = self.get_main_moves(self.party[i])
            
            # 주력기 타입 수집 및 카테고리 집계
            for item_list in mvs["주력기목록"]:
                for move in item_list:
                    main_types.add(move["기술타입"])
                    cat = move["카테고리"]
                    if cat in category_counts:
                        category_counts[cat] += 1

            for item_list in mvs["보조기목록"]:
                for move in item_list:
                    cat = move["카테고리"]
                    if cat in category_counts:
                        category_counts[cat] += 1

        print(f"파티 주력기 타입 목록: {list(main_types)}")

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
        
        quarter_resisted = {} # 1/4배 반감 (0.25)
        half_resisted = {}    # 1/2배 반감 (0.5)
        immune = {}           # 0배 무효 (0.0)

        # 단일 타입 및 주요 복합 타입 쌍을 만들어 검사
        # (모든 경우의 수를 체크하기 위해 1개 혹은 2개 조합 생성)
        checked_combinations = set()

        for t1 in all_types:
            # 단일 타입 검사
            comb = (t1,)
            self._evaluate_defense_combo(comb, main_types, quarter_resisted, half_resisted, immune)

            # 복합 타입 검사 (t1 + t2)
            for t2 in all_types:
                if t1 != t2:
                    comb = tuple(sorted([t1, t2])) # 순서 상관없이 동일 조합 처리 (예: 불꽃/강철 == 강철/불꽃)
                    if comb not in checked_combinations:
                        checked_combinations.add(comb)
                        self._evaluate_defense_combo(comb, main_types, quarter_resisted, half_resisted, immune)

        print("\n[방어 타입별 반감/무효 정보 (우리 파티 주력기 기준, 복합 타입 포함)]")
        
        if quarter_resisted:
            print("\n  • 1/4배 반감되는 방어 타입 조합:")
            for def_combo, atk_list in quarter_resisted.items():
                print(f"    - {'/'.join(def_combo)} 타입: {', '.join(atk_list)} 공격")

        if half_resisted:
            print("\n  • 1/2배 반감되는 방어 타입 조합:")
            for def_combo, atk_list in half_resisted.items():
                print(f"    - {'/'.join(def_combo)} 타입: {', '.join(atk_list)} 공격")

        if immune:
            print("\n  • 0배(무효)되는 방어 타입 조합:")
            for def_combo, atk_list in immune.items():
                print(f"    - {'/'.join(def_combo)} 타입: {', '.join(atk_list)} 공격")

    def _evaluate_defense_combo(self, def_combo, main_types, quarter_resisted, half_resisted, immune):
        """특정 방어 타입 조합에 대해 파티 주력기들의 상성 배율을 평가"""
        for atk_type in main_types:
            mult = self._get_type_multiplier(atk_type, def_combo)
            if mult == 0.25:
                if def_combo not in quarter_resisted:
                    quarter_resisted[def_combo] = []
                if atk_type not in quarter_resisted[def_combo]:
                    quarter_resisted[def_combo].append(atk_type)
            elif mult == 0.5:
                if def_combo not in half_resisted:
                    half_resisted[def_combo] = []
                if atk_type not in half_resisted[def_combo]:
                    half_resisted[def_combo].append(atk_type)
            elif mult == 0.0:
                if def_combo not in immune:
                    immune[def_combo] = []
                if atk_type not in immune[def_combo]:
                    immune[def_combo].append(atk_type)

    def analyze_party_defense(self):
        """파티 방어 상성 분석: 파티원 절반 초과 기준 약점 및 반감 불가(1배 이상) 타입 분석"""
        print("\n=== [파티 방어 상성 및 공통 약점 분석] ===")

        total_party_size = len(self.party)
        threshold = total_party_size / 2  # 절반 기준 (예: 6마리 중 3마리 초과인 4마리 이상)

        all_attack_types = list(type_chart.keys())
        
        weakness_counts = {}      # 약점(2배 이상)을 찔리는 파티원 수 집계
        not_resisted_counts = {}  # 반감하지 못하는(1배 이상, 즉 반감/무효가 아닌) 파티원 수 집계

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
    # 테스트할 샘플 파일 이름 리스트 (실제 'PokemonDATA/data/samples/' 폴더 안에 있는 파일명으로 수정해주세요)
    # 예: "sample1.csv", "sample2.csv" 등이 있다면 확장자(.csv)를 제외하거나 포함하여 작성
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
        # TeamAnalyzer 객체 생성
        analyzer = TeamAnalyzer(test_samples)
        
        # 1. 공격 상성 및 주력기/카테고리 분석 실행
        analyzer.analyze_party_offense()
        
        # 2. 방어 상성 및 공통 약점 분석 실행
        analyzer.analyze_party_defense()
        
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        print("'PokemonDATA/data/samples/' 경로에 해당 샘플 파일들이 정상적으로 위치해 있는지 확인해 주세요.")
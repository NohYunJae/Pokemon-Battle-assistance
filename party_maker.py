# import os
# import pochamps_list

# from pokemon import Pokemon
# from calculator.PBTcalculator import DMGoutput_Bulk_Calculator
# from calculator.PBTmodifiers import Power_modifiers
# from calculator.utils import type_chart
# from calculator.stats import _load_pokedex_cache
# from loader.data_loader import PokemonCSVLoader, Move

# DATA_DIR = os.path.join(os.path.expanduser("~"), "PokemonDATA", "data")

# class PartyMaker:
#     """포켓몬 파티를 구성하고 계산하는 클래스"""
#     def __init__(self):
#         self.party = {}
#         self.move_dict = Move.load_move_dict()

#     def _save_pokemon(self, file_path):
#         pkm_data = PokemonCSVLoader.load_pokemon_data(file_path)
#         self.party[len(self.party)] = Pokemon(pkm_data)

#         return self.party

#     def _calculate_damage_output(self, pkm_sample_file):
#         """input: 포켓몬 샘플파일"""
#         pkm = PokemonCSVLoader.load_pokemon_data(pkm_sample_file)
#         pkm_stat = pkm["실수치"]
#         calc = DMGoutput_Bulk_Calculator(pkm)
#         A = pkm_stat[1]  # 공격
        
#         dmg_output = calc.calculate_dmg_output(A, self.move_dict, weather=pkm.get("날씨", None))

#         return dmg_output
    
#     def _calculate_bulk(self, pkm_sample_file):
#         """input: 포켓몬 샘플파일"""
#         pkm = PokemonCSVLoader.load_pokemon_data(pkm_sample_file)
#         pkm_stat = pkm["실수치"]
#         calc = DMGoutput_Bulk_Calculator(pkm)
#         H = pkm_stat[0]  # HP
#         B = pkm_stat[2]  # 방어
#         D = pkm_stat[4]  # 특수방어

#         bulk = calc.calculate_bulk(H, B, D, weather=pkm.get("날씨", None))

#         return bulk
    
#     def _get_weaknesses(self, pkm_sample_file):
#         """input: 포켓몬 샘플파일"""
#         pkm = PokemonCSVLoader.load_pokemon_data(pkm_sample_file)
#         types = pkm["타입"]
#         weaknesses = {}
        
#         if isinstance(types, str):
#             types = [t.strip() for t in types.split(",")]
            
#         for attack_type, defense_dict in type_chart.items():
#             multiplier = 1.0
#             for p_type in types:
#                 # 방어 타입에 해당하는 공격 타입의 상성 배율을 곱함 (기본값 1.0)
#                 multiplier *= defense_dict.get(p_type, 1.0)
                
#             # 배율이 1.0을 초과하면(2배, 4배 등) 약점으로 등록
#             if multiplier > 1.0:
#                 weaknesses[attack_type] = multiplier


# class RoleBasedPruner:
#     """
#     stats.py의 포켓몬 도감 메모리 캐시를 활용하여 역할별 상위 후보군을 선별하는 클래스입니다.
#     """
#     def __init__(self):
#         self.roles = ["Sweeper", "Wall", "Pivot", "Lead"]
#         # stats.py에 정의된 도감 캐시를 로드하여 활용
#         self.pokedex_cache = _load_pokedex_cache()

#     def calculate_dmg_bulk(self, pkm, weather):
#         """
#         종족값 배열 [HP, 공격, 방어, 특수공격, 특수방어, 스피드]을 바탕으로 
#         물리/특수 내구를 계산합니다.
#         """
#         hp, a, b, c, d, s = pkm["실수치"]
#         mod = Power_modifiers(pkm, move)
#         bulk_phy = hp * b
#         bulk_spc = hp * d
#         dmg = max(a, c) * mv_power * mod.get_power_modifier()
#         calc = DMGoutput_Bulk_Calculator(pkm)
#         physical_bulk, special_bulk = calc.calculate_bulk(hp, b, d, weather)
#         return physical_bulk, special_bulk

        
#     def evaluate_role_scores(self, base_stats):
#         """
#         종족값 배열 [HP, 공격, 방어, 특수공격, 특수방어, 스피드]을 바탕으로 
#         각 역할별 적합도 점수를 산출합니다.
#         """
#         hp, a, b, c, d, s = base_stats
        
#         # 1. 스위퍼 (Sweeper): 화력(A 또는 C)과 스피드(S) 중심
#         sweeper_score = max(a, c) * 1.5 + s * 1.2
        
#         # 2. 물리/특수 벽 (Wall): 내구(HP, B, D) 중심
#         wall_score = hp * 1.2 + (b + d) * 1.5
        
#         # 3. 사이클 피벗 (Pivot): 밸런스 잡힌 내구와 중고속 스피드
#         pivot_score = hp * 1.0 + (b + d) * 1.0 + s * 1.0
        
#         # 4. 기점 마련 (Lead): 높은 스피드 라인과 안정적인 내구
#         lead_score = s * 1.0 + hp * 1.8
        
#         return {
#             "Sweeper": sweeper_score,
#             "Wall": wall_score,
#             "Pivot": pivot_score,
#             "Lead": lead_score
#         }

#     def prune_candidate_pools(self, top_n=25):
#         """
#         전체 메타 포켓몬 리스트에서 각 역할별 상위 top_n 마리의 후보 풀을 선별합니다.
#         """
#         role_pools = {role: [] for role in self.roles}
#         pokemon_cache = {}

#         all_mc_pokemon_list = pochamps_list.all_mc_pokemon_list
#         for name in all_mc_pokemon_list:
#             pkm_info = self.pokedex_cache.get(name)
#             if not pkm_info:
#                 continue
            
#             base_stats = pkm_info["base_stats"]
#             types = pkm_info["types"]
            
#             scores = self.evaluate_role_scores(base_stats)
#             pokemon_cache[name] = {"stats": base_stats, "types": types, "scores": scores}

#         # 2. 역할별로 점수 정렬 후 상위 포켓몬 선별
#         for role in self.roles:
#             sorted_pokes = sorted(
#                 pokemon_cache.items(),
#                 key=lambda item: item[1]["scores"][role],
#                 reverse=True
#             )
#             # 상위 top_n 마리 추출
#             role_pools[role] = [
#                 {"name": p[0], "stats": p[1]["stats"], "types": p[1]["types"], "score": p[1]["scores"][role]}
#                 for p in sorted_pokes[:top_n]
#             ]

#         return role_pools

# if __name__ == "__main__":
#     pruner = RoleBasedPruner()
#     pools = pruner.prune_candidate_pools(top_n=25)
    
#     for role, pokes in pools.items():
#         print(f"\n--- [{role}] 역할 상위 후보군 (총 {len(pokes)}마리) ---")
#         for p in pokes[:5]:  # 상위 5마리 샘플 출력
#             print(f"- {p['name']} (종족값 합: {sum(p['stats'])}, 점수: {p['score']:.1f})")
    




import numpy as np

from pokemon import Pokemon
from loader.data_loader import Move
from calculator.PBTcalculator import BattleCalculator, DMGoutput_Bulk_Calculator


class PokemonStatOptimizer:
    """
    포켓몬 스탯포인트 최적화 모듈
    속도, 결정력, 내구순으로 최적화 권장

    1. 속도 최적화: 추월 목표 대상의 특성(쓱쓱, 엽록소 등), 아이템 설정후 추월을 위한 최소 필요 sp 도출
    2. 결정력 최적화: 돌파 대상의 샘플 선택, 최적화 대상의 성격, 아이템 설정 후 돌파를 위한 최소 필요 sp 도출
    3. 내구 최적화: 사용가능 sp 입력 후 확정 견딤 기준 내구 최적화 진행, 확정 견딤 기준 필요 최소 sp 및 물리, 특수 가중치 기준 최적 내구를 위한 sp 분배 도출

    각 함수에서 pkm1이 최적화 대상 포켓몬을 의미함
    """
    def __init__(self):
        self.sp_h = 0
        self.sp_a = 0
        self.sp_b = 0
        self.sp_c = 0
        self.sp_d = 0
        self.sp_spd = 0

    def _build_pokemon(self, data):
        return Pokemon(
            name=data["포켓몬"],
            nature=data["성격"],
            SPs=data["SPs"],
            IVs=data["IVs"],
            lv=data["LV"],
            item=data["지닌도구"],
            ability=data["특성"]
        )
    
    def optimize_bulk_advanced(
        self,
        pkm1_data,
        pkm2_data,
        move_idxs,
        av_sp,
        nature_b,
        nature_d,
        rank_a,
        rank_b,
        current_hp_percent,
        w_def,
        w_spdef,
        target_prob,
        hits,
        weather,
        field,
        crit
    ):  
        available_sp = av_sp
        move_dict = Move.load_move_dict()
        pkm1 = self._build_pokemon(pkm1_data)
        pkm2 = self._build_pokemon(pkm2_data)

        pkm2_move = pkm2_data["기술"]

        # 단일 또는 다중 기술 인덱스(콤보) 리스트로 통일
        move_indices = [int(move_idxs)] if isinstance(move_idxs, (int, float)) else list(move_idxs)

        base_stats1 = pkm1_data["종족치"]
        real_stats2 = pkm2_data["실수치"]

        A2, C2 = real_stats2[1], real_stats2[3]
        hp0, B0, D0 = base_stats1[0], base_stats1[2], base_stats1[4]

        sp = np.arange(0, 33)
        H_sp, B_sp, D_sp = np.meshgrid(sp, sp, sp, indexing='ij')

        mask = (H_sp + B_sp + D_sp <= available_sp)

        H_sp_val = np.where(mask, H_sp, np.nan)
        B_sp_val = np.where(mask, B_sp, np.nan)
        D_sp_val = np.where(mask, D_sp, np.nan)

        H = np.where(mask, hp0 + H_sp_val + 75, np.nan)

        B = np.floor((B0 + B_sp_val + 20) * nature_b)
        D = np.floor((D0 + D_sp_val + 20) * nature_d)

        sequence_dmg_matrices = []

        # 기술 콤보 순회하며 각 기술의 데미지 배열 계산 및 적재
        for m_idx in move_indices:
            atk_move = move_dict.get(pkm2_move[m_idx - 1])
            mv_category = atk_move.category

            if mv_category == "물리":
                atk = A2   # 상대 공격
                df = B     # 최적화 대상 방어
            elif mv_category == "특수":
                atk = C2   # 상대 특공
                df = D     # 최적화 대상 특방
            else:
                raise ValueError(f"유효하지 않는 기술 분류: {mv_category}")

            # 1회 공격 시의 16가지 난수 데미지 계산 후 NumPy 배열로 변환
            dmg_raw = BattleCalculator(pkm2, pkm1, atk_move).calculate_damage(atk, df, H, rank_a, rank_b, weather, field, crit)[0]
            dmg = np.asarray(dmg_raw)
            
            # 각 타격별 독립된 16가지 난수의 모든 조합(Cartesian Product)을 누적 계산 (m타 시 16^m개 생성)
            current_combos = np.zeros((1, *dmg.shape[1:]))
            for _ in range(hits):
                c_exp = current_combos[:, np.newaxis, :, :, :]
                d_exp = dmg[np.newaxis, :, :, :, :]
                current_combos = (c_exp + d_exp).reshape(-1, *dmg.shape[1:])
            
            sequence_dmg_matrices.append(current_combos)

        # 여러 기술(콤보)의 데미지 분포를 순서대로 합산 (Cartesian Sum)
        total_dmg_combos = sequence_dmg_matrices[0]
        for next_dmg in sequence_dmg_matrices[1:]:
            c_exp = total_dmg_combos[:, np.newaxis, :, :, :]
            d_exp = next_dmg[np.newaxis, :, :, :, :]
            total_dmg_combos = (c_exp + d_exp).reshape(-1, *total_dmg_combos.shape[1:])

        HP_rm = H * current_hp_percent / 100 - total_dmg_combos       # 각 조합별 남은 체력 배열

        tg_hp = H * (1 - current_hp_percent / 100)
        
        # 모든 난수 조합에 대해 목표 체력 초과 생존 여부 확인 (True / False)
        roll_survive = (HP_rm > tg_hp)
        
        # 각 H, B, D 스탯 조합별로 실제 생존한 경우의 수 비율 계산
        survived_count = np.sum(roll_survive, axis=0)
        total_cases = roll_survive.shape[0]
        survival_probabilities = survived_count / total_cases
        
        # 요구 확률 조건을 만족하는 스탯 조합만 True로 마스킹 (1순위 풀)
        tier1_mask = mask & (survival_probabilities >= target_prob / 100)

        # 체력 조건 규칙 정의
        is_life_orb = (pkm1.item == "생명의구슬")
        is_sitrus_berry = (pkm1.item == "자뭉열매")

        benefical_hp_rule1 = np.where(
            is_sitrus_berry, 
            (H % 2 == 0),  # 자뭉열매일 때 짝수 체력
            (H % 2 != 0)   # 그 외에는 홀수 체력
        )
        
        benefical_hp_rule2 = np.where(
            (H % 2 != 0),
            np.where(
                is_life_orb,
                (H % 10 == 9),  # 10n - 1
                (H % 16 == 15)  # 16n - 1
            ),
            True
        )

        # 각 순위별 독립 마스크 생성 (전체 SP 제한 범위 내에서 검사)
        pure_tier2_mask = mask & benefical_hp_rule1
        pure_tier3_mask = mask & benefical_hp_rule2

        # 1순위 만족 조합 확인
        applied_tier1 = np.any(tier1_mask)
        
        # 2순위: 1순위 안에서 찾되, 없으면 2순위 조건만 단독으로 만족하는 풀에서 탐색
        tier2_mask = tier1_mask & benefical_hp_rule1
        if np.any(tier2_mask):
            applied_tier2 = True
        elif np.any(pure_tier2_mask):
            tier2_mask = pure_tier2_mask
            applied_tier2 = "조건 완화(2순위 단독)"
        else:
            tier2_mask = np.zeros_like(mask, dtype=bool)
            applied_tier2 = False

        # 3순위: 직전 풀(2순위 또는 1순위) 안에서 찾되, 없으면 3순위 조건만 단독으로 만족하는 풀에서 탐색
        base_pool_for_3 = tier2_mask if np.any(tier2_mask) else (tier1_mask if applied_tier1 else mask)
        tier3_mask = base_pool_for_3 & benefical_hp_rule2
        
        if np.any(tier3_mask):
            applied_tier3 = True
        elif np.any(pure_tier3_mask):
            tier3_mask = pure_tier3_mask
            applied_tier3 = "조건 완화(3순위 단독)"
        else:
            tier3_mask = np.zeros_like(mask, dtype=bool)
            applied_tier3 = False

        # 최종 최적화 풀 결정 (3순위 -> 2순위 -> 1순위 순으로 우선 적용)
        if np.any(tier3_mask):
            final_optimized_mask = tier3_mask
        elif np.any(tier2_mask):
            final_optimized_mask = tier2_mask
        elif applied_tier1:
            final_optimized_mask = tier1_mask
        else:
            # 모든 조건이 안 되면 전체 유효 범위에서 가중치 기반 탐색
            final_optimized_mask = mask

        print(f"\n[우선순위 독립 적용 결과]")
        print(f"\n1순위(목표 내구도) 만족 조합 수: {np.sum(tier1_mask)}개")
        print(f"\n2순위(체력 실수치 조건) 적용 상태: {applied_tier2}")
        print(f"\n3순위(체력 실수치 홀수 조건) 적용 상태: {applied_tier3}")
        print(f"\n최종 조건 만족 스탯 조합 수: {np.sum(final_optimized_mask)}개")

        Bulk_phys = np.floor(H * B / 0.411)
        Bulk_sp = np.floor(H * D / 0.411)

        phys_norm = Bulk_phys / np.nanmax(Bulk_phys)
        sp_norm = Bulk_sp / np.nanmax(Bulk_sp)

        score = w_def * phys_norm + w_spdef * sp_norm
        total_sp = H_sp + B_sp + D_sp

        # 유효한 SP 분배만 점수 계산에 사용
        score = np.where(mask, score, -np.inf)

        if np.any(final_optimized_mask):
            min_sp = int(np.min(total_sp[final_optimized_mask]))
            max_sp = int(np.max(total_sp[final_optimized_mask]))

            min_candidates = final_optimized_mask & (total_sp == min_sp)
            min_score_max = np.max(score[min_candidates])
            min_sp_positions = np.argwhere(min_candidates & (score == min_score_max))

            max_candidates = final_optimized_mask & (total_sp == max_sp)
            max_score_max = np.max(score[max_candidates])
            max_sp_positions = np.argwhere(max_candidates & (score == max_score_max))

            optimal_score = np.where(final_optimized_mask, score, -np.inf)
            max_val = np.max(optimal_score)
            positions = np.argwhere(optimal_score == max_val)

            distribution_groups = [
                (f"최소 생존 SP ({min_sp} SP)", min_sp_positions),
                (f"최대 생존 SP ({max_sp} SP)", max_sp_positions),
            ]
        else:
            print(f"⚠️조건을 만족하는 포인트 분배가 없습니다. 가중치 기반 내구 최적화를 진행합니다.")
            min_sp = None
            max_sp = None
            min_sp_positions = None
            max_sp_positions = None

            if not np.any(np.isfinite(score)):
                raise ValueError("⚠️유효한 SP 분배가 없습니다.")

            max_val = np.max(score)
            positions = np.argwhere(score == max_val)

            distribution_groups = [
                ("최적 내구 분배 (조건 미충족)", positions),
            ]

        print("\n=============== 내구 최적 분배 ===============")

        results = []

        for group_name, group_positions in distribution_groups:
            print(f"\n{'=' * 12} {group_name} {'=' * 12}")

            for h, b, d in group_positions:
                h, b, d = int(h), int(b), int(d)

                h_val = H[h, b, d]
                b_val = float(B[h, b, d])
                d_val = float(D[h, b, d])

                hp_rm_cases = HP_rm[:, h, b, d] 
                tg_hp_val = h * (1 - current_hp_percent / 100)

                survived_cases = hp_rm_cases > tg_hp_val
                survival_prob = (np.sum(survived_cases) / len(hp_rm_cases)) * 100

                best_remain_hp = float(np.max(hp_rm_cases))
                best_remain_pct = 0 if best_remain_hp < 0 else float((best_remain_hp / h_val) * 100)

                worst_remain_hp = float(np.min(hp_rm_cases))
                worst_remain_pct = 0 if worst_remain_hp < 0 else float((worst_remain_hp / h_val) * 100)

                result = {
                    "category": group_name,
                    "total_sp": h + b + d,
                    "hp_point": h,
                    "b_point": b,
                    "d_point": d,
                    "survival_probability": survival_prob,
                    "best_remain_hp": best_remain_hp,
                    "best_remain_percent": best_remain_pct,
                    "worst_remain_hp": worst_remain_hp,
                    "worst_remain_percent": worst_remain_pct,
                    "phys_bulk": float(Bulk_phys[h, b, d]),
                    "sp_bulk": float(Bulk_sp[h, b, d]),
                }
                results.append(result)

                print(
                    f"| 총 SP={h + b + d} "
                    f"(HP={h}, B={b}, D={d}) |\n"
                    f"| 실수치 (HP={int(h_val):d}, B={int(b_val):d}, D={int(d_val):d}) |\n"
                    f"| 현재 HP = {int(tg_hp_val):d} |\n"
                    f"| 생존 확률 = {survival_prob:.2f}% |\n"
                    f"| 남은 HP (최고) = {int(best_remain_hp):d} ({int(best_remain_pct):d}%) |\n"
                    f"| 남은 HP (최약) = {int(worst_remain_hp):d} ({int(worst_remain_pct):d}%) |\n"
                    f"| 물리 내구 = {int(Bulk_phys[h, b, d]):d} |\n"
                    f"| 특수 내구 = {int(Bulk_sp[h, b, d]):d} |"
                )

        return results

    def optimize_power_advanced(
            self,
            pkm1_data,
            pkm2_data,
            move_index,
            nature_a,
            rank_a,
            rank_b,
            hits,
            target_prob,
            weather,
            field,
            crit,
            sp_av,
            current_hp_percent
    ):
        available_sp = sp_av
        nature_modifier = nature_a
        move_dict = Move.load_move_dict()
        pkm1 = self._build_pokemon(pkm1_data)
        pkm2 = self._build_pokemon(pkm2_data)
        base_stats1 = pkm1_data["종족치"]
        Move1 = pkm1_data["기술"]
        real_stats2 = pkm2_data["실수치"]

        A01, C01 = base_stats1[1], base_stats1[3]
        H2, B2, D2 = real_stats2[0], real_stats2[2], real_stats2[4]

        # 상대방의 현재 체력 계산 (백분율 기준)
        target_hp = H2 * (current_hp_percent / 100.0)

        # 1. 입력된 기술 인덱스를 리스트로 통일
        move_indices = [int(move_index)] if isinstance(move_index, (int, float)) else list(move_index)

        # 2. 총 데미지 계산 공통 함수 (다단히트 및 연속 기술 조합용)
        def calculate_total_dmg(dmg_matrix, hits_val):
            dmg_matrix = np.array(dmg_matrix)
            if hits_val <= 1:
                return dmg_matrix
            dmg_sum = dmg_matrix  
            for _ in range(hits_val - 1):
                combined = dmg_sum[:, None, :] + dmg_matrix[None, :, :]
                dmg_sum = combined.reshape(-1, dmg_matrix.shape[1])
            return dmg_sum

        A_sp = np.arange(0, available_sp + 1)
        sequence_dmg_matrices = []
        dmg_outputs = []
        move_names_str = []

        # 3. 기술 리스트를 순서대로 순회하며 데미지 분포 누적 계산
        for m_idx in move_indices:
            move_name = Move1[m_idx - 1]
            move_names_str.append(move_name)
            atk_move = move_dict.get(move_name)
            
            # 물리/특수 카테고리 판별 (첫 번째 기술 기준 또는 개별 적용)
            if atk_move.category == "물리":
                A0, B = A01, B2
            elif atk_move.category == "특수":
                A0, B = C01, D2
            else:
                A0, B = A01, B2

            A = np.floor((A0 + A_sp + 20) * nature_modifier)

            dmg, _ = BattleCalculator(pkm1, pkm2, atk_move).calculate_damage(A, B, H2, rank_a, rank_b, weather, field, crit)
            dmg_output_single = DMGoutput_Bulk_Calculator(pkm1).calculate_dmg_output(A, atk_move, field, weather)
            
            # 각 기술별 타수 반영 후 리스트에 적재
            move_total_dmg = calculate_total_dmg(dmg, hits)
            sequence_dmg_matrices.append(move_total_dmg)
            dmg_outputs.append(dmg_output_single)

        # 4. 여러 기술(콤보)의 데미지 분포를 순서대로 합산 (Cartesian Sum)
        total_dmg = sequence_dmg_matrices[0]
        for next_dmg in sequence_dmg_matrices[1:]:
            combined = total_dmg[:, None, :] + next_dmg[None, :, :]
            total_dmg = combined.reshape(-1, total_dmg.shape[1])

        # 상대방의 현재 체력(target_hp)을 기준으로 기절(KO) 확률 계산
        ko_probabilities = np.mean(total_dmg >= target_hp, axis=0)
        combined_move_name = " , ".join(move_names_str)

        # 5. 기존 최적화 로직 수행 (단일/다중 공통)
        mask_target = (ko_probabilities >= target_prob / 100.0)
        mask_11n = (A % 11 == 0)

        valid_both = np.where(mask_target & mask_11n)[0]
        valid_target_only = np.where(mask_target & ~mask_11n)[0]
        valid_11n_only = np.where(~mask_target & mask_11n)[0]
        
        if len(valid_both) > 0:
            idx = valid_both[0]
            print("\n✨ [최적 조건] 목표 데미지와 11n 조건을 모두 만족하는 스탯을 선택했습니다.")
        elif len(valid_target_only) > 0:
            idx = valid_target_only[0]
            print("\n💡 [목표 우선] 11n을 만족하는 구간은 없으나, 목표 데미지를 충족하는 최소 스탯을 선택했습니다.")
        elif len(valid_11n_only) > 0:
            print("\n⚠️ [데미지 미달] 목표 데미지를 만족하는 구간이 없어, 11n 조건을 만족하는 후보 리스트를 출력합니다.")
            print("-" * 50)
            print(f"{'번호':<6} | {'스탯 포인트 (A_sp)':<15} | {'실수치 (A)':<10}")
            print("-" * 50)
            
            for i, v_idx in enumerate(valid_11n_only):
                print(f"[{i+1}]   | A_sp: {A_sp[v_idx]:<9} | A: {A[v_idx]:<10}")
            print("-" * 50)
            
            if len(valid_both) > 0:
                idx = valid_both[0]
                print("\n✨ [최적 조건] 목표 데미지와 11n 조건을 모두 만족하는 스탯을 선택했습니다.")
            elif len(valid_target_only) > 0:
                idx = valid_target_only[0]
                print("\n💡 [목표 우선] 11n을 만족하는 구간은 없으나, 목표 데미지를 충족하는 최소 스탯을 선택했습니다.")
            elif len(valid_11n_only) > 0:
                idx = valid_11n_only[-1]
                print(f"\n⚠️ [데미지 미달] 목표 데미지를 만족하는 구간이 없어, 11n 조건을 만족하는 최대 스탯(A_sp: {A_sp[idx]})을 자동 선택했습니다.")

        else:
            idx = -1
            print("\n⚠️ [최대 투자] 조건을 만족하는 값이 없어 남은 스탯 포인트를 전부 투자합니다.")

        if len(move_indices) == 1:
            title_text = f"기술명: {combined_move_name}"
            dmg_display = f"결정력: {int(dmg_outputs[0][idx])}"
            hits_text = f"목표 데미지 타수: {hits}타"
        else:
            title_text = f"기술명: {combined_move_name}"
            dmg_lines = [f"- {move_names_str[i]}: {int(dmg_outputs[i][idx])}" for i in range(len(move_indices))]
            dmg_display = "개별 결정력:\n" + "\n".join(dmg_lines)
            hits_text = f"행동 횟수: {len(move_indices)}턴"

        result = {
            "A_sp": int(A_sp[idx]),
            "A": int(A[idx]),

            "damage_min": int(total_dmg[0][idx]),
            "damage_max": int(total_dmg[-1][idx]),
            "damage_min_percent": int(round((total_dmg[0][idx] / H2) * 100)),
            "damage_max_percent": int(round((total_dmg[-1][idx] / H2) * 100)),

            "hits": len(move_indices),
            "ko_probability": float(round(ko_probabilities[idx] * 100, 2)),
        }

        if idx == -1:
            print(f"""
===== 결정력 최적 분배 =====
상대 현재 체력 비율: {current_hp_percent}% (실수치: {int(target_hp)})
스탯포인트: {result['A_sp']}
실수치: {result['A']}
{title_text}
{dmg_display}

총 데미지: {result['damage_min']} ~ {result['damage_max']}
데미지(% of Max HP): {result['damage_min_percent']}% ~ {result['damage_max_percent']}%
============================
""")
        else:
            print(f"""
===== 결정력 최적 분배 =====
상대 현재 체력 비율: {current_hp_percent}% (실수치: {int(target_hp)})
스탯포인트: {result['A_sp']}
실수치: {result['A']}
{title_text}
{dmg_display}

총 데미지: {result['damage_min']} ~ {result['damage_max']}
데미지(% of Max HP): {result['damage_min_percent']}% ~ {result['damage_max_percent']}%

{hits_text}
기절 확률(%): {result['ko_probability']}%
============================
""")
        return result

    def optimize_speed_advanced(
            self,
            pkm1_data, 
            pkm2_data,
            sp_av,
            nature_s, 
            rank, 
            pkm1_item
    ):  
        available_sp = sp_av
        nature_modifier = nature_s
        pkm1_s0 = pkm1_data["종족치"][5]
        pkm2_s = pkm2_data["실수치"][5]
        pkm2_item = pkm2_data["지닌도구"]

        S_sp = np.arange(0, available_sp + 1)
        pkm1_s = np.floor(np.floor((pkm1_s0 + S_sp + 20) * nature_modifier) * (2 + rank) / 2)

        if pkm1_item == 1:
            pkm1_s = np.floor(pkm1_s * 1.5)
        
        if pkm2_item == "구애스카프":
            pkm2_s = np.floor(pkm2_s * 1.5)

        valid_idx = np.where(pkm1_s > pkm2_s)[0]
        if len(valid_idx) == 0:
            idx = -1
            result = {
                "스탯최대투자": {
                    "SP": int(S_sp[idx]),
                    "실수치": int(pkm1_s[idx])
                }
            }
            print("\n[추월 최소 값]")
            print("⚠️ 조건을 만족하는 스탯 분배가 없어, 남은 스탯 포인트를 전부 투자합니다.")
            print(f"→ SP {result['스탯최대투자']['SP']} / 실수치 {result['스탯최대투자']['실수치']}")
        else:
            idx = valid_valid_idx = valid_idx[0]
            result = {
                "목표최소값": {
                    "SP": int(S_sp[idx]),
                    "실수치": int(pkm1_s[idx])
                },
                "전체": [
                    {"SP": int(sp), "실수치": int(s)}
                    for sp, s in zip(S_sp[valid_idx], pkm1_s[valid_idx])
                ]
            }

            print("\n[추월 최소 값]")
            if result.get("목표최소값"):
                rslt = result["목표최소값"]
                print(f"→ SP {rslt['SP']} / 실수치 {rslt['실수치']}")
            else:
                print("없음")

            print("\n[추월 가능 스탯 전체]")
            print("-" * 30)
            print(f"{'SP':>5} | {'실수치':>6}")
            print("-" * 30)

            for row in result.get("전체", []):
                print(f"{row['SP']:>5} | {row['실수치']:>6}")
        
        return result
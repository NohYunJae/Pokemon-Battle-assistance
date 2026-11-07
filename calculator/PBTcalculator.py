import numpy as np
from .PBTmodifiers import Power_modifiers, Bulk_modifiers, CriticalHitManager
from .utils.type_chart import type_chart

class BattleCalculator:
    def __init__(self, attacker, defender, move):
        self.attacker = attacker
        self.defender = defender
        self.move = move
    
    def _base_damage(self, atk_stat, def_stat, rank_a, rank_b, field):
        level = 50
        def calculate_ranked_stat(base_stat: int, rank: int) -> int:
            if not -6 <= rank <= 6:
                raise ValueError("랭크는 -6에서 +6 사이여야 합니다.")

            if rank >= 0:
                return (base_stat * (2 + rank)) // 2
            else:
                return (base_stat * 2) // (2 + abs(rank))
        
        power = self.move.power
        atk_stat = calculate_ranked_stat(atk_stat, rank_a)
        def_stat = calculate_ranked_stat(def_stat, rank_b)

        pmods = Power_modifiers(self.attacker, self.move)
        p_ability_mod, self.move.type = pmods.ability_mods()
        f_ability_mod, self.move.type, power = pmods.field_mods(field=field)
        item_power_mod, mod_atk_stat = pmods.item_mods(atk_stat)

        bmods = Bulk_modifiers(self.attacker, self.defender, self.move)
        d_ability_mod = bmods.ability_mods()
        mod_def_stat = bmods.item_mods(def_stat)

        power = int(power * f_ability_mod)
        power = int(power * p_ability_mod)
        power = int(power * item_power_mod)
        power = int(power * d_ability_mod)
        power = max(1, power)

        lv_damage = 2 * level // 5 + 2
        step1 = lv_damage * power * mod_atk_stat
        step2 = step1 // mod_def_stat
        step3 = step2 // 50
        base = step3 + 2
        if self.move.category == "변화":
            base = 0
        return base

    def calculate_damage(self, atk_stat, def_stat, def_hp, rank_a = 0, rank_b = 0, weather=None, field=None, critical=False):
        def apply_pokerng_rounding(acc: int, numerator: int) -> int:
            """
            PokeRNG 반올림 연산 규칙: (acc * numerator + 2048) // 4096
            """
            return ((acc * numerator) + 2048) // 4096
        def apply_other_modifiers(dmg: int, mod_numerators: list[int]) -> int:
            """
            최종 기타 보정(Other Modifiers)을 누적 연산 후 데미지에 적용합니다.
            
            :param dmg: 난수/상성까지 적용된 중간 데미지 값
            :param mod_numerators: 적용할 보정치 분자 목록 (예: [2048, 5325])
            :return: 최종 기타 보정이 완료된 데미지 값
            """
            if not mod_numerators:
                return dmg

            other_acc = 4096

            for num in mod_numerators:
                other_acc = apply_pokerng_rounding(other_acc, num)

            final_dmg = (dmg * other_acc) // 4096

            return final_dmg

        # 1. 날씨 및 급소 보정 계산
        weather_mod = 4096
        if weather == "비":
            if self.move.type == "물": weather_mod = 6144
            elif self.move.type == "불꽃": weather_mod = 2048
        elif weather == "쾌청":
            if self.move.type == "불꽃": weather_mod = 6144
            elif self.move.type == "물": weather_mod = 2048
        elif weather == "눈":
            if "얼음" in self.defender.type and self.move.type == "물리":
                def_stat = def_stat * 6144 // 4096
        elif weather == "모래바람":
            if "바위" in self.defender.type and self.move.type == "특수":
                def_stat = def_stat * 6144 // 4096

        base_damage = self._base_damage(atk_stat, def_stat, rank_a, rank_b, field)
        damages = []
        percentages = []

        crit = CriticalHitManager(self.attacker,self.defender,self.move)
        critical = crit.is_always_critical()
        crit_mod = 6144 if critical else 4096

        for roll in range(85, 101):
            dmg = base_damage

            if weather_mod != 4096:
                dmg = (dmg * weather_mod) // 4096
                
            if crit_mod != 4096:
                dmg = (dmg * crit_mod) // 4096

            dmg = (dmg * roll) // 100

            if self.attacker.ability == "적응력" and self.move.type in self.attacker.types:
                dmg = (dmg * 8192) // 4096
            elif self.move.type in self.attacker.types:
                dmg = (dmg * 6144) // 4096

            type_mod = 1.0
            for t in self.defender.types:
                type_mod *= type_chart.get(self.move.type, {}).get(t, 1.0)
            dmg = np.floor(dmg * type_mod)

            other_mods = []
            if self.defender.ability in ["멀티스케일", "스펙터가드"] and getattr(self.defender, "hp_percent", 100) == 100:
                other_mods.append(2048)

            if self.attacker.item == "생명의구슬":
                other_mods.append(5325)

            if self.attacker.item == "달인의띠" and type_mod > 1.0:
                other_mods.append(4915)

            dmg = apply_other_modifiers(dmg, other_mods)

            damages.append(dmg)
            percentages.append(np.round(dmg / def_hp * 100, 1))

        return damages, percentages
    
    def calculate_speed(self, rank_a, rank_b, item_a=None, item_b=None, weather=None):
        pkm_a = self.attacker
        pkm_b = self.defender
        def calculate_ranked_stat(base_stat: int, rank: int) -> int:
            if not -6 <= rank <= 6:
                raise ValueError("랭크는 -6에서 +6 사이여야 합니다.")

            if rank >= 0:
                return (base_stat * (2 + rank)) // 2
            else:
                return (base_stat * 2) // (2 + abs(rank))
            
        def apply_item_modifiers(base_stat: int, item: str) -> int:
            if item == "구애스카프":
                return (base_stat * 3) // 2
            else:
                return base_stat
            
        def apply_ability_modifiers(base_stat: int, ability: str, weather) -> int:
            if ability == "곡예":
                return base_stat * 2
            
            elif ability == "쓱쓱" and weather == "비":
                return base_stat * 2

            elif ability == "모래헤치기" and weather == "모래바람":
                return base_stat * 2
            
            else:
                return base_stat

        speed_a = calculate_ranked_stat(self.attacker.stats[5], rank_a)
        speed_b = calculate_ranked_stat(self.defender.stats[5], rank_b)

        speed_a = apply_ability_modifiers(speed_a, pkm_a.ability, weather)
        speed_b = apply_ability_modifiers(speed_b, pkm_b.ability, weather)
        
        speed_a = apply_item_modifiers(speed_a, item_a)
        speed_b = apply_item_modifiers(speed_b, item_b)

        return speed_a, speed_b

class DMGoutput_Bulk_Calculator:
    def __init__(self, pkm):
        self.pkm = pkm

    def _base_dmg_output(self, atk_stat, move, field = None):
        power = move.power

        powrmods = Power_modifiers(self.pkm, move)
        f_ability_mod, move.type, power = powrmods.field_mods(field=field)
        ability_mod, move.type = powrmods.ability_mods()
        item_power_mod, atk_stat_mod = powrmods.item_mods(atk_stat)

        power = int(power * f_ability_mod)
        power = int(power * ability_mod)
        power = int(power * item_power_mod)
        power = max(1, power)

        fp_bs = atk_stat_mod * power

        if move.category == "변화":
            fp_bs = 0

        return fp_bs
    
    def calculate_dmg_output(self, atk_stat, move, field = None, weather = None):
        def apply_pokerng_rounding(acc: int, numerator: int) -> int:
            """
            PokeRNG 반올림 연산 규칙: (acc * numerator + 2048) // 4096
            """
            return ((acc * numerator) + 2048) // 4096

        def apply_other_modifiers(dmg: int, mod_numerators: list[int]) -> int:
            """
            최종 기타 보정(Other Modifiers)을 누적 연산 후 데미지에 적용합니다.
            
            :param dmg: 난수/상성까지 적용된 중간 데미지 값
            :param mod_numerators: 적용할 보정치 분자 목록 (예: [2048, 5325])
            :return: 최종 기타 보정이 완료된 데미지 값
            """
            if not mod_numerators:
                return dmg

            other_acc = 4096

            for num in mod_numerators:
                other_acc = apply_pokerng_rounding(other_acc, num)

            final_dmg = (dmg * other_acc) // 4096

            return final_dmg
        
        weather_mod = 4096
        if weather == "비":
            if move.type == "물": weather_mod = 6144
            elif move.type == "불꽃": weather_mod = 2048
        elif weather == "쾌청":
            if move.type == "불꽃": weather_mod = 6144
            elif move.type == "물": weather_mod = 2048

        base_fp = self._base_dmg_output(atk_stat, move, field)
        dmg_output = base_fp

        if weather_mod != 4096:
            dmg_output = (dmg_output * weather_mod) // 4096

        if self.pkm.ability == "적응력" and move.type in self.pkm.types:
            dmg_output = (dmg_output * 8192) // 4096
        elif move.type in self.pkm.types:
            dmg_output = (dmg_output * 6144) // 4096

        other_mods4fp = []
        if self.pkm.item == "생명의구슬":
            other_mods4fp.append(5325)

        dmg_output = apply_other_modifiers(dmg_output, other_mods4fp)
        
        return dmg_output

    def calculate_bulk(self, H, B, D, weather):
        if weather == "눈":
            if "얼음" in self.pkm.type:
                B = B * 6144 // 4096
        elif weather == "모래바람":
            if "바위" in self.pkm.type:
                D = D * 6144 // 4096

        if self.pkm.item == "돌격조끼":
            D = D * 6144 // 4096

        physical_bulk = int(H * B / 0.411)
        special_bulk = int(H * D / 0.411)

        return physical_bulk, special_bulk

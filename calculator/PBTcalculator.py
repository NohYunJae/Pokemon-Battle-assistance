import numpy as np
from .PBTmodifiers import Power_modifiers, Bulk_modifiers, CriticalHitManager
from .utils.type_chart import type_chart
from .utils.abilities import MULTI_STRIKE_MOVES, ALWAYS_CRIT_MOVES

def poke_round_half_down(value: int, numerator: int) -> int:
    """
    5세대 이후 표준 4096 스케일 반올림 (0.5에서 내림: round half down)
    """
    return (value * numerator + 2047) // 4096

def poke_round_half_up(value: int, numerator: int) -> int:
    """
    other 보정 누적 시 사용하는 4096 스케일 반올림 (0.5에서 올림: round half up)
    """
    return (value * numerator + 2048) // 4096


class DummyObject:
    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)


class BattleCalculator:
    def __init__(self, attacker, defender, move):
        self.attacker = attacker
        self.defender = defender
        self.move = move

    def _base_damage(self, atk_stat, def_stat, rank_a, rank_b, field, status_a, status_b, critical=False):
        level = 50

        def calculate_ranked_stat(base_stat: int, rank: int) -> int:
            if not -6 <= rank <= 6:
                raise ValueError("랭크는 -6에서 +6 사이여야 합니다.")
            if rank >= 0:
                return (base_stat * (2 + rank)) // 2
            else:
                return (base_stat * 2) // (2 + abs(rank))

        eff_rank_a = max(0, rank_a) if critical else rank_a
        eff_rank_b = min(0, rank_b) if critical else rank_b

        atk_stat = calculate_ranked_stat(atk_stat, eff_rank_a)
        def_stat = calculate_ranked_stat(def_stat, eff_rank_b)

        move_type = self.move.type
        power = self.move.power

        pmods = Power_modifiers(self.attacker, self.move)
        p_ability_mod, move_type, atk_stat, power = pmods.ability_mods(atk_stat, status_a, move_type, power)
        f_ability_mod, move_type, power = pmods.field_mods(field=field, move_type=move_type, power=power)
        item_power_mod, mod_atk_stat = pmods.item_mods(atk_stat, move_type)

        bmods = Bulk_modifiers(self.attacker, self.defender, self.move)
        d_ability_mod, def_stat = bmods.ability_mods(status_b, def_stat, move_type)
        mod_def_stat = bmods.item_mods(def_stat)

        power = poke_round_half_down(power, int(round(f_ability_mod * 4096)))
        power = poke_round_half_down(power, int(round(p_ability_mod * 4096)))
        power = poke_round_half_down(power, int(round(item_power_mod * 4096)))
        power = poke_round_half_down(power, int(round(d_ability_mod * 4096)))
        power = max(1, power)

        lv_damage = (2 * level) // 5 + 2
        step1 = lv_damage * power * mod_atk_stat
        step2 = step1 // mod_def_stat
        step3 = step2 // 50
        base = step3 + 2

        if self.move.category == "변화":
            base = 0

        return base, move_type
    
    def _apply_paradox_boost(self, pokemon, stats, weather, field):
        if len(stats) < 6:
            return stats

        is_proto = pokemon.ability == "고대활성" and (
            weather == "쾌청" or pokemon.item == "부스트에너지"
        )
        is_quark = pokemon.ability == "쿼크차지" and (
            field == "일렉트릭필드" or pokemon.item == "부스트에너지"
        )

        if is_proto or is_quark:
            idx = max(range(1, 6), key=lambda i: stats[i])
            mult = 1.5 if idx == 5 else 1.3
            stats[idx] = int(np.floor(stats[idx] * mult))

        return stats
    
    def calculate_damage(
        self,
        atk_stat,
        def_stat,
        def_hp,
        rank_a=0,
        rank_b=0,
        weather=None,
        field=None,
        critical=False,
        status=(None, None),
        is_spread=False,
        tera_type=None,
    ):
        def apply_other_modifiers(dmg, mod_numerators: list[int]):
            if not mod_numerators:
                return dmg
            other_acc = 4096
            for num in mod_numerators:
                other_acc = poke_round_half_up(other_acc, num)
            return poke_round_half_down(dmg, other_acc)
        
        status_a, status_b = status if isinstance(status, (tuple, list)) else (status, None)

        if weather == "눈" and "얼음" in self.defender.types and self.move.category == "물리":
            def_stat = (def_stat * 3) // 2
        elif weather == "모래바람" and "바위" in self.defender.types and self.move.category == "특수":
            def_stat = (def_stat * 3) // 2

        crit_mgr = CriticalHitManager(self.attacker, self.defender, self.move)
        is_crit = crit_mgr.evaluate_critical(user_critical=critical, status_b=status_b)
        
        atk_stats = self.attacker.stats
        def_stats = self.defender.stats
        if self.move.category == "물리":
            atk_stats[1] = atk_stat
            def_stats[2] = def_stat
        elif self.move.category == "특수":
            atk_stats[3] = atk_stat
            def_stats[4] = def_stat

        atk_stats = self._apply_paradox_boost(self.attacker, atk_stats, weather, field)

        def_stats = self._apply_paradox_boost(self.defender, def_stats, weather, field)

        if self.move.category == "물리":
            atk_stat = atk_stats[1]
            def_stat = def_stats[2]
        elif self.move.category == "특수":
            atk_stat = atk_stats[3]
            def_stat = def_stats[4]

        if self.move.name == "바디프레스":
            atk_stat = atk_stats[2]

        base_damage, eff_move_type = self._base_damage(
            atk_stat, def_stat, rank_a, rank_b, field, status_a, status_b, critical=is_crit
        )

        weather_num = 4096
        has_weather_negate = (
            self.attacker.ability in ["날씨부정", "에어록"]
            or self.defender.ability in ["날씨부정", "에어록"]
        )
        if not has_weather_negate:
            if weather == "비":
                if eff_move_type == "물":
                    weather_num = 6144
                elif eff_move_type == "불꽃":
                    weather_num = 2048
            elif weather == "쾌청":
                if eff_move_type == "불꽃" or self.move.name == "하이드로스팀":
                    weather_num = 6144
                elif eff_move_type == "물":
                    weather_num = 2048

        type_mod = 1.0
        for t in self.defender.types:
            if self.move.name == "프리즈드라이" and t == "물":
                eff = 2.0
            else:
                eff = type_chart.get(eff_move_type, {}).get(t, 1.0)
            type_mod *= eff

        if type_mod == 0.0:
            if isinstance(def_hp, np.ndarray):
                zero_arr = np.zeros((16, *def_hp.shape), dtype=np.int64)
                return zero_arr, np.zeros_like(zero_arr, dtype=np.float64)
            return [0] * 16, [0.0] * 16

        orig_types = self.attacker.types
        is_adaptability = self.attacker.ability == "적응력"
        stab_num = 4096

        if tera_type:
            in_orig = eff_move_type in orig_types
            in_tera = eff_move_type == tera_type
            if in_orig and in_tera:
                stab_num = 9216 if is_adaptability else 8192
            elif in_tera:
                stab_num = 8192 if is_adaptability else 6144
            elif in_orig:
                stab_num = 6144
        else:
            if eff_move_type in orig_types:
                stab_num = 8192 if is_adaptability else 6144

        damages = []
        percentages = []

        for roll in range(85, 101):
            dmg = base_damage

            if is_spread:
                dmg = poke_round_half_down(dmg, 3072)

            if weather_num != 4096:
                dmg = poke_round_half_down(dmg, weather_num)

            if is_crit:
                dmg = poke_round_half_down(dmg, 6144)

            dmg = (dmg * roll) // 100

            if self.attacker.ability == "적응력" and eff_move_type in self.attacker.types:
                dmg = dmg * 2
            elif stab_num != 4096:
                dmg = poke_round_half_down(dmg, stab_num)
            elif self.attacker.ability == "변환자재":
                dmg = (dmg * 6144) // 4096

            dmg = dmg * type_mod
            if isinstance(dmg, np.ndarray):
                dmg = np.floor(dmg).astype(np.int64)
            else:
                dmg = int(dmg)

            if (
                status_a == "화상"
                and self.move.category == "물리"
                and self.attacker.ability != "근성"
                and self.move.name != "객기"
            ):
                dmg = poke_round_half_down(dmg, 2048)

            other_mods = []
            if self.defender.ability in ["멀티스케일", "스펙터가드"] and getattr(self.defender, "hp_percent", 100) == 100:
                other_mods.append(2048)

            if self.attacker.item == "생명의구슬":
                other_mods.append(5324)

            if self.attacker.item == "달인의띠" and type_mod > 1.0:
                other_mods.append(4915)

            dmg = apply_other_modifiers(dmg, other_mods)

            if isinstance(dmg, np.ndarray):
                dmg = np.maximum(1, dmg)
                pct = np.round(dmg / def_hp * 100, 1)
            else:
                dmg = max(1, dmg)
                pct = float(np.round(dmg / def_hp * 100, 1))

            damages.append(dmg)
            percentages.append(pct)

        if damages and isinstance(damages[0], np.ndarray):
            return np.stack(damages, axis=0), np.stack(percentages, axis=0)

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
                return (base_stat * 6144) // 4096
            return base_stat

        def apply_ability_modifiers(base_stat: int, ability: str, weather) -> int:
            if ability == "곡예":
                return base_stat * 2
            elif ability == "쓱쓱" and weather == "비":
                return base_stat * 2
            elif ability == "모래헤치기" and weather == "모래바람":
                return base_stat * 2
            return base_stat

        speed_a = calculate_ranked_stat(self.attacker.stats[5], rank_a)
        speed_b = calculate_ranked_stat(self.defender.stats[5], rank_b)

        speed_a = apply_ability_modifiers(speed_a, pkm_a.ability, weather)
        speed_b = apply_ability_modifiers(speed_b, pkm_b.ability, weather)

        speed_a = apply_item_modifiers(speed_a, item_a)
        speed_b = apply_item_modifiers(speed_b, item_b)

        return speed_a, speed_b


class DMGoutput_Bulk_Calculator:
    def __init__(self, pkm, move):
        self.pkm = pkm
        self.move = move

    def _base_dmg_output(self, atk_stat, move, field=None, status=None, rank_a=0, is_crit=False):
        if move.category == "변화":
            if isinstance(atk_stat, np.ndarray):
                return np.zeros_like(atk_stat, dtype=np.float64), move.type
            return 0.0, move.type

        def calculate_ranked_stat(base_stat, rank: int):
            if not -6 <= rank <= 6:
                raise ValueError("랭크는 -6에서 +6 사이여야 합니다.")
            if rank >= 0:
                return (base_stat * (2 + rank)) // 2
            else:
                return (base_stat * 2) // (2 + abs(rank))

        move_type = move.type
        power = np.asarray(move.power, dtype=np.float64) if isinstance(move.power, np.ndarray) else float(move.power)

        eff_rank_a = max(0, rank_a) if is_crit else rank_a
        atk_stat = calculate_ranked_stat(atk_stat, eff_rank_a)

        powrmods = Power_modifiers(self.pkm, move)
        ability_mod, move_type, atk_stat, power = powrmods.ability_mods(atk_stat, status, move_type, power)
        f_ability_mod, move_type, power = powrmods.field_mods(field=field, move_type=move_type, power=power)
        item_power_mod, final_atk_stat = powrmods.item_mods(atk_stat, move_type)

        power = power * f_ability_mod * ability_mod * item_power_mod
        if isinstance(power, np.ndarray) or isinstance(final_atk_stat, np.ndarray):
            power_arr = np.maximum(1.0, np.asarray(power, dtype=np.float64))
            atk_arr = np.asarray(final_atk_stat, dtype=np.float64)
            fp_bs = atk_arr * power_arr
        else:
            power_val = max(1.0, float(power))
            fp_bs = float(final_atk_stat) * power_val

        return fp_bs, move_type
    
    def _apply_paradox_boost(self, pokemon, stats, weather, field):
        if len(stats) < 6:
            return stats

        is_proto = pokemon.ability == "고대활성" and (
            weather == "쾌청" or pokemon.item == "부스트에너지"
        )
        is_quark = pokemon.ability == "쿼크차지" and (
            field == "일렉트릭필드" or pokemon.item == "부스트에너지"
        )

        if is_proto or is_quark:
            idx = max(range(1, 6), key=lambda i: stats[i])
            mult = 1.5 if idx == 5 else 1.3
            stats[idx] = int(np.floor(stats[idx] * mult))

        return stats
    
    def calculate_dmg_output(
        self,
        atk_stat,
        field=None,
        weather=None,
        status=None,
        rank_a=0,
        tera_type=None,
        is_sub_call=False,
    ):
        base_move_name = self.move.name.split("_sub")[0]

        multi_cat = None
        for cat, moves in MULTI_STRIKE_MOVES.items():
            if base_move_name in moves:
                multi_cat = cat
                break

        hit_count = 1
        if multi_cat and not is_sub_call:
            is_loaded_dice = getattr(self.pkm, "item", None) == "속임수주사위"
            if multi_cat == "multi_2_5":
                hit_count = 4 if is_loaded_dice else 3
            elif multi_cat == "multi_2":
                hit_count = 2
            elif multi_cat == "multi_3":
                hit_count = 3
            elif multi_cat == "multi_10":
                hit_count = 10

        atk_stats = self.pkm.stats
        if self.move.category == "물리":
            atk_stats[1] = atk_stat
        elif self.move.category == "특수":
            atk_stats[3] = atk_stat

        atk_stats = self._apply_paradox_boost(self.pkm, atk_stats, weather, field)

        if self.move.category == "물리":
            atk_stat = atk_stats[1]
        elif self.move.category == "특수":
            atk_stat = atk_stats[3]

        if self.move.name == "바디프레스":
            atk_stat = atk_stats[2]

        is_always_crit = base_move_name in ALWAYS_CRIT_MOVES

        if multi_cat and not is_sub_call and base_move_name in ["트리플킥", "트리플악셀"]:
            hit_powers = {"트리플킥": [10, 20, 30], "트리플악셀": [20, 40, 60]}[
                base_move_name
            ][:hit_count]
            total_dmg_output = 0
            for p in hit_powers:
                temp_move = DummyObject(
                    name=f"{base_move_name}_sub",
                    power=p,
                    type=self.move.type,
                    category=self.move.category,
                    contact=getattr(self.move, "contact", False),
                )
                temp_calc = DMGoutput_Bulk_Calculator(self.pkm, temp_move)
                total_dmg_output += temp_calc.calculate_dmg_output(
                    atk_stat, field, weather, status, rank_a, tera_type, is_sub_call=True
                )
            if isinstance(total_dmg_output, np.ndarray):
                return np.floor(total_dmg_output).astype(np.int64)
            return int(np.floor(total_dmg_output))

        base_fp, eff_move_type = self._base_dmg_output(
            atk_stat, self.move, field, status, rank_a, is_crit=is_always_crit
        )
        dmg_output = np.asarray(base_fp, dtype=np.float64) if isinstance(base_fp, np.ndarray) else float(base_fp)

        weather_multiplier = 1.0
        if weather == "비":
            if eff_move_type == "물":
                weather_multiplier = 1.5
            elif eff_move_type == "불꽃":
                weather_multiplier = 0.5
        elif weather == "쾌청":
            if eff_move_type == "불꽃" or base_move_name in [
                "하이드로스팀",
            ]:
                weather_multiplier = 1.5
            elif eff_move_type == "물":
                weather_multiplier = 0.5

        dmg_output = dmg_output * weather_multiplier

        if is_always_crit:
            dmg_output = dmg_output * 1.5

        orig_types = self.pkm.types
        is_adaptability = self.pkm.ability == "적응력"
        stab_multiplier = 1.0

        if tera_type:
            in_orig = eff_move_type in orig_types
            in_tera = eff_move_type == tera_type
            if in_orig and in_tera:
                stab_multiplier = 2.25 if is_adaptability else 2.0
            elif in_tera:
                stab_multiplier = 2.0 if is_adaptability else 1.5
            elif in_orig:
                stab_multiplier = 1.5
        else:
            if eff_move_type in orig_types:
                stab_multiplier = 2.0 if is_adaptability else 1.5

        if (
            self.pkm.ability == "적응력"
            and eff_move_type in orig_types
            and not tera_type
        ):
            dmg_output = dmg_output * 2.0
        elif stab_multiplier != 1.0:
            dmg_output = dmg_output * stab_multiplier
        elif self.pkm.ability == "변환자재":
            dmg_output = dmg_output * 1.5

        if (
            status == "화상"
            and self.move.category == "물리"
            and self.pkm.ability != "근성"
            and not base_move_name.endswith("객기")
        ):
            dmg_output = dmg_output * 0.5

        if self.pkm.item == "생명의구슬":
            dmg_output = dmg_output * 1.3

        if multi_cat and not is_sub_call and base_move_name not in ["트리플킥", "트리플악셀"]:
            dmg_output = dmg_output * hit_count

        if isinstance(dmg_output, np.ndarray):
            return np.floor(dmg_output).astype(np.int64)
        return int(np.floor(dmg_output))

    def calculate_bulk(self, H, B, D, weather, field, status, rank_b=0):
        def has_status(status):
            return bool(status)

        def calculate_ranked_stat(base_stat: int, rank: int) -> int:
            if not -6 <= rank <= 6:
                raise ValueError("랭크는 -6에서 +6 사이여야 합니다.")
            if rank >= 0:
                return (base_stat * (2 + rank)) // 2
            else:
                return (base_stat * 2) // (2 + abs(rank))
            
        pkm_stats = self.pkm.stats
        pkm_stats[2] = B
        pkm_stats[4] = D
        pkm_stats = self._apply_paradox_boost(self.pkm, pkm_stats, weather, field)
        B = pkm_stats[2]
        D = pkm_stats[4]

        rank_b_ = rank_b if self.move.category == "물리" else 0
        rank_d = rank_b if self.move.category == "특수" else 0

        ranked_B = calculate_ranked_stat(B, rank_b_)
        ranked_D = calculate_ranked_stat(D, rank_d)

        if weather == "눈" and "얼음" in self.pkm.types:
            ranked_B = (ranked_B * 3) // 2
        elif weather == "모래바람" and "바위" in self.pkm.types:
            ranked_D = (ranked_D * 3) // 2

        if self.pkm.item == "돌격조끼":
            ranked_D = (ranked_D * 3) // 2

        if self.pkm.ability == "이상한비늘" and has_status(status):
            ranked_B = (ranked_B * 3) // 2

        physical_bulk = int(H * ranked_B / 0.411)
        special_bulk = int(H * ranked_D / 0.411)

        return physical_bulk, special_bulk
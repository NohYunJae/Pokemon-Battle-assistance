from .utils.abilities import (
    MEGA_LAUNCHER_MOVES,
    STRONG_JAW_MOVES,
    SHARP_MOVES,
    IRON_FIST_MOVES,
    ALWAYS_CRIT_MOVES,
    HIGH_CRIT_MOVES,
)
from .utils.items import TYPE_BOOST_ITEMS


class CriticalHitManager:
    def __init__(self, attacker, defender, move):
        self.attacker = attacker
        self.defender = defender
        self.move = move

    def evaluate_critical(self, user_critical: bool = False, status_b=None) -> bool:
        """
        급소 여부 판정:
        1) 상대 특성이 '전투무장' 또는 '조가비갑옷'이면 무조건 False
        2) 확정 급소 기술이거나, 대상이 독 상태 + 공격자 '무도한행동', 또는 급소 랭크 +3 이상이면 True
        3) 그 외에는 사용자가 지정한 user_critical 값 반환
        """
        if self.defender.ability in ["전투무장", "조가비갑옷"]:
            return False

        if self.move.name in ALWAYS_CRIT_MOVES:
            return True

        if self.attacker.ability == "무도한행동" and status_b in ["독", "맹독"]:
            return True

        crit_stage = 0
        if self.move.name in HIGH_CRIT_MOVES:
            crit_stage += 1
        if self.attacker.item in ["초점렌즈", "예리한손톱"]:
            crit_stage += 1
        if self.attacker.ability == "대운":
            crit_stage += 1
        if self.attacker.name in ["파오리", "가라르파오리", "창파나이트"] and self.attacker.item == "대파":
            crit_stage += 2

        if crit_stage >= 3:
            return True

        return user_critical


class Power_modifiers:
    def __init__(self, pkm, move):
        self.pkm = pkm
        self.move = move

    def ability_mods(self, atk_stat, status, move_type=None, power=None):
        move_type = move_type if move_type is not None else self.move.type
        power = power if power is not None else self.move.power
        ability_mod = 1.0
        atk_stat_mod_num = None
        ability = self.pkm.ability

        if ability == "단단한발톱" and self.move.contact:
            ability_mod = 1.3

        elif ability == "메가런처" and self.move.name in MEGA_LAUNCHER_MOVES:
            ability_mod = 1.5

        elif ability == "옹골찬턱" and self.move.name in STRONG_JAW_MOVES:
            ability_mod = 1.5

        elif ability == "예리함" and self.move.name in SHARP_MOVES:
            ability_mod = 1.5

        elif ability == "스카이스킨" and move_type == "노말":
            move_type = "비행"
            ability_mod = 1.2

        elif ability == "페어리스킨" and move_type == "노말":
            move_type = "페어리"
            ability_mod = 1.2

        elif ability == "프리즈스킨" and move_type == "노말":
            move_type = "얼음"
            ability_mod = 1.2

        elif ability == "일렉트릭스킨" and move_type == "노말":
            move_type = "전기"
            ability_mod = 1.2

        elif ability == "드래곤스킨" and move_type == "노말":
            move_type = "드래곤"
            ability_mod = 1.2

        elif ability == "테크니션" and power <= 60:
            ability_mod = 1.5

        elif ability == "철주먹" and self.move.name in IRON_FIST_MOVES:
            ability_mod = 1.2

        elif ability == "천하장사" and self.move.category == "물리":
            ability_mod = 2.0

        elif ability == "근성" and bool(status) and self.move.category == "물리":
            atk_stat_mod_num = 6144

        elif ability in ["진홍빛고동", "하드론엔진"]:
            atk_stat_mod_num = 5461

        if self.move.name == "객기" and bool(status):
            power = 140

        return ability_mod, move_type, atk_stat, power, atk_stat_mod_num

    def field_mods(self, field, move_type=None, power=None):
        move_type = move_type if move_type is not None else self.move.type
        power = power if power is not None else self.move.power

        is_airborne = (
            self.pkm.ability == "부유"
            or (isinstance(self.pkm.types, str) and self.pkm.types == "비행")
            or (isinstance(self.pkm.types, (list, tuple)) and "비행" in self.pkm.types)
        )

        if is_airborne or not field:
            return 1.0, move_type, power

        field_mod = 1.0
        if field == "그래스필드":
            if self.move.name == "대지의파동":
                move_type = "풀"
                power = 100
            if move_type == "풀":
                field_mod = 1.3
            elif self.move.name in ["지진", "매그니튜드", "땅고르기"]:
                field_mod = 0.5

        elif field == "미스트필드":
            if self.move.name == "대지의파동":
                move_type = "페어리"
                power = 100
            if move_type == "드래곤":
                field_mod = 0.5
            elif self.move.name == "미스트버스트":
                power = 150

        elif field == "일렉트릭필드":
            if self.move.name == "대지의파동":
                move_type = "전기"
                power = 100
            if move_type == "전기":
                field_mod = 1.3
                
        elif field == "사이코필드":
            if self.move.name == "대지의파동":
                move_type = "에스퍼"
                power = 100
            if self.move.name == "와이드포스":
                power = 120
            if move_type == "에스퍼":
                field_mod = 1.3

        return field_mod, move_type, power

    def item_mods(self, atk_stat, move_type=None):
        move_type = move_type if move_type is not None else self.move.type

        atk_stat_mod_num = None
        if self.pkm.item == "구애머리띠" and self.move.category == "물리":
            atk_stat_mod_num = 6144
        elif self.pkm.item == "구애안경" and self.move.category == "특수":
            atk_stat_mod_num = 6144

        item_power_mod = 1.2 if TYPE_BOOST_ITEMS.get(self.pkm.item) == move_type else 1.0
        return item_power_mod, atk_stat, atk_stat_mod_num


class Bulk_modifiers:
    def __init__(self, attacker, defender, move):
        self.attacker = attacker
        self.defender = defender
        self.move = move

    def ability_mods(self, status, def_stat, move_type=None):
        move_type = move_type if move_type is not None else self.move.type
        ability_mod = 1.0
        def_stat_mod_num = None
        ability = self.defender.ability

        if ability == "두꺼운지방" and move_type in ["얼음", "불꽃"]:
            ability_mod = 0.5
        elif ability in ["타오르는불꽃", "부유", "저수"]:
            if (
                (ability == "타오르는불꽃" and move_type == "불꽃")
                or (ability == "부유" and move_type == "땅")
                or (ability == "저수" and move_type == "물")
            ):
                ability_mod = 0.0
        elif ability == "이상한비늘" and bool(status) and self.move.category == "물리":
            def_stat_mod_num = 6144

        return ability_mod, def_stat, def_stat_mod_num

    def item_mods(self, def_stat):
        def_stat_mod_num = None
        if self.defender.item == "돌격조끼" and self.move.category == "특수":
            def_stat_mod_num = 6144
        elif self.defender.item == "진화의휘석":
            def_stat_mod_num = 6144

        return def_stat, def_stat_mod_num

from .utils.abilities import MEGA_LAUNCHER_MOVES, STRONG_JAW_MOVES, SHARP_MOVES, IRON_FIST_MOVES, ALWAYS_CRIT_MOVES, HIGH_CRIT_MOVES
from .utils.items import TYPE_BOOST_ITEMS

class CriticalHitManager:
    def __init__(self, attacker, defender, move):
        self.attacker = attacker
        self.defender = defender
        self.move = move

    def is_always_critical(self) -> bool:
        """
        확정 급소 상태인지 판정 (상대 특성 '전투무장', '조개껍질' 일때 급소불가)
        """
        if self.defender.ability in ["전부무장", "조개껍질"]:
            return False

        if self.move.name in ALWAYS_CRIT_MOVES:
            return True

        crit_stage = 0
        if self.move.name in HIGH_CRIT_MOVES:
            crit_stage += 1
        if self.attacker.item in ["초점렌즈", "대운의부적"]:
            crit_stage += 1
        if self.attacker.ability == "대운":
            crit_stage += 1

        return crit_stage >= 3
    
class Power_modifiers:
    def __init__(self, pkm, move):
        self.pkm = pkm
        self.move = move

    def ability_mods(self, atk_stat, status):
        def has_status(status):
            return bool(status)
        
        ability_mod = 1

        if self.pkm.ability == "단단한발톱" and self.move.contact:
            ability_mod = 1.3

        elif self.pkm.ability == "메가런처" and self.move.name in MEGA_LAUNCHER_MOVES:
            ability_mod = 1.5

        elif self.pkm.ability == "옹골찬턱" and self.move.name in STRONG_JAW_MOVES:
            ability_mod = 1.5

        elif self.pkm.ability == "예리함" and self.move.name in SHARP_MOVES:
            ability_mod = 1.5

        elif self.pkm.ability == "스카이스킨" and self.move.type == "노말":
            self.move.type = "비행"
            ability_mod = 1.2

        elif self.pkm.ability == "페어리스킨" and self.move.type == "노말":
            self.move.type = "페어리"
            ability_mod = 1.2

        elif self.pkm.ability == "프리즈스킨" and self.move.type == "노말":
            self.move.type = "얼음"
            ability_mod = 1.2

        elif self.pkm.ability == "일렉트릭스킨" and self.move.type == "노말":
            self.move.type = "전기"
            ability_mod = 1.2

        elif self.pkm.ability == "드래곤스킨" and self.move.type == "노말":
            self.move.type = "드래곤"
            ability_mod = 1.2

        elif self.pkm.ability == "테크니션" and self.move.power <= 60:
            ability_mod = 1.5

        elif self.pkm.ability == "철주먹" and self.move.name in IRON_FIST_MOVES:
            ability_mod = 1.2

        elif self.pkm.ability == "천하장사" and self.move.category == "물리":
            ability_mod = 2

        elif self.pkm.ability == "근성" and has_status(status) and self.move.category == "물리":
            ability_mod = 1
            atk_stat = atk_stat * 3 // 2

        if self.move.name == "객기" and has_status(status):
            self.move.power = 140
            ability_mod = 1

        return ability_mod, self.move.type, atk_stat, self.move.power
    
    def field_mods(self, field):
        is_airborne = (
            self.pkm.ability == "부유" or 
            (isinstance(self.pkm.types, str) and self.pkm.types == "비행") or 
            (isinstance(self.pkm.types, (list, tuple)) and "비행" in self.pkm.types)
        )
        
        if is_airborne or not field:
            return 1, self.move.type, self.move.power

        if field == "그래스필드":
            if self.pkm.ability == "의태":
                self.pkm.types = "풀"
            if self.move.name == "대지의파동":
                self.move.type = "풀"
                self.move.power = 100
            if self.move.type == "풀":
                field_mod = 1.3
            elif self.move.name in ["지진", "매그니튜드", "땅고르기"]:
                field_mod = 0.5
            else:
                field_mod = 1

        elif field == "미스트필드":
            if self.pkm.ability == "의태":
                self.pkm.types = "페어리"
            if self.move.name == "대지의파동":
                self.move.type = "페어리"
                self.move.power = 100
            if self.move.type == "드래곤":
                field_mod = 0.5
            elif self.move.name == "미스트버스트":
                self.move.power = 150
                field_mod = 1
            else:
                field_mod = 1

        elif field == "일렉트릭필드":
            if self.pkm.ability == "의태":
                self.pkm.types = "전기"
            if self.move.name == "대지의파동":
                self.move.type = "전기"
                self.move.power = 100

            if self.move.type == "전기":
                field_mod = 1.3
            else:
                field_mod = 1

        elif field == "사이코필드":
            if self.pkm.ability == "의태":
                self.pkm.types = "에스퍼"
            if self.move.name == "대지의파동":
                self.move.type = "에스퍼"
                self.move.power = 100
            if self.move.name == "와이드포스":
                self.move.power = 120
            if self.move.type == "에스퍼":
                field_mod = 1.3
            else:
                field_mod = 1
        else:
            field_mod = 1

        return field_mod, self.move.type, self.move.power

    def item_mods(self, atk_stat):
        if self.pkm.item == "구애머리띠" and self.move.category == "물리":
            atk_stat = atk_stat * 6144 // 4096

        elif self.pkm.item == "구애안경" and self.move.category == "특수":
            atk_stat = atk_stat * 6144 // 4096

        if TYPE_BOOST_ITEMS.get(self.pkm.item) == self.move.type:
            item_power_mod = 1.2
            
        else:
            item_power_mod = 1

        return item_power_mod, atk_stat

class Bulk_modifiers:
    def __init__(self, attacker, defender, move):
        self.attacker = attacker
        self.defender = defender
        self.move = move

    def ability_mods(self, status, def_stat):
        def has_status(status):
            return bool(status)
        
        if self.defender.ability == "두꺼운지방" and self.move.type in ["얼음", "불꽃"]:
            ability_mod = 0.5
       
        elif self.defender.ability == "타오르는불꽃" and self.move.type == "불꽃":
            ability_mod = 0

        elif self.defender.ability == "부유" and self.move.type == "땅":
            ability_mod = 0

        elif self.defender.ability == "저수" and self.move.type == "물":
            ability_mod  = 0

        elif (
            self.defender.ability == "이상한비늘"
            and has_status(status)
            and self.move.category == "물리"
        ):
            def_stat = def_stat * 3 // 2
            ability_mod = 1

        else:
            ability_mod = 1

        return ability_mod, def_stat

    def item_mods(self, def_stat):
        if self.defender.item == "돌격조끼" and self.move.category == "특수":
            def_stat = def_stat * 6144 // 4096
            
        elif self.defender.item == "진화의휘석":
            def_stat = def_stat * 6144 // 4096
            
        return def_stat

            



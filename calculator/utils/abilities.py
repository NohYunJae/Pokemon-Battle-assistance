MEGA_LAUNCHER_MOVES = {"물의파동", "용의파동", "악의파동", "치유의파동", "파동탄", "근원의파동", "대지의파동"}
STRONG_JAW_MOVES = {"물기", "꺠물어부수기", "불꽃엄니", "아가미물기", "필살앞니", "얼음엄니", "물고버티기", "맹독엄니", "사이코팽", "번개엄니"}
SHARP_MOVES = {
    "깜짝베기",
    "거수참",
    "도각참",
    "드래곤클로",
    "리프블레이드",
    "베어가르기",
    "브레이크클로",
    "비검천중파",
    "사이코커터",
    "섀도클로",
    "성스러운칼",
    "셸블레이드",
    "솔라블레이드",
    "시저크로스",
    "아쿠아커터",
    "암석액스",
    "에어슬래시",
    "에어커터",
    "연속자르기",
    "원념의칼",
    "잎날가르기",
    "제비반환",
    "찍찍베기",
    "크로스포이즌",
    "페이탈클로",
    "풀베기"
}
IRON_FIST_MOVES = {
    "그로우펀치",
    "냉동펀치",
    "드레인펀치",
    "마하펀치",
    "메가톤펀치",
    "번개펀치",
    "불꽃펀치",
    "불릿펀치",
    "섀도펀치",
    "스카이어퍼",
    "암해머",
    "연속펀치",
    "전광쌍격",
    "잼잼펀치",
    "코멧펀치",
    "폭발펀치",
    "힘껏펀치"
}
ALWAYS_CRIT_MOVES = {
    "암흑강타", "수류연타", "트릭플라워", "산통깨기", "얼음성채"
}
HIGH_CRIT_MOVES = {
    "깜빡베기", "섀도크루", "급소찌르기", "크로스포이즌", "스톤에지", 
    "드래곤다이브", "에어슬래시", "공격지령", "솔라블레이드"
}
# import numpy as np
# def round_half_down(x):
#     return np.floor(x + 0.5 - 1e-12)

# def round_half_up(x):
#     return np.floor(x + 0.5)

# class Calculate_mods:
#     def __init__(self):
#         self.value = 1.0

#     def apply_ability_mod(self, value, mods):
#         for m in mods:
#             value = round_half_down(value * m)
#         return int(value)

#     def apply_other_mods(self, mods):
#         acc = 4096

#         for m in mods:
#             acc = round_half_up(acc * m)

#         return (acc / 4096)

    # def ability_mod(self):
    #     if pkm2_ability == "단단한발톱" and mv_contact:
    #         move_mods = 1.3
    #     elif pkm2_ability == "메가런처" and move_name in MEGA_LAUNCHER_MOVES:
    #         move_mods = 1.5
    #     elif pkm2_ability == "옹골찬턱" and move_name in STRONG_JAW_MOVES:
    #         move_mods = 1.5
from types import SimpleNamespace

from calculator.stats import get_pokemon_stats
from loader.data_loader import Move
from calculator.PBTcalculator import DMGoutput_Bulk_Calculator

class Pokemon:
    move_dict = Move.load_move_dict()
    def __init__(self, name, nature, SPs, IVs=None, lv=50, item=None, ability=None):
        self.name = name
        self.nature = nature
        self.SPs = SPs
        self.IVs = IVs or [31] * 6
        self.lv = lv
        self.stats, self.types = get_pokemon_stats(name, nature, self.SPs, self.IVs, self.lv)
        self.item = item
        self.ability = ability
        self.pkm = SimpleNamespace(
                    name=self.name,
                    nature=self.nature,
                    SPs=self.SPs,
                    IVs=self.IVs,
                    lv=self.lv,
                    stats=self.stats,
                    types=self.types,
                    item=self.item,
                    ability=self.ability
                )

    def get_stat(self, stat_type):
        index = {"HP": 0, "A": 1, "B": 2, "C": 3, "D": 4, "S": 5}[stat_type]
        return self.stats[index]
    
    def calculate_DMG_output(self, move: Move, field, weather, status):
        if move.power == 0 or move.category == "변화":
            return 0
        
        A = self.get_stat("A") if move.category == "물리" else self.get_stat("C")
        dmg_output = DMGoutput_Bulk_Calculator(self.pkm, move).calculate_dmg_output(A, field, weather, status)
        return dmg_output
    
    def calculate_bulk(self, move: Move, weather, status):
        hp = self.get_stat("HP")
        b = self.get_stat("B")
        d = self.get_stat("D")
        
        physical_bulk, special_bulk = DMGoutput_Bulk_Calculator(self.pkm, move).calculate_bulk(hp, b, d, weather, status)
        return physical_bulk, special_bulk
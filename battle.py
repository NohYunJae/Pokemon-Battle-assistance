from pokemon import Pokemon
from calculator.PBTcalculator import BattleCalculator
from loader.data_loader import Move, PokemonCSVLoader

class Simulator:
    def __init__(self, sample1, sample2):
        csvloader = PokemonCSVLoader()
        self.data1 = csvloader.load_pokemon_data(f"data/samples/{sample1}")
        self.data2 = csvloader.load_pokemon_data(f"data/samples/{sample2}")
        self.pkm1 = self._build_pokemon(self.data1)
        self.pkm2 = self._build_pokemon(self.data2)
        self.move_dict = Move.load_move_dict()

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

    def make_battle_table(self):
        pkm1 = self.pkm1
        pkm2 = self.pkm2
        data1 = self.data1
        data2 = self.data2
        
        def get_damage_table(attacker, defender, move_names):
            table = []
            for move_name in move_names:
                if move_name not in self.move_dict:
                    print(f"Warning: {move_name} 기술이 존재하지 않습니다.")
                    continue
                move = self.move_dict[move_name]
                calculator = BattleCalculator(attacker, defender, move)

                atk_stat = attacker.get_stat("A") if move.category == "물리" else attacker.get_stat("C")
                def_stat = defender.get_stat("B") if move.category == "물리" else defender.get_stat("D")
                
                def_hp = defender.get_stat("HP")
                
                damages, per_damages = calculator.calculate_damage(atk_stat, def_stat, def_hp, weather=data1.get("날씨"), field=data1.get("필드"), status=data1.get("상태이상"))
                
                key_indices = [0, 5, 10, 15]
                filtered_damages = [damages[i] for i in key_indices]
                filtered_percents = [per_damages[i] for i in key_indices]
                
                table.append([move_name, move.category] + filtered_percents)
                
            return table

        damage_table1 = get_damage_table(pkm1, pkm2, data1["기술"])
        damage_table2 = get_damage_table(pkm2, pkm1, data2["기술"])
        
        return data1, data2, damage_table1, damage_table2
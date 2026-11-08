import os
import math
import tkinter as tk
import customtkinter as ctk
import threading

from PIL import Image
from pokemon import Pokemon
from pokeCSVbuilder import SampleCSVbuilder
from .utils.cache_manager import GameDataCache

DATA_DIR = os.path.join(os.path.expanduser("~"), "PokemonDATA", "data")
FONT_FAMILY = "Malgun Gothic"


class AutoCompleteEntry(ctk.CTkFrame):
    def __init__(self, master, suggestions=None, width=140, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.suggestions = suggestions or []
        self.lower_suggestions = [(item, item.lower()) for item in self.suggestions]
        self.width = width

        self.var = ctk.StringVar()
        self.var.trace_add("write", self.on_text_changed)

        self.entry = ctk.CTkEntry(
            self, textvariable=self.var, width=width, height=26,
            fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11)
        )
        self.entry.pack(fill="x")
        
        self.entry.bind("<Down>", self.on_key_down)
        self.entry.bind("<Up>", self.on_key_up)
        self.entry.bind("<Return>", self.on_return)
        self.entry.bind("<Tab>", self.on_tab)

        self.listbox_win = None
        self.listbox = None
        self._after_id = None

    def update_values(self, new_values):
        self.suggestions = new_values or []
        self.lower_suggestions = [(item, item.lower()) for item in self.suggestions]

    def on_text_changed(self, *args):
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(30, self._process_text_change)

    def _process_text_change(self):
        typed = self.var.get().strip().lower()
        if not typed or len(typed) < 1:
            self.hide_dropdown()
            return
        
        matches = []
        for item, item_lower in self.lower_suggestions:
            if typed in item_lower:
                matches.append(item)
                if len(matches) >= 6:
                    break

        if matches:
            self.show_dropdown(matches)
        else:
            self.hide_dropdown()

    def show_dropdown(self, matches):
        if self.listbox_win is None or not self.listbox_win.winfo_exists():
            self.listbox_win = tk.Toplevel(self)
            self.listbox_win.wm_overrideredirect(True)
            self.listbox_win.attributes("-topmost", True)
            self.listbox = tk.Listbox(
                self.listbox_win, width=18, height=len(matches),
                bg="#082746", fg="#ffffff", selectbackground="#ef4444", selectforeground="#ffffff",
                font=(FONT_FAMILY, 9), bd=0, highlightthickness=0
            )
            self.listbox.pack(fill="both", expand=True)
            self.listbox.bind("<<ListboxSelect>>", self.on_select)
            self.listbox.bind("<Return>", self.on_return)

        self.listbox.delete(0, tk.END)
        for m in matches:
            self.listbox.insert(tk.END, m)
        self.listbox.config(height=len(matches))
        try:
            x = self.entry.winfo_rootx()
            y = self.entry.winfo_rooty() + self.entry.winfo_height()
            self.listbox_win.geometry(f"{self.entry.winfo_width()}x{len(matches)*18}+{x}+{y}")
            self.listbox_win.deiconify()
        except Exception:
            pass

    def hide_dropdown(self):
        if self.listbox_win and self.listbox_win.winfo_exists():
            self.listbox_win.withdraw()

    def on_select(self, event):
        if self.listbox and self.listbox.curselection():
            self.var.set(self.listbox.get(self.listbox.curselection()[0]))
            self.hide_dropdown()

    def on_key_down(self, event):
        if self.listbox_win and self.listbox_win.winfo_exists() and self.listbox.size() > 0:
            cur = self.listbox.curselection()
            next_index = 0 if not cur else min(cur[0] + 1, self.listbox.size() - 1)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(next_index)
            self.listbox.see(next_index)
            return "break"

    def on_key_up(self, event):
        if self.listbox_win and self.listbox_win.winfo_exists() and self.listbox.size() > 0:
            cur = self.listbox.curselection()
            next_index = self.listbox.size() - 1 if not cur else max(cur[0] - 1, 0)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(next_index)
            self.listbox.see(next_index)
            return "break"

    def on_return(self, event):
        if self.listbox_win and self.listbox_win.winfo_exists() and self.listbox.curselection():
            self.on_select(event)
            return "break"

    def on_tab(self, event):
        self.hide_dropdown()
        return None

    def get(self): return self.var.get()
    def set(self, value): self.var.set(value)


class SampleView:
    def __init__(self, parent_tab):
        self.tab = parent_tab
        self.pokemon_list = []
        self.move_list = []
        self.pending_sample_data = None  # 미리보기 상태에서 저장할 데이터를 담을 변수
        
        self.create_widgets()
        self.load_pokemon_image("samplesheetimg", size=(300, 200))
        
        threading.Thread(target=self._load_cache_background, daemon=True).start()

    def _load_cache_background(self):
        try:
            pokedex_names = GameDataCache.get_pokedex_names()
            move_names = GameDataCache.get_move_names()
            self.tab.after(0, lambda: self._on_cache_loaded(pokedex_names, move_names))
        except Exception as e:
            print(f"캐시 로드 오류: {e}")

    def _on_cache_loaded(self, pokedex_names, move_names):
        self.pokemon_list = pokedex_names or []
        self.move_list = move_names or []
        
        if hasattr(self, 'entry_name'):
            self.entry_name.update_values(self.pokemon_list)
        if hasattr(self, 'entry_moves'):
            for m_entry in self.entry_moves:
                m_entry.update_values(self.move_list)

    def load_pokemon_image(self, pokemon_name, size=(100, 100)):
        try:
            img_path = os.path.join(DATA_DIR, "images", f"{pokemon_name}.png")
            if not os.path.exists(img_path):
                if hasattr(self, 'image_label'):
                    self.image_label.configure(text="이미지 없음", image="")
                return

            pil_img = Image.open(img_path)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
            
            if hasattr(self, 'image_label'):
                self.image_label.configure(text="", image=ctk_img)
                self.image_label.image = ctk_img
            elif hasattr(self, 'bg_image_label'):
                self.bg_image_label.configure(image=ctk_img)
                self.bg_image_label.image = ctk_img
                
        except Exception as e:
            print(f"이미지 로드 오류: {e}")

    def create_widgets(self):
        main_card = ctk.CTkFrame(self.tab, fg_color="#DAF6FE", corner_radius=12, border_width=2, border_color="#000000")
        main_card.pack(fill="both", expand=True, padx=8, pady=4)

        title_ribbon = ctk.CTkFrame(main_card, fg_color="#FFFFFF", corner_radius=8, border_width=1.5, border_color="#000000", height=30)
        title_ribbon.pack(anchor="w", padx=12, pady=(8, 4))
        ctk.CTkLabel(title_ribbon, text="포켓몬 배틀 샘플 생성기", text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack(side="left", padx=10, pady=2)

        split_container = ctk.CTkFrame(main_card, fg_color="transparent")
        split_container.pack(fill="both", expand=True, padx=8, pady=4)

        left_frame = ctk.CTkFrame(split_container, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=False, padx=(0, 4))

        self.bg_image_label = ctk.CTkLabel(left_frame, text="", fg_color="transparent")
        self.bg_image_label.place(relx=0.5, rely=0.86, anchor="center")

        right_frame = ctk.CTkFrame(split_container, fg_color="#E6F7FF", corner_radius=10, border_width=1.5, border_color="#000000")
        right_frame.pack(side="right", fill="both", expand=True, padx=(4, 0), pady=2)

        ctk.CTkLabel(right_frame, text="[실시간 결과 시트 미리보기]", text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))
        
        self.canvas_container = ctk.CTkFrame(right_frame, fg_color="#ffffff", corner_radius=8, border_width=1, border_color="#000000")
        self.canvas_container.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        self.result_canvas = tk.Canvas(self.canvas_container, bg="#ffffff", highlightthickness=0)
        self.v_scrollbar = ctk.CTkScrollbar(self.canvas_container, orientation="vertical", command=self.result_canvas.yview)
        self.h_scrollbar = ctk.CTkScrollbar(self.canvas_container, orientation="horizontal", command=self.result_canvas.xview)
        
        self.result_canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        self.v_scrollbar.pack(side="right", fill="y")
        self.h_scrollbar.pack(side="bottom", fill="x")
        self.result_canvas.pack(side="left", fill="both", expand=True)

        self.result_inner_frame = ctk.CTkFrame(self.result_canvas, fg_color="#ffffff")
        self.canvas_window = self.result_canvas.create_window((0, 0), window=self.result_inner_frame, anchor="nw")

        def _on_frame_configure(event):
            self.result_canvas.configure(scrollregion=self.result_canvas.bbox("all"))
        self.result_inner_frame.bind("<Configure>", _on_frame_configure)

        self.init_placeholder = ctk.CTkLabel(self.result_inner_frame, text="미리보기를 누르면 여기에 표시됩니다.", text_color="#666666", font=(FONT_FAMILY, 11))
        self.init_placeholder.pack(padx=20, pady=40)

        # 미리보기 하단 저장/취소 버튼 영역 (초기에는 숨김 또는 비활성화 상태)
        self.preview_action_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        self.preview_action_frame.pack(fill="x", padx=8, pady=(0, 8))

        self.btn_save = ctk.CTkButton(
            self.preview_action_frame, text="저장하기", fg_color="#10b981", hover_color="#059669", text_color="#ffffff",
            font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=11), height=32, corner_radius=6,
            command=self.on_confirm_save
        )
        self.btn_save.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_cancel = ctk.CTkButton(
            self.preview_action_frame, text="취소", fg_color="#6b7280", hover_color="#4b5563", text_color="#ffffff",
            font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=11), height=32, corner_radius=6, width=80,
            command=self.on_cancel_preview
        )
        self.btn_cancel.pack(side="right")
        self.preview_action_frame.pack_forget()  # 최초에는 숨김

        form_card = ctk.CTkFrame(left_frame, fg_color="#E6F7FF", corner_radius=10, border_width=1.5, border_color="#000000")
        form_card.pack(fill="x", padx=4, pady=4)

        form_grid = ctk.CTkFrame(form_card, fg_color="transparent")
        form_grid.pack(fill="x", padx=8, pady=8)

        ew = 130
        eh = 26

        fields = [
            [("파일명:", "entry_filename", "pikachu_sample", ctk.CTkEntry, None), ("포켓몬 이름:", "entry_name", "피카츄", AutoCompleteEntry, self.pokemon_list)],
            [("지닌도구:", "entry_item", "전기구슬", ctk.CTkEntry, None), ("특성:", "entry_ability", "피뢰침", ctk.CTkEntry, None)],
            [("성격:", "entry_nature", "겁쟁이", ctk.CTkEntry, None), ("날씨:", "combo_weather", ["", "쾌청", "비", "눈", "모래바람"], "combo", None)],
            [("노트:", "entry_note", "GUI 생성 샘플", ctk.CTkEntry, None), ("필드:", "combo_field", ["", "일렉트릭필드", "그래스필드", "사이코필드", "미스트필드"], "combo", None)]
        ]

        for r, row_items in enumerate(fields):
            for col_offset, item in enumerate(row_items):
                label_text, var_name, default_val, widget_type, sugg = item
                col_idx = col_offset * 2

                ctk.CTkLabel(form_grid, text=label_text, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=11)).grid(row=r, column=col_idx, sticky="w", padx=(2 if col_idx == 0 else 8, 2), pady=4)
                
                if widget_type == AutoCompleteEntry:
                    w = widget_type(form_grid, suggestions=sugg, width=ew)
                    w.set(default_val)
                    if var_name == "entry_name":
                        self.entry_name = w
                elif widget_type == "combo":
                    w = ctk.CTkComboBox(form_grid, values=default_val, width=ew, height=eh, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
                    w.set("")
                else:
                    w = ctk.CTkEntry(form_grid, width=ew, height=eh, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
                    w.insert(0, default_val)
                
                setattr(self, var_name, w)
                w.grid(row=r, column=col_idx + 1, sticky="w", padx=2, pady=4)

        sps_card = ctk.CTkFrame(left_frame, fg_color="#E6F7FF", corner_radius=10, border_width=1.5, border_color="#000000")
        sps_card.pack(fill="x", padx=4, pady=4)
        sps_inner = ctk.CTkFrame(sps_card, fg_color="transparent")
        sps_inner.pack(fill="x", padx=6, pady=5)
        ctk.CTkLabel(sps_inner, text="SPs [HP,A,B,C,D,S]:", text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=10)).pack(side="left", padx=2)
        
        self.entry_sps = []
        for i, lbl in enumerate(["HP", "A", "B", "C", "D", "S"]):
            ctk.CTkLabel(sps_inner, text=lbl, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=10)).pack(side="left", padx=(3, 1))
            e = ctk.CTkEntry(sps_inner, width=38, height=24, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
            e.pack(side="left", padx=1)
            e.insert(0, ["2", "0", "0", "32", "0", "32"][i])
            self.entry_sps.append(e)

        ivs_card = ctk.CTkFrame(left_frame, fg_color="#E6F7FF", corner_radius=10, border_width=1.5, border_color="#000000")
        ivs_card.pack(fill="x", padx=4, pady=4)
        ivs_inner = ctk.CTkFrame(ivs_card, fg_color="transparent")
        ivs_inner.pack(fill="x", padx=6, pady=5)
        ctk.CTkLabel(ivs_inner, text="IVs [HP,A,B,C,D,S]:", text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=10)).pack(side="left", padx=2)
        
        self.entry_ivs = []
        for i, lbl in enumerate(["HP", "A", "B", "C", "D", "S"]):
            ctk.CTkLabel(ivs_inner, text=lbl, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=10)).pack(side="left", padx=(3, 1))
            e = ctk.CTkEntry(ivs_inner, width=38, height=24, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
            e.pack(side="left", padx=1)
            e.insert(0, "31")
            self.entry_ivs.append(e)

        moves_card = ctk.CTkFrame(left_frame, fg_color="#E6F7FF", corner_radius=10, border_width=1.5, border_color="#000000")
        moves_card.pack(fill="x", padx=4, pady=4)
        moves_inner = ctk.CTkFrame(moves_card, fg_color="transparent")
        moves_inner.pack(fill="x", padx=6, pady=5)
        ctk.CTkLabel(moves_inner, text="기술 세팅:", text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=10)).pack(side="left", padx=2)
        
        self.entry_moves = []
        for i, dm in enumerate(["10만볼트", "볼트체인지", "풀묶기", "파도타기"]):
            e = AutoCompleteEntry(moves_inner, suggestions=self.move_list, width=68)
            e.pack(side="left", padx=1)
            e.set(dm)
            self.entry_moves.append(e)

        action_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        action_frame.pack(fill="x", padx=4, pady=(6, 8))

        self.log_box = ctk.CTkTextbox(action_frame, height=42, font=(FONT_FAMILY, 10), fg_color="#DBF4FF", text_color="#000000", corner_radius=8, border_width=1.5, border_color="#000000")
        self.log_box.pack(side="left", fill="both", expand=True, padx=(0, 4))
        self.log_box.insert("end", "[시스템] 준비 완료. 값을 입력 후 '미리보기'를 누르세요.\n")

        self.btn_submit = ctk.CTkButton(
            action_frame, text="미리보기", fg_color="#ef4444", hover_color="#dc2626", text_color="#ffffff",
            font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=11), height=42, width=75, corner_radius=8, border_width=1.5, border_color="#000000",
            command=self.on_submit
        )
        self.btn_submit.pack(side="right")

    def on_submit(self):
        """버튼 클릭 시 데이터를 계산하고 저장 대신 미리보기를 생성합니다."""
        try:
            filename = self.entry_filename.get().strip()
            name = self.entry_name.get().strip()
            note = self.entry_note.get().strip()
            item = self.entry_item.get().strip()
            ability = self.entry_ability.get().strip()
            nature = self.entry_nature.get().strip()
            level = 50
            
            SPs = [int(e.get().strip()) for e in self.entry_sps]
            IVs = [int(e.get().strip()) for e in self.entry_ivs]
            moves = [e.get().strip() for e in self.entry_moves if e.get().strip()]
            weather = self.combo_weather.get().strip() or None
            field = self.combo_field.get().strip() or None

            # 저장에 필요한 데이터를 임시 보관
            self.pending_sample_data = {
                "filename": filename, "name": name, "note": note, "item": item,
                "ability": ability, "nature": nature, "level": level,
                "SPs": SPs, "IVs": IVs, "moves": moves, "weather": weather, "field": field
            }

            self.log_box.insert("end", f"[미리보기] '{name}' 샘플 미리보기 생성됨. 저장 여부를 선택하세요.\n")
            self.log_box.see("end")

            pokedex_cache = GameDataCache.get_pokedex()
            pokemon_data = pokedex_cache.get(name)
            if not pokemon_data:
                raise ValueError(f"'{name}' 포켓몬이 Pokedex 캐시에 없습니다.")
            
            base_stats = pokemon_data["base_stats"]
            types = pokemon_data["types"]

            move_dict_cache = GameDataCache.get_move_dict()
            pkm = Pokemon(name, nature, SPs, IVs, level, item, ability)
            
            damages = []
            for m in moves:
                move_info = move_dict_cache.get(m, {"name": "알 수 없음", "type": "노말", "category": "물리", "power": 0})
                class DummyMove:
                    def __init__(self, d):
                        self.name = d.get("name", "알 수 없음")
                        self.type = d.get("type", "노말")
                        self.category = d.get("category", "물리")
                        self.power = d.get("power", 0)
                        self.contact = d.get("contact", "x")
                
                dmg_val = pkm.calculate_DMG_output(DummyMove(move_info), field, weather)
                damages.append(dmg_val)

            bulk = pkm.calculate_bulk(weather)
            if item == "구애스카프":
                spd = pkm.stats[5] * 3 // 2
            elif pkm.ability == "곡예":
                spd = pkm.stats[5] * 2
            else:
                spd = pkm.stats[5]

            def calculate_speed(base: int, nature_mod: float = 1.0, is_scarf: bool = False) -> int:
                base_calc = base + 52
                speed = math.floor(base_calc * nature_mod)
                return math.floor(speed * 1.5) if is_scarf else speed

            def find_out_run(target_actual_speed: int) -> list:
                results = []
                for nature_mod, is_scarf in [(1.0, False), (1.1, False), (1.0, True), (1.1, True)]:
                    max_base = None
                    for base in range(1, 201):
                        if calculate_speed(base, nature_mod, is_scarf) < target_actual_speed:
                            if max_base is None or base > max_base:
                                max_base = base
                    results.append(max_base)
                return results

            table_data = [
                ["포켓몬", name],
                ["타입"] + types,
                ["노트", note],
                ["지닌도구", item],
                ["특성", ability],
                ["LV", level],
                ["성격", nature],
                [""] + ["HP", "A", "B", "C", "D", "SPD"],
                ["종족치"] + base_stats,
                ["SPs"] + SPs,
                ["IVs"] + IVs,
                ["실수치"] + pkm.stats,
                ["날씨", weather or ""],
                ["필드", field or ""],
                ["기술"] + moves,
                ["DMG"] + damages,
                ["", "물리", "특수"],
                ["BULK", bulk[0], bulk[1]],
                [""] + ["무보정", "준속", "최속", "준속 스카프", "최속스카프"],
                ["속도 추월 라인"] + [spd - 21] + find_out_run(spd)
            ]

            for widget in self.result_inner_frame.winfo_children():
                widget.destroy()

            for r_idx, row in enumerate(table_data):
                for c_idx, val in enumerate(row):
                    is_h = (c_idx == 0)
                    ctk.CTkLabel(
                        self.result_inner_frame, text=str(val if val is not None else ""), width=75, height=22,
                        fg_color="#E6F7FF" if is_h else "#FFFFFF", text_color="#000000", corner_radius=3,
                        font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold" if is_h else "normal")
                    ).grid(row=r_idx, column=c_idx, padx=1, pady=1, sticky="nsew")

            # 미리보기 생성 완료 후 저장/취소 버튼 노출
            self.preview_action_frame.pack(fill="x", padx=8, pady=(0, 8))

        except Exception as e:
            self.log_box.insert("end", f"[오류] {str(e)}\n")
            self.log_box.see("end")

    def on_confirm_save(self):
        """미리보기 후 사용자가 [저장하기]를 눌렀을 때 실행됩니다."""
        if not self.pending_sample_data:
            return
        try:
            d = self.pending_sample_data
            saved_path = SampleCSVbuilder.make_sample_csv(
                d["filename"], d["name"], d["note"], d["item"], d["ability"], 
                d["nature"], d["level"], d["SPs"], d["IVs"], d["moves"], d["weather"], d["field"]
            )
            self.log_box.insert("end", f"[성공] 파일 저장 완료: {os.path.basename(saved_path)}\n")
            self.log_box.see("end")
            self.preview_action_frame.pack_forget()  # 저장 완료 후 버튼 숨김
            self.pending_sample_data = None
        except Exception as e:
            self.log_box.insert("end", f"[저장 오류] {str(e)}\n")
            self.log_box.see("end")

    def on_cancel_preview(self):
        """미리보기 후 사용자가 [취소]를 눌렀을 때 실행됩니다."""
        self.pending_sample_data = None
        self.preview_action_frame.pack_forget()
        for widget in self.result_inner_frame.winfo_children():
            widget.destroy()
        
        self.init_placeholder = ctk.CTkLabel(self.result_inner_frame, text="생성 버튼을 누르면 시트 미리보기가 여기에 표시됩니다.", text_color="#666666", font=(FONT_FAMILY, 11))
        self.init_placeholder.pack(padx=20, pady=40)
        self.log_box.insert("end", "[취소] 샘플 저장이 취소되었습니다.\n")
        self.log_box.see("end")
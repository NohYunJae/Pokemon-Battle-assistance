import os
import customtkinter as ctk
import tkinter as tk
import threading

from calculator.PBTcalculator import BattleCalculator
from calculator.stats import get_pokemon_stats
from .utils.cache_manager import GameDataCache
from calculator.utils.nature_chart import nature_chart

DATA_DIR = os.path.join(os.path.expanduser("~"), "PokemonDATA", "data")
FONT_FAMILY = "Malgun Gothic"

class AutocompleteCombobox(ctk.CTkFrame):
    def __init__(self, master, values=None, command=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.values = values or []
        self.command = command

        self.var = ctk.StringVar()
        self.entry = ctk.CTkEntry(self, textvariable=self.var, height=22, font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.entry.pack(side="left", fill="none", expand=False)
        
        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.entry.bind("<Return>", self._on_return)
        self.entry.bind("<Tab>", self._on_tab)
        self.entry.bind("<Down>", self._on_arrow_down)
        self.entry.bind("<Up>", self._on_arrow_up)
        
        if self.command:
            self.var.trace_add("write", lambda *args: self.command(self.var.get()))

        self.listbox_window = tk.Toplevel(self)
        self.listbox_window.wm_overrideredirect(True)
        self.listbox_window.attributes("-topmost", True)
        self.listbox_window.withdraw()

        self.listbox = tk.Listbox(
            self.listbox_window, 
            height=5, 
            font=(FONT_FAMILY, 11),
            bg="#F8FAFC",
            fg="#0F172A",
            selectbackground="#0284C7",
            selectforeground="#FFFFFF",
            relief="flat", 
            bd=0,
            highlightthickness=1,
            highlightcolor="#BAE6FD"
        )
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        self.listbox.bind("<Return>", self._on_return)

        self._debounce_timer = None

    def get(self):
        return self.var.get()

    def set(self, value):
        self.var.set(value)

    def update_values(self, new_values):
        self.values = new_values

    def _on_key_release(self, event):
        if event.keysym in ("Down", "Up", "Return", "Escape", "Tab"):
            return
        if self._debounce_timer is not None:
            self.after_cancel(self._debounce_timer)
        self._debounce_timer = self.after(80, self._perform_search)

    def _perform_search(self):
        typed = self.var.get().strip().lower()
        if not typed:
            self._close_listbox()
            return
        matches = [v for v in self.values if typed in v.lower()]
        if matches:
            self._show_listbox(matches)
        else:
            self._close_listbox()

    def _show_listbox(self, matches):
        self.listbox.delete(0, tk.END)
        for m in matches:
            self.listbox.insert(tk.END, m)
        self.listbox.config(height=min(len(matches), 5))

        try:
            x = self.entry.winfo_rootx()
            y = self.entry.winfo_rooty() + self.entry.winfo_height()
            width = self.entry.winfo_width()
            item_count = min(len(matches), 5)
            self.listbox_window.geometry(f"{width}x{item_count * 22}+{x}+{y}")
            self.listbox_window.deiconify()
        except Exception:
            pass

    def _on_arrow_down(self, event):
        if self.listbox and self.listbox.size() > 0:
            current = self.listbox.curselection()
            next_index = 0 if not current else (current[0] + 1) % self.listbox.size()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(next_index)
            self.listbox.see(next_index)
            return "break"

    def _on_arrow_up(self, event):
        if self.listbox and self.listbox.size() > 0:
            current = self.listbox.curselection()
            prev_index = self.listbox.size() - 1 if not current else (current[0] - 1) % self.listbox.size()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(prev_index)
            self.listbox.see(prev_index)
            return "break"

    def _on_select(self, event):
        if self.listbox and self.listbox.curselection():
            index = self.listbox.curselection()[0]
            selected = self.listbox.get(index)
            self.var.set(selected)
            self._close_listbox()
            self.entry.icursor(tk.END)
            if self.command:
                self.command(selected)

    def _on_return(self, event):
        if self.listbox_window and self.listbox_window.state() == "normal" and self.listbox.size() > 0:
            if not self.listbox.curselection():
                self.listbox.selection_set(0)
            self._on_select(None)
            return "break"
        else:
            self.entry.tk_focusNext().focus()
            return "break"

    def _on_tab(self, event):
        self._close_listbox()
        return None

    def _close_listbox(self):
        if self.listbox_window:
            try:
                self.listbox_window.withdraw()
            except Exception:
                pass


class DummyObject:
    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)


class SpdCalculatorView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.pack(fill="both", expand=True)

        self.nature_list = list(nature_chart.keys())
        self._is_initialized = False

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.left_frame = ctk.CTkFrame(self, fg_color="#F0F9FF", corner_radius=8, border_width=1.5, border_color="#000000")
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(5, 3), pady=5)

        self.right_frame = ctk.CTkFrame(self, fg_color="#F0F9FF", corner_radius=8, border_width=1.5, border_color="#000000")
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(3, 5), pady=5)

        title_label = ctk.CTkLabel(self.left_frame, text="스피드 비교 계산기", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"))
        title_label.pack(anchor="w", padx=12, pady=(8, 4))

        input_container = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        input_container.pack(fill="both", expand=False, padx=12, pady=2)

        # 포켓몬 A 설정
        pkm1_label = ctk.CTkLabel(input_container, text="[포켓몬 A 설정]", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=12))
        pkm1_label.pack(anchor="w", pady=(1, 1))
        
        self.pkm1_name_combo = self._create_autocomplete_row(input_container, "포켓몬:", [], command=lambda x: self.run_calculation())
        self.pkm1_nature_combo = self._create_combo_row(input_container, "성격:", self.nature_list, command=lambda x: self.run_calculation())
        self.pkm1_nature_combo.set("겁쟁이" if "겁쟁이" in self.nature_list else self.nature_list[0])
        
        self.pkm1_item_entry = self._create_input_row(input_container, "지닌물건:", "", command=lambda e: self.run_calculation())
        self.pkm1_ability_entry = self._create_input_row(input_container, "특성:", "", command=lambda e: self.run_calculation())
        
        self.pkm1_spd_entry, self.pkm1_rank_entry = self._create_sp_with_rank_row(
            input_container, ctk.StringVar(value="스피드 [SP]:"), "32", "0", command=lambda e: self.run_calculation()
        )

        # 포켓몬 B 설정
        pkm2_label = ctk.CTkLabel(input_container, text="[포켓몬 B 설정]", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=12))
        pkm2_label.pack(anchor="w", pady=(6, 1))

        self.pkm2_name_combo = self._create_autocomplete_row(input_container, "포켓몬:", [], command=lambda x: self.run_calculation())
        self.pkm2_nature_combo = self._create_combo_row(input_container, "성격:", self.nature_list, command=lambda x: self.run_calculation())
        self.pkm2_nature_combo.set("고집" if "고집" in self.nature_list else self.nature_list[0])

        self.pkm2_item_entry = self._create_input_row(input_container, "지닌물건:", "", command=lambda e: self.run_calculation())
        self.pkm2_ability_entry = self._create_input_row(input_container, "특성:", "", command=lambda e: self.run_calculation())
        
        self.pkm2_spd_entry, self.pkm2_rank_entry = self._create_sp_with_rank_row(
            input_container, ctk.StringVar(value="스피드 [SP]:"), "32", "0", command=lambda e: self.run_calculation()
        )

        # 환경 설정
        env_label = ctk.CTkLabel(input_container, text="[환경 설정]", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=12))
        env_label.pack(anchor="w", pady=(6, 1))

        self.weather_combo = self._create_combo_row(
            input_container, "날씨:", ["", "비", "모래바람", "쾌청", "눈"], 
            command=lambda x: self.run_calculation()
        )
        self.weather_combo.set("")

        # 우측 결과 창
        res_title_label = ctk.CTkLabel(self.right_frame, text="📊 스피드 비교 결과", font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"))
        res_title_label.pack(anchor="w", padx=15, pady=(15, 10))

        self.result_textbox = ctk.CTkTextbox(self.right_frame, fg_color="#FFFFFF", text_color="#1E293B", corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=13))
        self.result_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        self.result_textbox.configure(state="normal")
        self.result_textbox.delete("0.1", "end")
        self.result_textbox.insert("0.1", "⏳ [시스템] 캐시 초기화 중입니다... 잠시만 기다려주세요.")
        self.result_textbox.configure(state="disabled")

        threading.Thread(target=self._load_cache_background, daemon=True).start()

    def _load_cache_background(self):
        try:
            pokedex_cache = GameDataCache.get_pokedex()
            self.pokemon_list = list(pokedex_cache.keys())
            if not self.pokemon_list:
                self.pokemon_list = ["파오젠", "랜드로스", "우라오스"]

            self.after(0, self._on_cache_loaded)
        except Exception as e:
            self.after(0, lambda: self._on_cache_error(str(e)))

    def _on_cache_loaded(self):
        self.pkm1_name_combo.update_values(self.pokemon_list)
        self.pkm2_name_combo.update_values(self.pokemon_list)

        self.pkm1_name_combo.set("")
        self.pkm2_name_combo.set("")

        self._is_initialized = True
        self.run_calculation()

    def _on_cache_error(self, err_msg):
        self.result_textbox.configure(state="normal")
        self.result_textbox.delete("0.1", "end")
        self.result_textbox.insert("0.1", f"❌ [시스템] 캐시 초기화 중 오류 발생:\n{err_msg}")
        self.result_textbox.configure(state="disabled")

    def _create_input_row(self, parent, label_text, default_value="", command=None):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=1)
        lbl = ctk.CTkLabel(frame, text=label_text, width=80, anchor="w", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        lbl.pack(side="left")
        entry = ctk.CTkEntry(frame, width=120, height=20, font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        entry.pack(side="left")
        entry.insert(0, default_value)
        entry.bind("<Return>", lambda e: e.widget.tk_focusNext().focus())
        if command:
            entry.bind("<KeyRelease>", command)
        return entry

    def _create_sp_with_rank_row(self, parent, label_var, default_sp="32", default_rank="0", command=None):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=1)
        
        lbl = ctk.CTkLabel(frame, textvariable=label_var, width=80, anchor="w", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"))
        lbl.pack(side="left")

        right_sub_frame = ctk.CTkFrame(frame, fg_color="transparent")
        right_sub_frame.pack(side="left", fill="none")

        def adjust_value(entry_widget, delta, min_val, max_val):
            try:
                val = int(entry_widget.get().strip() or "0")
                new_val = min(max(val + delta, min_val), max_val)
                entry_widget.delete(0, "end")
                entry_widget.insert(0, str(new_val))
                if command:
                    command(None)
            except ValueError:
                entry_widget.delete(0, "end")
                entry_widget.insert(0, str(min_val))
                if command:
                    command(None)

        sp_entry = ctk.CTkEntry(right_sub_frame, width=45, height=19, font=ctk.CTkFont(family=FONT_FAMILY, size=11), justify="center")
        sp_entry.pack(side="left", padx=(0, 2))
        sp_entry.insert(0, default_sp)
        sp_entry.bind("<Return>", lambda e: e.widget.tk_focusNext().focus())
        if command:
            sp_entry.bind("<KeyRelease>", command)

        sp_btn_frame = ctk.CTkFrame(right_sub_frame, fg_color="transparent", width=14)
        sp_btn_frame.pack(side="left", padx=(0, 6))
        
        up_btn_s = ctk.CTkButton(sp_btn_frame, text="▲", width=14, height=9, font=ctk.CTkFont(family=FONT_FAMILY, size=7),
                                 fg_color="#E2E8F0", text_color="#334155", hover_color="#CBD5E1",
                                 command=lambda: adjust_value(sp_entry, 1, 0, 32))
        up_btn_s.pack(side="top", fill="x")
        down_btn_s = ctk.CTkButton(sp_btn_frame, text="▼", width=14, height=9, font=ctk.CTkFont(family=FONT_FAMILY, size=7),
                                   fg_color="#E2E8F0", text_color="#334155", hover_color="#CBD5E1",
                                   command=lambda: adjust_value(sp_entry, -1, 0, 32))
        down_btn_s.pack(side="bottom", fill="x")

        rank_lbl = ctk.CTkLabel(right_sub_frame, text="랭크:", font=ctk.CTkFont(family=FONT_FAMILY, size=10), anchor="e")
        rank_lbl.pack(side="left", padx=(0, 2))

        rank_entry = ctk.CTkEntry(right_sub_frame, width=35, height=19, font=ctk.CTkFont(family=FONT_FAMILY, size=11), justify="center")
        rank_entry.pack(side="left", padx=(0, 2))
        rank_entry.insert(0, default_rank)
        rank_entry.bind("<Return>", lambda e: e.widget.tk_focusNext().focus())
        if command:
            rank_entry.bind("<KeyRelease>", command)

        rank_btn_frame = ctk.CTkFrame(right_sub_frame, fg_color="transparent", width=14)
        rank_btn_frame.pack(side="left")

        up_btn_r = ctk.CTkButton(rank_btn_frame, text="▲", width=14, height=9, font=ctk.CTkFont(family=FONT_FAMILY, size=7),
                                 fg_color="#E2E8F0", text_color="#334155", hover_color="#CBD5E1",
                                 command=lambda: adjust_value(rank_entry, 1, -6, 6))
        up_btn_r.pack(side="top", fill="x")
        down_btn_r = ctk.CTkButton(rank_btn_frame, text="▼", width=14, height=9, font=ctk.CTkFont(family=FONT_FAMILY, size=7),
                                   fg_color="#E2E8F0", text_color="#334155", hover_color="#CBD5E1",
                                   command=lambda: adjust_value(rank_entry, -1, -6, 6))
        down_btn_r.pack(side="bottom", fill="x")

        return sp_entry, rank_entry

    def _create_combo_row(self, parent, label_text, values, command=None):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=1)
        lbl = ctk.CTkLabel(frame, text=label_text, width=80, anchor="w", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        lbl.pack(side="left")
        combo = ctk.CTkComboBox(frame, values=values, width=120, height=20, font=ctk.CTkFont(family=FONT_FAMILY, size=11), command=command)
        combo.pack(side="left")
        if values:
            combo.set(values[0])
        combo.bind("<Return>", lambda e: e.widget.tk_focusNext().focus())
        return combo

    def _create_autocomplete_row(self, parent, label_text, values, command=None):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=1)
        lbl = ctk.CTkLabel(frame, text=label_text, width=80, anchor="w", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        lbl.pack(side="left")

        ac_box = AutocompleteCombobox(frame, values=values, command=command)
        ac_box.entry.configure(width=120, height=20)
        ac_box.pack(side="left")
        if values:
            ac_box.set(values[0])
        return ac_box

    def run_calculation(self):
        if not getattr(self, "_is_initialized", False):
            return

        try:
            pkm1_name = self.pkm1_name_combo.get().strip()
            pkm1_nature = self.pkm1_nature_combo.get().strip()
            pkm1_item = self.pkm1_item_entry.get().strip()
            pkm1_ability = self.pkm1_ability_entry.get().strip()
            
            pkm1_sp_str = self.pkm1_spd_entry.get().strip()
            pkm1_sp_val = min(max(int(pkm1_sp_str) if pkm1_sp_str.isdigit() else 0, 0), 32)
            
            pkm1_rank_str = self.pkm1_rank_entry.get().strip()
            try:
                rank_a = int(pkm1_rank_str) if pkm1_rank_str else 0
            except ValueError:
                rank_a = 0
            rank_a = min(max(rank_a, -6), 6)

            pkm2_name = self.pkm2_name_combo.get().strip()
            pkm2_nature = self.pkm2_nature_combo.get().strip()
            pkm2_item = self.pkm2_item_entry.get().strip()
            pkm2_ability = self.pkm2_ability_entry.get().strip()
            
            pkm2_sp_str = self.pkm2_spd_entry.get().strip()
            pkm2_sp_val = min(max(int(pkm2_sp_str) if pkm2_sp_str.isdigit() else 0, 0), 32)
            
            pkm2_rank_str = self.pkm2_rank_entry.get().strip()
            try:
                rank_b = int(pkm2_rank_str) if pkm2_rank_str else 0
            except ValueError:
                rank_b = 0
            rank_b = min(max(rank_b, -6), 6)

            weather = self.weather_combo.get().strip()
            if weather == "" or not weather:
                weather = None

            # 스탯 계산 (인덱스 5가 스피드)
            pkm1_stats, _ = get_pokemon_stats(pkm1_name, pkm1_nature, [0, 0, 0, 0, 0, pkm1_sp_val])
            pkm2_stats, _ = get_pokemon_stats(pkm2_name, pkm2_nature, [0, 0, 0, 0, 0, pkm2_sp_val])

            base_speed_a = pkm1_stats[5]
            base_speed_b = pkm2_stats[5]

            # BattleCalculator의 calculate_speed 메서드 연동을 위한 더미 객체 생성
            attacker = DummyObject(name=pkm1_name, item=pkm1_item, ability=pkm1_ability, stats=pkm1_stats, types=self._get_types_from_cache(pkm1_name))
            defender = DummyObject(name=pkm2_name, item=pkm2_item, ability=pkm2_ability, stats=pkm2_stats, types=self._get_types_from_cache(pkm2_name))

            calc = BattleCalculator(attacker, defender, None)
            final_speed_a, final_speed_b = calc.calculate_speed(rank_a, rank_b, item_a=pkm1_item, item_b=pkm2_item, weather=weather)

            rank_a_display = f"{rank_a:+d}" if rank_a != 0 else "0"
            rank_b_display = f"{rank_b:+d}" if rank_b != 0 else "0"

            result_text = f"===== [실시간 스피드 비교 분석] =====\n"
            result_text += f"날씨 환경: {weather if weather else '없음'}\n\n"
            
            result_text += f"🔹 포켓몬 A: {pkm1_name if pkm1_name else '(미입력)'}\n"
            result_text += f" • 기본 실수치: {base_speed_a} (랭크: {rank_a_display})\n"
            result_text += f" • 최종 실수치: {final_speed_a}\n"
            result_text += f" • 특성/아이템: 특성 [{pkm1_ability or '없음'}], 지닌물건 [{pkm1_item or '없음'}]\n\n"

            result_text += f"🔹 포켓몬 B: {pkm2_name if pkm2_name else '(미입력)'}\n"
            result_text += f" • 기본 실수치: {base_speed_b} (랭크: {rank_b_display})\n"
            result_text += f" • 최종 실수치: {final_speed_b}\n"
            result_text += f" • 특성/아이템: 특성 [{pkm2_ability or '없음'}], 지닌물건 [{pkm2_item or '없음'}]\n\n"

            result_text += f"🏆 선공권 판정:\n"
            if final_speed_a > final_speed_b:
                result_text += f" ⚡ {pkm1_name or '포켓몬 A'}가 더 빠릅니다! (속도 차이: +{final_speed_a - final_speed_b})\n"
            elif final_speed_b > final_speed_a:
                result_text += f" ⚡ {pkm2_name or '포켓몬 B'}가 더 빠릅니다! (속도 차이: +{final_speed_b - final_speed_a})\n"
            else:
                result_text += f" 🤝 두 포켓몬의 스피드 실수치가 같습니다! (동속 난수)\n"

            self.result_textbox.configure(state="normal")
            self.result_textbox.delete("0.1", "end")
            self.result_textbox.insert("0.1", result_text)
            self.result_textbox.configure(state="disabled")

        except Exception as e:
            err_msg = f"⏳ [입력 대기 중] 올바른 포켓몬 이름과 수치를 입력해주세요.\n(세부 오류: {str(e)})"
            self.result_textbox.configure(state="normal")
            self.result_textbox.delete("0.1", "end")
            self.result_textbox.insert("0.1", err_msg)
            self.result_textbox.configure(state="disabled")

    def _get_types_from_cache(self, pokemon_name):
        pokedex_cache = GameDataCache.get_pokedex()
        pkm_data = pokedex_cache.get(pokemon_name)
        if pkm_data and "types" in pkm_data:
            return pkm_data["types"]
        return ["노말"]
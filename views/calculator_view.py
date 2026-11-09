import os
import customtkinter as ctk
import tkinter as tk
import threading

from calculator.PBTcalculator import BattleCalculator, DMGoutput_Bulk_Calculator
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
            font=(FONT_FAMILY, 9),
            bg="#0C1C2C",
            fg="#FFFFFF",
            selectbackground="#C74002",
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


class CalculatorView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.pack(fill="both", expand=True)

        self.nature_list = list(nature_chart.keys())
        self._is_initialized = False

        self.grid_columnconfigure(0, weight=0, minsize=260)  # 왼쪽 패널 최소 가로크기 확보 (잘림 방지)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 휠 스크롤 패널 적용 및 가로 크기 넉넉하게 확장
        self.left_frame = ctk.CTkScrollableFrame(self, fg_color="#F0F9FF", corner_radius=8, border_width=1.5, border_color="#000000", width=260)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(5, 3), pady=5)

        self.right_frame = ctk.CTkFrame(self, fg_color="#F0F9FF", corner_radius=8, border_width=1.5, border_color="#000000")
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(3, 5), pady=5)

        title_label = ctk.CTkLabel(self.left_frame, text="배틀 계산기", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"))
        title_label.pack(anchor="w", padx=12, pady=(8, 4))

        input_container = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        input_container.pack(fill="both", expand=False, padx=12, pady=2)

        # ---------------- 1. 공격자 설정 ----------------
        atk_label = ctk.CTkLabel(input_container, text="[공격자 설정]", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=12))
        atk_label.pack(anchor="w", pady=(1, 1))
        
        self.atk_name_combo = self._create_autocomplete_row(input_container, "포켓몬:", [], command=lambda x: self.run_calculation())
        
        self.move_cat_var = ctk.StringVar(value="물리")
        self.atk_sp_label_var = ctk.StringVar(value="공격 [SP] :")
        self.def_sp_stat_label_var = ctk.StringVar(value="방어 [SP] :")

        self.move_name_combo = self._create_move_row(input_container, "기술/위력:", [], self.on_move_changed)
        
        self.atk_nature_combo = self._create_combo_row(input_container, "성격:", self.nature_list, command=lambda x: self.run_calculation())
        self.atk_nature_combo.set("고집" if "고집" in self.nature_list else self.nature_list[0])
        
        self.atk_item_entry = self._create_input_row(input_container, "지닌물건:", "", command=lambda e: self.run_calculation())
        self.atk_ability_entry = self._create_input_row(input_container, "특성:", "", command=lambda e: self.run_calculation())
        
        self.atk_status_combo = self._create_combo_row(
            input_container, "상태이상:", ["", "화상", "마비", "얼음", "독", "맹독", "수면"], 
            command=lambda x: self.run_calculation()
        )
        self.atk_status_combo.set("")

        self.atk_sp_entry, self.atk_rank_entry = self._create_sp_with_rank_row(
            input_container, self.atk_sp_label_var, "32", "0", command=lambda e: self.run_calculation()
        )

        # ---------------- 2. 방어자 설정 ----------------
        def_label = ctk.CTkLabel(input_container, text="[방어자 설정]", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=12))
        def_label.pack(anchor="w", pady=(6, 1))

        self.def_name_combo = self._create_autocomplete_row(input_container, "포켓몬:", [], command=lambda x: self.run_calculation())
        
        self.def_nature_combo = self._create_combo_row(input_container, "성격:", self.nature_list, command=lambda x: self.run_calculation())
        self.def_nature_combo.set("대담" if "대담" in self.nature_list else self.nature_list[0])

        self.def_item_entry = self._create_input_row(input_container, "지닌물건:", "", command=lambda e: self.run_calculation())
        self.def_ability_entry = self._create_input_row(input_container, "특성:", "", command=lambda e: self.run_calculation())
        
        self.def_status_combo = self._create_combo_row(
            input_container, "상태이상:", ["", "화상", "마비", "얼음", "독", "맹독", "수면"], 
            command=lambda x: self.run_calculation()
        )
        self.def_status_combo.set("")

        self.def_sp_h_entry = self._create_input_row(input_container, "체력 [SP] :", "32", command=lambda e: self.run_calculation())
        
        self.def_sp_stat_entry, self.def_rank_entry = self._create_sp_with_rank_row(
            input_container, self.def_sp_stat_label_var, "32", "0", command=lambda e: self.run_calculation()
        )

        # ---------------- 3. 필드 / 환경 설정 (맨 아래로 이동) ----------------
        env_label = ctk.CTkLabel(input_container, text="[필드 / 환경 설정]", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=12))
        env_label.pack(anchor="w", pady=(6, 1))

        self.weather_combo = self._create_combo_row(
            input_container, "날씨:", ["", "쾌청", "비", "눈", "모래바람"], 
            command=lambda x: self.run_calculation()
        )
        self.weather_combo.set("")

        self.field_combo = self._create_combo_row(
            input_container, "필드:", ["", "일레트릭필드", "그래스필드", "사이코필드", "미스트필드"], 
            command=lambda x: self.run_calculation()
        )
        self.field_combo.set("")

        # 급소 여부: 체크박스 형태 및 헤더 라벨 정렬 맞춤
        crit_frame = ctk.CTkFrame(input_container, fg_color="transparent")
        crit_frame.pack(fill="x", pady=1)
        
        crit_lbl = ctk.CTkLabel(crit_frame, text="급소 여부:", width=80, anchor="w", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        crit_lbl.pack(side="left")
        
        self.crit_var = ctk.BooleanVar(value=False)
        self.crit_checkbox = ctk.CTkCheckBox(
            crit_frame, text="적용", variable=self.crit_var, 
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            command=self.run_calculation,
            corner_radius=4, height=20, width=20
        )
        self.crit_checkbox.pack(side="left", padx=2)

        # ---------------- 결과 표시 영역 ----------------
        res_title_label = ctk.CTkLabel(self.right_frame, text="📊 계산 결과", font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"))
        res_title_label.pack(anchor="w", padx=15, pady=(15, 10))

        self.result_textbox = ctk.CTkTextbox(self.right_frame, fg_color="#FFFFFF", text_color="#1E293B", corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=13))
        self.result_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        self.result_textbox.configure(state="normal")
        self.result_textbox.delete("0.1", "end")
        self.result_textbox.insert("0.1", "⏳ [시스템] 캐시 초기화 중입니다... 잠시만 기다려주세요.")
        self.result_textbox.configure(state="disabled")

        self.after(100, lambda: threading.Thread(target=self._load_cache_background, daemon=True).start())

    def _load_cache_background(self):
        try:
            pokedex_cache = GameDataCache.get_pokedex()
            self.pokemon_list = list(pokedex_cache.keys())
            if not self.pokemon_list:
                self.pokemon_list = ["파오젠", "랜드로스", "우라오스"]

            self.move_dict = GameDataCache.get_move_dict()
            self.move_list = list(self.move_dict.keys())
            if not self.move_list:
                self.move_list = ["고드름떨구기", "지진", "인파이트"]

            self.after(0, self._on_cache_loaded)
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda: self._on_cache_error(err_msg))

    def _on_cache_loaded(self):
        self.atk_name_combo.update_values(self.pokemon_list)
        self.def_name_combo.update_values(self.pokemon_list)
        self.move_name_combo_widget.update_values(self.move_list)

        self.atk_name_combo.set("")
        self.def_name_combo.set("")
        self.move_name_combo_widget.set("")
        self.on_move_changed("")

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
        entry = ctk.CTkEntry(frame, width=140, height=20, font=ctk.CTkFont(family=FONT_FAMILY, size=11))
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

        sp_entry = ctk.CTkEntry(right_sub_frame, width=40, height=19, font=ctk.CTkFont(family=FONT_FAMILY, size=11), justify="center")
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

        rank_entry = ctk.CTkEntry(right_sub_frame, width=30, height=19, font=ctk.CTkFont(family=FONT_FAMILY, size=11), justify="center")
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
        combo = ctk.CTkComboBox(frame, values=values, width=140, height=20, font=ctk.CTkFont(family=FONT_FAMILY, size=11), command=command)
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
        ac_box.entry.configure(width=140, height=20)
        ac_box.pack(side="left")
        if values:
            ac_box.set(values[0])
        return ac_box

    def _create_move_row(self, parent, label_text, values, command=None):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=1)
        
        lbl = ctk.CTkLabel(frame, text=label_text, width=80, anchor="w", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        lbl.pack(side="left")

        right_sub_frame = ctk.CTkFrame(frame, fg_color="transparent")
        right_sub_frame.pack(side="left", fill="none")

        self.move_name_combo_widget = AutocompleteCombobox(right_sub_frame, values=values, command=command)
        self.move_name_combo_widget.entry.configure(width=72, height=20)
        self.move_name_combo_widget.pack(side="left", padx=(0, 2))

        self.move_power_entry = ctk.CTkEntry(right_sub_frame, width=32, height=20, font=ctk.CTkFont(family=FONT_FAMILY, size=11), justify="center")
        self.move_power_entry.pack(side="left", padx=(0, 2))
        self.move_power_entry.insert(0, "85")
        self.move_power_entry.bind("<Return>", lambda e: e.widget.tk_focusNext().focus())
        self.move_power_entry.bind("<KeyRelease>", lambda e: self.run_calculation())

        self.move_type_entry = ctk.CTkEntry(right_sub_frame, width=34, height=20, font=ctk.CTkFont(family=FONT_FAMILY, size=11), justify="center")
        self.move_type_entry.pack(side="left")
        self.move_type_entry.insert(0, "노말")
        self.move_type_entry.bind("<Return>", lambda e: e.widget.tk_focusNext().focus())
        self.move_type_entry.bind("<KeyRelease>", lambda e: self.run_calculation())

        if values:
            self.move_name_combo_widget.set(values[0])
        return self.move_name_combo_widget

    def on_move_changed(self, choice=None):
        move_name = (choice if choice else (self.move_name_combo_widget.get() if hasattr(self, "move_name_combo_widget") else "")).strip()
        if not hasattr(self, "move_dict") or not self.move_dict:
            return
        move_obj = self.move_dict.get(move_name)

        if move_obj:
            self.move_power_entry.delete(0, "end")
            self.move_power_entry.insert(0, str(move_obj.get("power", 0)))

            self.move_type_entry.delete(0, "end")
            self.move_type_entry.insert(0, str(move_obj.get("type", "노말")))

            cat = move_obj.get("category", "물리")
            self.move_cat_var.set(cat)

            self.atk_sp_label_var.set("공격 [SP] :")
            self.def_sp_stat_label_var.set("방어 [SP] :")

        self.run_calculation()

    def run_calculation(self):
        if not getattr(self, "_is_initialized", False):
            return

        try:
            cat = self.move_cat_var.get()
            if cat == "변화":
                self.result_textbox.configure(state="normal")
                self.result_textbox.delete("0.1", "end")
                self.result_textbox.insert("0.1", "⚠️ 변화 기술은 데미지 계산을 지원하지 않습니다.")
                self.result_textbox.configure(state="disabled")
                return

            atk_name = self.atk_name_combo.get().strip()
            atk_nature = self.atk_nature_combo.get().strip()
            atk_val_str = self.atk_sp_entry.get().strip()
            atk_sp_val = min(max(int(atk_val_str) if atk_val_str.isdigit() else 0, 0), 32)
            
            atk_rank_str = self.atk_rank_entry.get().strip()
            try:
                rank_a = int(atk_rank_str) if atk_rank_str else 0
            except ValueError:
                rank_a = 0
            rank_a = min(max(rank_a, -6), 6)

            atk_SPs = [0, 0, 0, 0, 0, 0]
            if cat == "특수":
                atk_SPs[3] = atk_sp_val
            else:
                atk_SPs[1] = atk_sp_val

            atk_stats, _ = get_pokemon_stats(atk_name, atk_nature, atk_SPs)
            atk_stat = atk_stats[3] if cat == "특수" else atk_stats[1]

            def_name = self.def_name_combo.get().strip()
            def_nature = self.def_nature_combo.get().strip()
            
            h_str = self.def_sp_h_entry.get().strip()
            h_sp = min(max(int(h_str) if h_str.isdigit() else 0, 0), 32)

            stat_str = self.def_sp_stat_entry.get().strip()
            stat_sp = min(max(int(stat_str) if stat_str.isdigit() else 0, 0), 32)

            def_rank_str = self.def_rank_entry.get().strip()
            try:
                rank_b = int(def_rank_str) if def_rank_str else 0
            except ValueError:
                rank_b = 0
            rank_b = min(max(rank_b, -6), 6)

            def_SPs = [0, 0, 0, 0, 0, 0]
            def_SPs[0] = h_sp
            if cat == "특수":
                def_SPs[4] = stat_sp
            else:
                def_SPs[2] = stat_sp

            def_stats, _ = get_pokemon_stats(def_name, def_nature, def_SPs)
            def_hp, def_b, def_d = def_stats[0], def_stats[2], def_stats[4]
            def_stat = def_d if cat == "특수" else def_b

            atk_item = self.atk_item_entry.get().strip()
            atk_ability = self.atk_ability_entry.get().strip()
            def_item = self.def_item_entry.get().strip()
            def_ability = self.def_ability_entry.get().strip()

            move_name = self.move_name_combo_widget.get().strip()
            
            power_str = self.move_power_entry.get().strip()
            move_power = int(power_str) if power_str.isdigit() else 85

            move_type = self.move_type_entry.get().strip()
            
            weather = self.weather_combo.get().strip()
            if weather == "" or not weather: 
                weather = None

            atk_status = self.atk_status_combo.get().strip()
            if atk_status == "" or not atk_status:
                atk_status = None

            def_status = self.def_status_combo.get().strip()
            if def_status == "" or not def_status:
                def_status = None

            status = [atk_status, def_status]

            field = self.field_combo.get().strip()
            if field == "" or not field: 
                field = None

            crit = self.crit_var.get()

            atk_types = self._get_types_from_cache(atk_name)
            def_types = self._get_types_from_cache(def_name)

            move_obj_data = self.move_dict.get(move_name, {})
            contact_val = True if move_obj_data.get("contact") == "o" else False

            attacker = DummyObject(
                name=atk_name, item=atk_item, ability=atk_ability, types=atk_types, hp_percent=100
            )
            defender = DummyObject(
                name=def_name, item=def_item, ability=def_ability, types=def_types, hp_percent=100
            )
            move = DummyObject(
                name=move_name, power=move_power, type=move_type, category=cat, contact=contact_val
            )

            calc = BattleCalculator(attacker, defender, move)
            damages, percentages = calc.calculate_damage(
                atk_stat, def_stat, def_hp, rank_a=rank_a, rank_b=rank_b, 
                weather=weather, field=field, critical=crit, status=status
            )

            dmg_output_calc = DMGoutput_Bulk_Calculator(attacker)
            dmg_output = dmg_output_calc.calculate_dmg_output(atk_stat, move, field, weather, atk_status)

            bulk_calc = DMGoutput_Bulk_Calculator(defender)
            phys_bulk, spec_bulk = bulk_calc.calculate_bulk(def_hp, def_b, def_d, weather, def_status)

            min_dmg, max_dmg = damages[0], damages[-1]
            min_pct, max_pct = percentages[0], percentages[-1]

            rank_a_display = f"{rank_a:+d}" if rank_a != 0 else "0"
            rank_b_display = f"{rank_b:+d}" if rank_b != 0 else "0"

            if cat == "물리":
                cat_text_b = "방어[B]"
                cat_text_a = "공격[A]"
            elif cat == "특수":
                cat_text_b = "특방[D]"
                cat_text_a = "특공[C]"

            result_text = f"===== [실시간 배틀 데미지 및 내구 분석] =====\n"
            result_text += f"공격자: {atk_name} (실수치 {cat_text_a}: {atk_stat} / 랭크: {rank_a_display})\n"
            result_text += f"방어자: {def_name} (실수치 체력[HP]: {def_hp} / {cat_text_b}: {def_stat} / 랭크: {rank_b_display})\n"
            result_text += f"사용 기술: {move_name} ({cat} / 위력: {move_power} / 타입: {move_type})\n"
            result_text += f"적용 날씨: {weather if weather else '없음'} / 급소: {'O' if crit else 'X'}\n\n"
            
            result_text += f"🎯 데미지 범위:\n"
            result_text += f" • 최저 데미지: {min_dmg} ({min_pct}%)\n"
            result_text += f" • 최대 데미지: {max_dmg} ({max_pct}%)\n"
            result_text += f" • 결정력: {dmg_output}\n\n"

            result_text += f"📈 85%~100% 난수표 (데미지 / 퍼센트):\n"
            for i, (d, p) in enumerate(zip(damages, percentages)):
                result_text += f" {d} ({p}%)\t"
                if (i + 1) % 4 == 0:
                    result_text += "\n"

            result_text += f"\n\n🛡️ [방어자 내구 분석]\n"
            result_text += f" • 물리 내구치: {phys_bulk}\n"
            result_text += f" • 특수 내구치: {spec_bulk}\n"

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

        # except Exception as e:
        #     import traceback
        #     error_traceback = traceback.format_exc()
        #     err_msg = (
        #         f"❌ [에러 발생]\n{error_traceback}"  # 상세한 줄 번호 포함
        #     )

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
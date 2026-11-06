import os
import sys
import customtkinter as ctk
import threading

from stat_optimizer import PokemonStatOptimizer
from pokeCSVbuilder import SampleCSVbuilder
from loader.data_loader import PokemonCSVLoader
from .utils.cache_manager import GameDataCache

DATA_DIR = os.path.join(os.path.expanduser("~"), "PokemonDATA", "data")
SAMPLES_DIR = os.path.join(DATA_DIR, "samples")
FONT_FAMILY = "Malgun Gothic"

class StdoutRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, str_val):
        if not str_val:
            return
        try:
            self.text_widget.configure(state="normal")
            self.text_widget.insert("end", str_val)
            self.text_widget.see("end")
            self.text_widget.configure(state="disabled")
        except Exception:
            pass

    def flush(self):
        pass


class OptimizerView:
    def __init__(self, parent_tab):
        self.tab = parent_tab
        self.sample_files = self._get_sample_file_list()
        self.move_list = []

        self.power_selected_moves = []
        self.bulk_selected_moves = []

        self.latest_optimized_sp = {"H": 0, "A": 0, "B": 0, "C": 0, "D": 0, "S": 0}

        self.optimization_choices = []
        self.raw_optimization_options = []

        self.create_widgets()
        
        sys.stdout = StdoutRedirector(self.result_box)
        self._init_default_choices()
        print("[시스템] 준비 완료. 샘플 파일을 선택하고 최적화를 실행하세요.")
        threading.Thread(target=self._load_cache_background, daemon=True).start()

    def _get_sample_file_list(self):
        try:
            if not os.path.exists(SAMPLES_DIR):
                os.makedirs(SAMPLES_DIR, exist_ok=True)
            files = [f[:-4] for f in os.listdir(SAMPLES_DIR) if f.endswith('.csv')]
            return files if files else ["기본샘플"]
        except Exception:
            return ["기본샘플"]

    def refresh_samples(self):
        self.sample_files = self._get_sample_file_list()
        combo_attrs = ['speed_pkm1', 'speed_pkm2', 'power_pkm1', 'power_pkm2', 'bulk_pkm1', 'bulk_pkm2', 'regen_target_combo']
        for attr in combo_attrs:
            if hasattr(self, attr):
                widget = getattr(self, attr)
                if isinstance(widget, ctk.CTkComboBox):
                    current_val = widget.get()
                    widget.configure(values=self.sample_files)
                    if current_val in self.sample_files:
                        widget.set(current_val)
                    elif self.sample_files:
                        widget.set(self.sample_files[0])
        print("[시스템] 샘플 목록이 새로고침 되었습니다.")

    def _load_cache_background(self):
        try:
            move_names = GameDataCache.get_move_names()
            self.tab.after(0, lambda: self._on_cache_loaded(move_names))
        except Exception as e:
            print(f"캐시 로드 오류: {e}")

    def _on_cache_loaded(self, move_names):
        self.move_list = move_names or []
        self.refresh_samples()

        if hasattr(self, '_update_power_moves'):
            self._update_power_moves()
        if hasattr(self, '_update_bulk_moves'):
            self._update_bulk_moves()

        print("[시스템] 샘플 파일 및 데이터 캐시 로드가 완료되었습니다.")

    def create_widgets(self):
        main_card = ctk.CTkFrame(self.tab, fg_color="#DAF6FE", corner_radius=12, border_width=2, border_color="#000000")
        main_card.pack(fill="both", expand=True, padx=8, pady=4)

        title_ribbon = ctk.CTkFrame(main_card, fg_color="#FFFFFF", corner_radius=8, border_width=1.5, border_color="#000000", height=30)
        title_ribbon.pack(anchor="w", padx=12, pady=(8, 4))
        ctk.CTkLabel(title_ribbon, text="포켓몬 스탯 최적화 툴", text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack(side="left", padx=10, pady=2)

        split_container = ctk.CTkFrame(main_card, fg_color="transparent")
        split_container.pack(fill="both", expand=True, padx=8, pady=4)

        left_frame = ctk.CTkFrame(split_container, fg_color="#E6F7FF", corner_radius=10, border_width=1.5, border_color="#000000", width=310)
        left_frame.pack_propagate(False)
        left_frame.pack(side="left", fill="y", expand=False, padx=(0, 4), pady=2)

        self.opt_tabs = ctk.CTkTabview(left_frame, fg_color="transparent", segmented_button_fg_color="#DBF4FF", segmented_button_selected_color="#ef4444", segmented_button_selected_hover_color="#dc2626")
        self.opt_tabs._segmented_button.configure(font=(FONT_FAMILY, 12, "bold"))
        self.opt_tabs.pack(fill="both", expand=True, padx=6, pady=6)

        tab_speed = self.opt_tabs.add("속도 최적화")
        tab_power = self.opt_tabs.add("결정력 최적화")
        tab_bulk = self.opt_tabs.add("내구 최적화")

        self.setup_speed_tab(tab_speed)
        self.setup_power_tab(tab_power)
        self.setup_bulk_tab(tab_bulk)

        right_frame = ctk.CTkFrame(split_container, fg_color="#E6F7FF", corner_radius=10, border_width=1.5, border_color="#000000")
        right_frame.pack(side="right", fill="both", expand=True, padx=(4, 0), pady=2)

        ctk.CTkLabel(right_frame, text="[최적화 결과 리포트]", text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))
        
        self.result_box = ctk.CTkTextbox(
            right_frame, fg_color="#ffffff", text_color="#000000", corner_radius=8, 
            border_width=1, border_color="#000000", font=(FONT_FAMILY, 11)
        )
        self.result_box.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        regen_frame = ctk.CTkFrame(right_frame, fg_color="#D1E9FF", corner_radius=8, border_width=1, border_color="#000000")
        regen_frame.pack(fill="x", padx=8, pady=(0, 8))

        ctk.CTkLabel(regen_frame, text="스탯 포인트(SP) 설정 및 샘플 재생성", text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold")).pack(anchor="w", padx=8, pady=(4, 2))

        select_grid = ctk.CTkFrame(regen_frame, fg_color="transparent")
        select_grid.pack(fill="x", padx=8, pady=2)
        select_grid.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(select_grid, text="최적화 결과 선택:", text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=10)).grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
        self.result_select_combo = ctk.CTkComboBox(select_grid, values=["무보정 (SP = 0)", "남은 스탯 전부 투자"], height=24, fg_color="#FFFFFF", border_color="#000000", border_width=1, text_color="#000000", command=self.on_result_option_selected, font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.result_select_combo.grid(row=0, column=1, sticky="ew", pady=2)

        manual_sp_grid = ctk.CTkFrame(regen_frame, fg_color="transparent")
        manual_sp_grid.pack(fill="x", padx=8, pady=2)
        
        sp_labels = ["H", "A", "B", "C", "D", "S"]
        self.manual_sp_entries = {}
        
        for i, stat in enumerate(sp_labels):
            manual_sp_grid.grid_columnconfigure(i*2, weight=0)
            manual_sp_grid.grid_columnconfigure(i*2+1, weight=1)
            
            ctk.CTkLabel(manual_sp_grid, text=f"{stat}:", text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold")).grid(row=0, column=i*2, sticky="e", padx=(2, 2), pady=2)
            entry = ctk.CTkEntry(manual_sp_grid, width=32, height=22, fg_color="#FFFFFF", border_color="#000000", border_width=1, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
            entry.grid(row=0, column=i*2+1, sticky="ew", padx=(0, 4), pady=2)
            entry.insert(0, "0")
            self.manual_sp_entries[stat] = entry

        regen_grid = ctk.CTkFrame(regen_frame, fg_color="transparent")
        regen_grid.pack(fill="x", padx=8, pady=2)
        regen_grid.grid_columnconfigure(1, weight=1)
        regen_grid.grid_columnconfigure(2, weight=0)

        ctk.CTkLabel(regen_grid, text="대상 샘플:", text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=10)).grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
        self.regen_target_combo = ctk.CTkComboBox(regen_grid, values=self.sample_files, height=24, fg_color="#FFFFFF", border_color="#000000", border_width=1, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.regen_target_combo.grid(row=0, column=1, sticky="ew", pady=2)
        if self.sample_files: self.regen_target_combo.set(self.sample_files[0])

        refresh_btn = ctk.CTkButton(regen_grid, text="목록 갱신", width=80, height=24, fg_color="#0284c7", hover_color="#0369a1", text_color="#ffffff", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), command=self.refresh_samples)
        refresh_btn.grid(row=0, column=2, padx=(4, 0), pady=2)

        ctk.CTkLabel(regen_grid, text="저장 파일명:", text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=10)).grid(row=1, column=0, sticky="w", padx=(0, 4), pady=2)
        self.regen_filename_entry = ctk.CTkEntry(regen_grid, height=24, fg_color="#FFFFFF", border_color="#000000", border_width=1, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.regen_filename_entry.grid(row=1, column=1, columnspan=2, sticky="ew", pady=2)
        self.regen_filename_entry.insert(0, "[opt]파일명")

        regen_btn = ctk.CTkButton(regen_frame, text="샘플 재생성/저장", fg_color="#3b82f6", hover_color="#1d4ed8", text_color="#ffffff", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), height=26, command=self.regenerate_sample_file)
        regen_btn.pack(fill="x", padx=8, pady=(2, 8))

    def _init_default_choices(self):
        self.optimization_choices = ["무보정 (SP = 0)", "남은 스탯 전부 투자"]
        self.raw_optimization_options = [
            {"type": "zero", "SPs": [0, 0, 0, 0, 0, 0]},
            {"type": "max", "SPs": [32, 32, 32, 32, 32, 32]}
        ]

    def setup_speed_tab(self, parent):
        scroll_f = ctk.CTkScrollableFrame(parent, fg_color="transparent", width=280, height=400)
        scroll_f.pack(fill="both", expand=True, padx=2, pady=2)
        scroll_f.grid_columnconfigure(1, weight=1)

        refresh_btn = ctk.CTkButton(scroll_f, text="샘플 목록 갱신", fg_color="#0284c7", hover_color="#0369a1", text_color="#ffffff", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), height=26, command=self.refresh_samples)
        refresh_btn.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6), padx=2)

        ctk.CTkLabel(scroll_f, text="내 샘플 파일:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=1, column=0, sticky="w", pady=4, padx=(2, 8))
        self.speed_pkm1 = ctk.CTkComboBox(scroll_f, values=self.sample_files, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.speed_pkm1.grid(row=1, column=1, sticky="ew", pady=4)
        if self.sample_files: self.speed_pkm1.set(self.sample_files[0])

        ctk.CTkLabel(scroll_f, text="상대 샘플 파일:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=2, column=0, sticky="w", pady=4, padx=(2, 8))
        self.speed_pkm2 = ctk.CTkComboBox(scroll_f, values=self.sample_files, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.speed_pkm2.grid(row=2, column=1, sticky="ew", pady=4)
        if self.sample_files: self.speed_pkm2.set(self.sample_files[0])

        ctk.CTkLabel(scroll_f, text="사용 가능 SP:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=3, column=0, sticky="w", pady=4, padx=(2, 8))
        self.speed_sp_av = ctk.CTkEntry(scroll_f, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.speed_sp_av.grid(row=3, column=1, sticky="ew", pady=4)
        self.speed_sp_av.insert(0, "32")

        ctk.CTkLabel(scroll_f, text="성격 보정:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=4, column=0, sticky="w", pady=4, padx=(2, 8))
        self.speed_nature = ctk.CTkComboBox(scroll_f, values=["1.1", "1.0", "0.9"], width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.speed_nature.grid(row=4, column=1, sticky="ew", pady=4)
        self.speed_nature.set("1.0")

        ctk.CTkLabel(scroll_f, text="스피드 랭크:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=5, column=0, sticky="w", pady=4, padx=(2, 8))
        self.speed_rank = ctk.CTkEntry(scroll_f, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.speed_rank.grid(row=5, column=1, sticky="ew", pady=4)
        self.speed_rank.insert(0, "0")

        ctk.CTkLabel(scroll_f, text="아이템 보정:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=6, column=0, sticky="w", pady=4, padx=(2, 8))
        self.speed_item = ctk.CTkComboBox(scroll_f, values=["0", "1 (스카프 등 1.5배)"], width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.speed_item.grid(row=6, column=1, sticky="ew", pady=4)
        self.speed_item.set("0")

        btn = ctk.CTkButton(scroll_f, text="속도 최적화 실행", fg_color="#ef4444", hover_color="#dc2626", text_color="#ffffff", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=11), height=32, command=self.run_speed_optimization)
        btn.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(15, 5), padx=2)

    def setup_power_tab(self, parent):
        scroll_f = ctk.CTkScrollableFrame(parent, fg_color="transparent", width=280, height=400)
        scroll_f.pack(fill="both", expand=True, padx=2, pady=2)
        scroll_f.grid_columnconfigure(1, weight=1)

        refresh_btn = ctk.CTkButton(scroll_f, text="샘플 목록 갱신", fg_color="#0284c7", hover_color="#0369a1", text_color="#ffffff", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), height=26, command=self.refresh_samples)
        refresh_btn.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6), padx=2)

        ctk.CTkLabel(scroll_f, text="내 샘플 파일:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=1, column=0, sticky="w", pady=3, padx=(2, 8))
        self.power_pkm1 = ctk.CTkComboBox(scroll_f, values=self.sample_files, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", command=lambda x: self._update_power_moves(), font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.power_pkm1.grid(row=1, column=1, sticky="ew", pady=3)
        if self.sample_files: self.power_pkm1.set(self.sample_files[0])

        ctk.CTkLabel(scroll_f, text="상대 샘플 파일:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=2, column=0, sticky="w", pady=3, padx=(2, 8))
        self.power_pkm2 = ctk.CTkComboBox(scroll_f, values=self.sample_files, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.power_pkm2.grid(row=2, column=1, sticky="ew", pady=3)
        if self.sample_files: self.power_pkm2.set(self.sample_files[0])

        ctk.CTkLabel(scroll_f, text="기술 선택:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=3, column=0, sticky="w", pady=3, padx=(2, 8))
        
        power_move_frame = ctk.CTkFrame(scroll_f, fg_color="transparent")
        power_move_frame.grid(row=3, column=1, sticky="ew", pady=3)
        power_move_frame.grid_columnconfigure(0, weight=1)

        self.power_move_input = ctk.CTkComboBox(power_move_frame, values=["기술을 선택하세요"], width=100, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.power_move_input.pack(side="left", fill="x", expand=True, padx=(0, 2))

        add_power_btn = ctk.CTkButton(power_move_frame, text="추가", width=40, height=26, fg_color="#3b82f6", hover_color="#1d4ed8", text_color="#ffffff", command=self.add_power_skill, font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        add_power_btn.pack(side="right")

        ctk.CTkLabel(scroll_f, text="선택된 기술:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=4, column=0, sticky="nw", pady=3, padx=(2, 8))
        
        self.power_tags_container = ctk.CTkScrollableFrame(scroll_f, orientation="horizontal", fg_color="#FFFFFF", border_width=1, border_color="#000000", corner_radius=6, height=50)
        self.power_tags_container.grid(row=4, column=1, sticky="ew", pady=3)
        
        self.power_tags_frame = ctk.CTkFrame(self.power_tags_container, fg_color="transparent")
        self.power_tags_frame.pack(side="left", anchor="w")

        ctk.CTkLabel(scroll_f, text="공격 성격 보정:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=5, column=0, sticky="w", pady=3, padx=(2, 8))
        self.power_nature = ctk.CTkComboBox(scroll_f, values=["1.1", "1.0", "0.9"], width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.power_nature.grid(row=5, column=1, sticky="ew", pady=3)
        self.power_nature.set("1.0")

        ctk.CTkLabel(scroll_f, text="공격 랭크:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=6, column=0, sticky="w", pady=3, padx=(2, 8))
        self.power_rank_a = ctk.CTkEntry(scroll_f, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.power_rank_a.grid(row=6, column=1, sticky="ew", pady=3)
        self.power_rank_a.insert(0, "0")

        ctk.CTkLabel(scroll_f, text="상대 방어 랭크:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=7, column=0, sticky="w", pady=3, padx=(2, 8))
        self.power_rank_b = ctk.CTkEntry(scroll_f, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.power_rank_b.grid(row=7, column=1, sticky="ew", pady=3)
        self.power_rank_b.insert(0, "0")

        ctk.CTkLabel(scroll_f, text="상대 현재 체력(%):", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=8, column=0, sticky="w", pady=3, padx=(2, 8))
        self.power_current_hp = ctk.CTkEntry(scroll_f, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.power_current_hp.grid(row=8, column=1, sticky="ew", pady=3)
        self.power_current_hp.insert(0, "100")

        ctk.CTkLabel(scroll_f, text="타수 (다중 공격시 1):", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color="#000000").grid(row=9, column=0, sticky="w", pady=3, padx=(2, 8))
        self.power_hits = ctk.CTkEntry(scroll_f, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.power_hits.grid(row=9, column=1, sticky="ew", pady=3)
        self.power_hits.insert(0, "1")

        ctk.CTkLabel(scroll_f, text="목표 기절 확률(%):", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=10, column=0, sticky="w", pady=3, padx=(2, 8))
        self.power_target_prob = ctk.CTkEntry(scroll_f, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.power_target_prob.grid(row=10, column=1, sticky="ew", pady=3)
        self.power_target_prob.insert(0, "100")

        ctk.CTkLabel(scroll_f, text="날씨:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=11, column=0, sticky="w", pady=3, padx=(2, 8))
        self.power_weather = ctk.CTkComboBox(scroll_f, values=["", "쾌청", "비", "눈", "모래바람"], width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.power_weather.grid(row=11, column=1, sticky="ew", pady=3)
        self.power_weather.set("")

        ctk.CTkLabel(scroll_f, text="필드:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=12, column=0, sticky="w", pady=3, padx=(2, 8))
        self.power_field = ctk.CTkComboBox(scroll_f, values=["", "일레트릭필드", "그래스필드", "사이코필드", "미스트필드"], width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.power_field.grid(row=12, column=1, sticky="ew", pady=3)
        self.power_field.set("")

        ctk.CTkLabel(scroll_f, text="사용 가능 SP:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=13, column=0, sticky="w", pady=3, padx=(2, 8))
        self.power_sp_av = ctk.CTkEntry(scroll_f, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.power_sp_av.grid(row=13, column=1, sticky="ew", pady=3)
        self.power_sp_av.insert(0, "32")

        ctk.CTkLabel(scroll_f, text="급소 여부:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=14, column=0, sticky="w", pady=3, padx=(2, 8))
        self.power_crit_var = ctk.BooleanVar(value=False)
        self.power_crit_chk = ctk.CTkCheckBox(scroll_f, text="급소", variable=self.power_crit_var, fg_color="#ef4444", hover_color="#dc2626", text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.power_crit_chk.grid(row=14, column=1, sticky="w", pady=3)

        btn = ctk.CTkButton(scroll_f, text="결정력 최적화 실행", fg_color="#ef4444", hover_color="#dc2626", text_color="#ffffff", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=11), height=32, command=self.run_power_optimization)
        btn.grid(row=14, column=0, columnspan=2, sticky="ew", pady=(10, 5), padx=2)

    def setup_bulk_tab(self, parent):
        scroll_f = ctk.CTkScrollableFrame(parent, fg_color="transparent", width=280, height=400)
        scroll_f.pack(fill="both", expand=True, padx=2, pady=2)
        scroll_f.grid_columnconfigure(1, weight=1)

        refresh_btn = ctk.CTkButton(scroll_f, text="샘플 목록 갱신", fg_color="#0284c7", hover_color="#0369a1", text_color="#ffffff", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), height=26, command=self.refresh_samples)
        refresh_btn.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6), padx=2)

        ctk.CTkLabel(scroll_f, text="내 샘플 파일:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=1, column=0, sticky="w", pady=3, padx=(2, 8))
        self.bulk_pkm1 = ctk.CTkComboBox(scroll_f, values=self.sample_files, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.bulk_pkm1.grid(row=1, column=1, sticky="ew", pady=3)
        if self.sample_files: self.bulk_pkm1.set(self.sample_files[0])

        ctk.CTkLabel(scroll_f, text="상대 샘플 파일:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=2, column=0, sticky="w", pady=3, padx=(2, 8))
        self.bulk_pkm2 = ctk.CTkComboBox(scroll_f, values=self.sample_files, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", command=lambda x: self._update_bulk_moves(), font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.bulk_pkm2.grid(row=2, column=1, sticky="ew", pady=3)
        if self.sample_files: self.bulk_pkm2.set(self.sample_files[0])

        ctk.CTkLabel(scroll_f, text="상대 기술 선택:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=3, column=0, sticky="w", pady=3, padx=(2, 8))
        
        bulk_move_frame = ctk.CTkFrame(scroll_f, fg_color="transparent")
        bulk_move_frame.grid(row=3, column=1, sticky="ew", pady=3)
        bulk_move_frame.grid_columnconfigure(0, weight=1)

        self.bulk_move_input = ctk.CTkComboBox(bulk_move_frame, values=["기술을 선택하세요"], width=100, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.bulk_move_input.pack(side="left", fill="x", expand=True, padx=(0, 2))

        add_bulk_btn = ctk.CTkButton(bulk_move_frame, text="추가", width=40, height=26, fg_color="#3b82f6", hover_color="#1d4ed8", text_color="#ffffff", command=self.add_bulk_skill, font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        add_bulk_btn.pack(side="right")

        ctk.CTkLabel(scroll_f, text="선택된 상대 기술:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=4, column=0, sticky="nw", pady=3, padx=(2, 8))
        
        self.bulk_tags_container = ctk.CTkScrollableFrame(scroll_f, orientation="horizontal", fg_color="#FFFFFF", border_width=1, border_color="#000000", corner_radius=6, height=50)
        self.bulk_tags_container.grid(row=4, column=1, sticky="ew", pady=3)
        
        self.bulk_tags_frame = ctk.CTkFrame(self.bulk_tags_container, fg_color="transparent")
        self.bulk_tags_frame.pack(side="left", anchor="w")

        ctk.CTkLabel(scroll_f, text="사용 가능 SP:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=5, column=0, sticky="w", pady=3, padx=(2, 8))
        self.bulk_av_sp = ctk.CTkEntry(scroll_f, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.bulk_av_sp.grid(row=5, column=1, sticky="ew", pady=3)
        self.bulk_av_sp.insert(0, "66")

        ctk.CTkLabel(scroll_f, text="방어 성격 보정:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=6, column=0, sticky="w", pady=3, padx=(2, 8))
        self.bulk_nature_b = ctk.CTkComboBox(scroll_f, values=["1.1", "1.0", "0.9"], width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.bulk_nature_b.grid(row=6, column=1, sticky="ew", pady=3)
        self.bulk_nature_b.set("1.0")

        ctk.CTkLabel(scroll_f, text="특방 성격 보정:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=7, column=0, sticky="w", pady=3, padx=(2, 8))
        self.bulk_nature_d = ctk.CTkComboBox(scroll_f, values=["1.1", "1.0", "0.9"], width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.bulk_nature_d.grid(row=7, column=1, sticky="ew", pady=3)
        self.bulk_nature_d.set("1.0")

        ctk.CTkLabel(scroll_f, text="상대 공격 랭크:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=8, column=0, sticky="w", pady=3, padx=(2, 8))
        self.bulk_rank_a = ctk.CTkEntry(scroll_f, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.bulk_rank_a.grid(row=8, column=1, sticky="ew", pady=3)
        self.bulk_rank_a.insert(0, "0")

        ctk.CTkLabel(scroll_f, text="내 방어 랭크:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=9, column=0, sticky="w", pady=3, padx=(2, 8))
        self.bulk_rank_b = ctk.CTkEntry(scroll_f, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.bulk_rank_b.grid(row=9, column=1, sticky="ew", pady=3)
        self.bulk_rank_b.insert(0, "0")

        ctk.CTkLabel(scroll_f, text="남은 체력(%):", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=10, column=0, sticky="w", pady=3, padx=(2, 8))
        self.bulk_target_hp = ctk.CTkEntry(scroll_f, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.bulk_target_hp.grid(row=10, column=1, sticky="ew", pady=3)
        self.bulk_target_hp.insert(0, "0")

        ctk.CTkLabel(scroll_f, text="물리 가중치:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=11, column=0, sticky="w", pady=3, padx=(2, 8))
        self.bulk_w_def = ctk.CTkEntry(scroll_f, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.bulk_w_def.grid(row=11, column=1, sticky="ew", pady=3)
        self.bulk_w_def.insert(0, "0.5")

        ctk.CTkLabel(scroll_f, text="특수 가중치:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=12, column=0, sticky="w", pady=3, padx=(2, 8))
        self.bulk_w_spdef = ctk.CTkEntry(scroll_f, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.bulk_w_spdef.grid(row=12, column=1, sticky="ew", pady=3)
        self.bulk_w_spdef.insert(0, "0.5")

        ctk.CTkLabel(scroll_f, text="타수 (다중 공격시 1):", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color="#000000").grid(row=13, column=0, sticky="w", pady=3, padx=(2, 8))
        self.bulk_hits = ctk.CTkEntry(scroll_f, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.bulk_hits.grid(row=13, column=1, sticky="ew", pady=3)
        self.bulk_hits.insert(0, "1")

        ctk.CTkLabel(scroll_f, text="견딜 확률(%):", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=14, column=0, sticky="w", pady=3, padx=(2, 8))
        self.bulk_tg_prob = ctk.CTkEntry(scroll_f, width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.bulk_tg_prob.grid(row=14, column=1, sticky="ew", pady=3)
        self.bulk_tg_prob.insert(0, "100")

        ctk.CTkLabel(scroll_f, text="날씨:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=15, column=0, sticky="w", pady=3, padx=(2, 8))
        self.bulk_weather = ctk.CTkComboBox(scroll_f, values=["", "쾌청", "비", "눈", "모래바람"], width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.bulk_weather.grid(row=15, column=1, sticky="ew", pady=3)
        self.bulk_weather.set("")

        ctk.CTkLabel(scroll_f, text="필드:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=16, column=0, sticky="w", pady=3, padx=(2, 8))
        self.bulk_field = ctk.CTkComboBox(scroll_f, values=["", "일레트릭필드", "그래스필드", "사이코필드", "미스트필드"], width=145, height=26, fg_color="#DBF4FF", border_color="#000000", border_width=1.5, text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.bulk_field.grid(row=16, column=1, sticky="ew", pady=3)
        self.bulk_field.set("")

        ctk.CTkLabel(scroll_f, text="급소 여부:", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color="#000000").grid(row=17, column=0, sticky="w", pady=3, padx=(2, 8))
        self.bulk_crit_var = ctk.BooleanVar(value=False)
        self.bulk_crit_chk = ctk.CTkCheckBox(scroll_f, text="급소", variable=self.bulk_crit_var, fg_color="#ef4444", hover_color="#dc2626", text_color="#000000", font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.bulk_crit_chk.grid(row=17, column=1, sticky="w", pady=3)

        btn = ctk.CTkButton(scroll_f, text="내구 최적화 실행", fg_color="#ef4444", hover_color="#dc2626", text_color="#ffffff", font=ctk.CTkFont(family=FONT_FAMILY, weight="bold", size=11), height=32, command=self.run_bulk_optimization)
        btn.grid(row=18, column=0, columnspan=2, sticky="ew", pady=(15, 5), padx=2)

    def add_power_skill(self):
        move = self.power_move_input.get().strip()
        if move and move != "기술을 선택하세요":
            self.power_selected_moves.append(move)
            self.refresh_power_tags()

    def remove_power_skill(self, move):
        if move in self.power_selected_moves:
            self.power_selected_moves.remove(move)
            self.refresh_power_tags()

    def refresh_power_tags(self):
        for widget in self.power_tags_frame.winfo_children():
            widget.destroy()
        for move in self.power_selected_moves:
            tag_btn = ctk.CTkButton(
                self.power_tags_frame, text=f"{move} ✕", width=0, height=22,
                fg_color="#DBF4FF", hover_color="#ff9999", text_color="#000000",
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                command=lambda m=move: self.remove_power_skill(m)
            )
            tag_btn.pack(side="left", padx=2, pady=2)

    def add_bulk_skill(self):
        move = self.bulk_move_input.get().strip()
        if move and move != "기술을 선택하세요":
            self.bulk_selected_moves.append(move)
            self.refresh_bulk_tags()

    def remove_bulk_skill(self, move):
        if move in self.bulk_selected_moves:
            self.bulk_selected_moves.remove(move)
            self.refresh_bulk_tags()

    def refresh_bulk_tags(self):
        for widget in self.bulk_tags_frame.winfo_children():
            widget.destroy()
        for move in self.bulk_selected_moves:
            tag_btn = ctk.CTkButton(
                self.bulk_tags_frame, text=f"{move} ✕", width=0, height=22,
                fg_color="#DBF4FF", hover_color="#ff9999", text_color="#000000",
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                command=lambda m=move: self.remove_bulk_skill(m)
            )
            tag_btn.pack(side="left", padx=2, pady=2)

    def _load_sample_csv_data(self, file_path):
        if not file_path.endswith(".csv"):
            file_path += ".csv"
        relative_path = os.path.join("data", "samples", file_path)
        return PokemonCSVLoader.load_pokemon_data(relative_path)

    def _update_power_moves(self):
        p1_samplefile = self.power_pkm1.get().strip()
        p1_data = self._load_sample_csv_data(p1_samplefile)
        moves = p1_data.get("기술", ["10만볼트", "볼트체인지", "방어", "대타출동"])
        self.power_move_input.configure(values=moves)
        if moves:
            self.power_move_input.set(moves[0])

    def _update_bulk_moves(self):
        p2_samplefile = self.bulk_pkm2.get().strip()
        p2_data = self._load_sample_csv_data(p2_samplefile)
        moves = p2_data.get("기술", ["10만볼트", "볼트체인지", "방어", "대타출동"])
        self.bulk_move_input.configure(values=moves)
        if moves:
            self.bulk_move_input.set(moves[0])

    def run_speed_optimization(self):
        try:
            print(f"\n[속도 최적화 실행 중: {self.speed_pkm1.get()} vs {self.speed_pkm2.get()}]")
            p1_samplefile = self.speed_pkm1.get().strip()
            p2_samplefile = self.speed_pkm2.get().strip()
            p1_data = self._load_sample_csv_data(p1_samplefile)
            p2_data = self._load_sample_csv_data(p2_samplefile)

            sp_av = int(self.speed_sp_av.get().strip() or "32")
            nature_s = float(self.speed_nature.get().strip() or "1.1")
            rank = int(self.speed_rank.get().strip() or "0")
            item_val = 1 if "1" in self.speed_item.get() else 0

            optimizer = PokemonStatOptimizer()
            result = optimizer.optimize_speed_advanced(p1_data, p2_data, sp_av, nature_s, rank, item_val)
            
            self.optimization_choices = ["무보정 (SP = 0)", f"남은 스탯 전부 투자 (SP = {sp_av})"]
            self.raw_optimization_options = [
                {"type": "SPs", "SPs": [self.latest_optimized_sp["H"], self.latest_optimized_sp["A"], self.latest_optimized_sp["B"], self.latest_optimized_sp["C"], self.latest_optimized_sp["D"], 0]},
                {"type": "SPs", "SPs": [self.latest_optimized_sp["H"], self.latest_optimized_sp["A"], self.latest_optimized_sp["B"], self.latest_optimized_sp["C"], self.latest_optimized_sp["D"], sp_av]}
            ]

            if result and "전체" in result:
                for row in result["전체"]:
                    desc = f"속도 SP: {row['SP']} (실수치: {row['실수치']})"
                    self.optimization_choices.append(desc)
                    self.raw_optimization_options.append({"type": "speed_row", "SP": row['SP']})
            
            if self.optimization_choices:
                self.result_select_combo.configure(values=self.optimization_choices)
                self.result_select_combo.set(self.optimization_choices[0])
                self.on_result_option_selected(self.optimization_choices[0])

        except Exception as e:
            print(f"[오류] 속도 최적화 실패: {str(e)}")

    def run_power_optimization(self):
        try:
            print(f"\n[결정력 최적화 실행 중: {self.power_pkm1.get()} -> {self.power_pkm2.get()}]")
            if not self.power_selected_moves:
                print("[경고] 최소 하나 이상의 기술을 추가해주세요.")
                return

            p1_samplefile = self.power_pkm1.get().strip()
            p2_samplefile = self.power_pkm2.get().strip()

            p1_data = self._load_sample_csv_data(p1_samplefile)
            moves_list = p1_data.get("기술", [])
            
            move_indices = []
            for m in self.power_selected_moves:
                try:
                    move_indices.append(moves_list.index(m) + 1)
                except ValueError:
                    move_indices.append(1)

            from loader.data_loader import Move
            loaded_move_dict = Move.load_move_dict()
            
            first_move_name = self.power_selected_moves[0]
            move_obj = loaded_move_dict.get(first_move_name)
            stat_type = "A"
            if move_obj and move_obj.category == "특수":
                stat_type = "C"
                print(f"[시스템] 선택한 첫번째 기술 '{first_move_name}'은(는) 특수 기술이므로 '특수공격(C)' 최적화를 진행합니다.")
            else:
                print(f"[시스템] 선택한 첫번째 기술 '{first_move_name}'은(는) 물리 기술이므로 '공격(A)' 최적화를 진행합니다.")

            nature_a = float(self.power_nature.get().strip() or "1.1")
            rank_a = int(self.power_rank_a.get().strip() or "0")
            rank_b = int(self.power_rank_b.get().strip() or "0")
            current_hp_percent = float(self.power_current_hp.get().strip() or "100")
            hits = int(self.power_hits.get().strip() or "1")
            target_prob = float(self.power_target_prob.get().strip() or "16")
            weather = self.power_weather.get().strip() or None
            field = self.power_field.get().strip() or None
            sp_av = int(self.power_sp_av.get().strip() or "32")
            crit_a = bool(self.power_crit_var.get())

            p2_data = self._load_sample_csv_data(p2_samplefile)

            optimizer = PokemonStatOptimizer()
            
            result = optimizer.optimize_power_advanced(
                p1_data, p2_data, move_indices, nature_a, rank_a, rank_b, 
                hits, target_prob, weather, field, crit_a, sp_av, current_hp_percent
            )
            
            self.optimization_choices = ["무보정 (SP = 0)", f"남은 스탯 전부 투자 (SP = {sp_av})"]
            
            h_curr = self.latest_optimized_sp.get("H", 0)
            a_curr = self.latest_optimized_sp.get("A", 0)
            b_curr = self.latest_optimized_sp.get("B", 0)
            c_curr = self.latest_optimized_sp.get("C", 0)
            d_curr = self.latest_optimized_sp.get("D", 0)
            s_curr = self.latest_optimized_sp.get("S", 0)

            zero_sps = [h_curr, 0 if stat_type=="A" else a_curr, b_curr, 0 if stat_type=="C" else c_curr, d_curr, s_curr]
            max_sps = [h_curr, sp_av if stat_type=="A" else a_curr, b_curr, sp_av if stat_type=="C" else c_curr, d_curr, s_curr]

            self.raw_optimization_options = [
                {"type": "SPs", "SPs": zero_sps},
                {"type": "SPs", "SPs": max_sps}
            ]

            if result and "A_sp" in result:
                optimized_sp_val = result['A_sp']
                stat_name_kr = "공격" if stat_type == "A" else "특수공격"
                desc = f"{stat_name_kr} SP: {optimized_sp_val} (실수치: {result['A']}, K.O확률: {result['ko_probability']}%)"
                self.optimization_choices.append(desc)
                self.raw_optimization_options.append({"type": "power_res", "stat_type": stat_type, "sp_val": optimized_sp_val})
                
                self.result_select_combo.configure(values=self.optimization_choices)
                self.result_select_combo.set(self.optimization_choices[0])
                self.on_result_option_selected(self.optimization_choices[0])

        except Exception as e:
            print(f"[오류] 결정력 최적화 실패: {str(e)}")

    def run_bulk_optimization(self):
        try:
            print(f"\n[내구 최적화 실행 중: {self.bulk_pkm1.get()} vs {self.bulk_pkm2.get()}]")
            if not self.bulk_selected_moves:
                print("[경고] 최소 하나 이상의 상대 기술을 추가해주세요.")
                return

            p1_samplefile = self.bulk_pkm1.get().strip()
            p2_samplefile = self.bulk_pkm2.get().strip()

            p2_data = self._load_sample_csv_data(p2_samplefile)
            moves_list = p2_data.get("기술", [])
            
            move_indices = []
            for m in self.bulk_selected_moves:
                try:
                    move_indices.append(moves_list.index(m) + 1)
                except ValueError:
                    move_indices.append(1)

            av_sp = int(self.bulk_av_sp.get().strip() or "32")
            nb = float(self.bulk_nature_b.get().strip() or "1.0")
            nd = float(self.bulk_nature_d.get().strip() or "1.0")
            ra = int(self.bulk_rank_a.get().strip() or "0")
            rb = int(self.bulk_rank_b.get().strip() or "0")
            thp = float(self.bulk_target_hp.get().strip() or "0")

            w_def = float(self.bulk_w_def.get().strip() or "0.5")
            w_spdef = float(self.bulk_w_spdef.get().strip() or "0.5")
            tgp = int(self.bulk_tg_prob.get().strip() or "100")
            hits = int(self.bulk_hits.get().strip() or "1")
            weather = self.bulk_weather.get().strip() or None
            field = self.bulk_field.get().strip() or None
            crit_b = bool(self.bulk_crit_var.get())

            p1_data = self._load_sample_csv_data(p1_samplefile)

            optimizer = PokemonStatOptimizer()
            results = optimizer.optimize_bulk_advanced(
                p1_data, p2_data, move_indices, av_sp, nb, nd,
                ra, rb, thp, w_def, w_spdef, tgp, hits, weather, field, crit_b
            )
            
            self.optimization_choices = ["무보정 (SP = 0)", f"남은 스탯 전부 투자 (H분배 SP = {av_sp})"]
            self.raw_optimization_options = [
                {"type": "SPs", "SPs": [0, self.latest_optimized_sp["A"], 0, self.latest_optimized_sp["C"], 0, self.latest_optimized_sp["S"]]},
                {"type": "SPs", "SPs": [av_sp, self.latest_optimized_sp["A"], 0, self.latest_optimized_sp["C"], 0, self.latest_optimized_sp["S"]]}
            ]

            if results:
                for res in results:
                    desc = f"[{res.get('category', '분배')}] 총SP={res.get('total_sp')} (H={res.get('hp_point')}, B={res.get('b_point')}, D={res.get('d_point')}) - 생존율: {res.get('survival_probability'):.1f}%"
                    self.optimization_choices.append(desc)
                    self.raw_optimization_options.append({"type": "bulk_res", "res": res})
            
            if self.optimization_choices:
                self.result_select_combo.configure(values=self.optimization_choices)
                self.result_select_combo.set(self.optimization_choices[0])
                self.on_result_option_selected(self.optimization_choices[0])

        except Exception as e:
            print(f"[오류] 내구 최적화 실행 중 오류 발생: {str(e)}")

    def on_result_option_selected(self, choice_text):
        if not self.raw_optimization_options:
            return
        
        for idx, text in enumerate(self.optimization_choices):
            if text == choice_text:
                selected_data = self.raw_optimization_options[idx]
                dtype = selected_data.get("type")

                if dtype == "zero":
                    sp_dict = {"H": 0, "A": 0, "B": 0, "C": 0, "D": 0, "S": 0}
                elif dtype == "max":
                    sp_dict = {"H": selected_data["SPs"][0], "A": selected_data["SPs"][1], "B": selected_data["SPs"][2], 
                               "C": selected_data["SPs"][3],"D": selected_data["SPs"][4], "S": selected_data["SPs"][5]}
                elif dtype == "SPs":
                    sp_dict = {"H": selected_data["SPs"][0], "A": selected_data["SPs"][1], "B": selected_data["SPs"][2], 
                               "C": selected_data["SPs"][3], "D": selected_data["SPs"][4], "S": selected_data["SPs"][5]}
                elif dtype == "speed_row":
                    sp_dict = self.latest_optimized_sp.copy()
                    sp_dict["S"] = selected_data.get("SP", 0)
                elif dtype == "power_res":
                    sp_dict = self.latest_optimized_sp.copy()
                    stype = selected_data.get("stat_type", "A")
                    sp_val = selected_data.get("sp_val", selected_data.get("A_sp", 0))
                    
                    if stype == "C":
                        sp_dict["C"] = sp_val
                    else:
                        sp_dict["A"] = sp_val
                elif dtype == "bulk_res":
                    res = selected_data.get("res", {})
                    sp_dict = self.latest_optimized_sp.copy()
                    sp_dict["H"] = res.get("hp_point", 0)
                    sp_dict["B"] = res.get("b_point", 0)
                    sp_dict["D"] = res.get("d_point", 0)
                else:
                    sp_dict = self.latest_optimized_sp.copy()

                self.latest_optimized_sp = sp_dict

                for stat, entry in self.manual_sp_entries.items():
                    entry.delete(0, "end")
                    entry.insert(0, str(self.latest_optimized_sp.get(stat, 0)))
                break

    def regenerate_sample_file(self):
        try:
            target_sample = self.regen_target_combo.get().strip()
            new_filename = self.regen_filename_entry.get().strip()

            if not target_sample:
                print("[경고] 기준이 될 대상 샘플을 선택해주세요.")
                return
            if not new_filename:
                print("[경고] 저장할 파일명을 입력해주세요.")
                return

            for stat, entry in self.manual_sp_entries.items():
                val = entry.get().strip()
                try:
                    self.latest_optimized_sp[stat] = int(val) if val else 0
                except ValueError:
                    self.latest_optimized_sp[stat] = 0

            h_sp = self.latest_optimized_sp["H"]
            a_sp = self.latest_optimized_sp["A"]
            b_sp = self.latest_optimized_sp["B"]
            c_sp = self.latest_optimized_sp["C"]
            d_sp = self.latest_optimized_sp["D"]
            s_sp = self.latest_optimized_sp["S"]

            p1_data = self._load_sample_csv_data(target_sample)
            
            name = p1_data.get("포켓몬", "")
            note = p1_data.get("노트", "")
            item = p1_data.get("지닌도구", "")
            ability = p1_data.get("특성", "")
            nature = p1_data.get("성격", "노력")
            level = p1_data.get("LV", 50)
            ivs = p1_data.get("IVs", [31, 31, 31, 31, 31, 31])
            moves = p1_data.get("기술", [])
            weather = p1_data.get("날씨", "")
            
            updated_SPs = [h_sp, a_sp, b_sp, c_sp, d_sp, s_sp]

            saved_path = SampleCSVbuilder.make_sample_csv(
                filename=new_filename,
                name=name,
                note=note,
                item=item,
                ability=ability,
                nature=nature,
                level=level,
                SPs=updated_SPs,
                IVs=ivs,
                moves=moves,
                weather=weather
            )

            print(f"\n[성공] 샘플 파일이 성공적으로 재생성 및 저장되었습니다!\n→ 경로: {saved_path}")
            print(f"적용된 SP = H:{h_sp}, A:{a_sp}, B:{b_sp}, C:{c_sp}, D:{d_sp}, S:{s_sp}")

            self.refresh_samples()

        except Exception as e:
            print(f"[오류] 샘플 재생성 실패: {str(e)}")
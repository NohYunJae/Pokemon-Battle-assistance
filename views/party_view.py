import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

# 백엔드 분석 모듈 임포트 (프로젝트 경로에 맞게 조정하세요)
from party_maker import TeamAnalyzer, PokemonSelector, DATA_DIR

# =====================================================================
# [전체 글꼴 설정] 아래 FONT_FAMILY 값만 변경하면 화면 전체 글꼴이 일괄 변경됩니다.
# =====================================================================
FONT_FAMILY = "맑은 고딕"  # macOS의 경우 "Apple SD Gothic Neo" 등으로 변경 가능

FONTS = {
    "title": (FONT_FAMILY, 18, "bold"),
    "subtitle": (FONT_FAMILY, 14, "bold"),
    "body": (FONT_FAMILY, 12),
    "body_bold": (FONT_FAMILY, 12, "bold"),
    "small": (FONT_FAMILY, 11),
    "tree_heading": (FONT_FAMILY, 11, "bold"),
    "tree_row": (FONT_FAMILY, 11),
}


class PartyView(ctk.CTkFrame):
    """포켓몬 파티 상성 분석 및 보완 포켓몬 추천 GUI 뷰"""

    def __init__(self, master, font_family=None, **kwargs):
        super().__init__(master, **kwargs)

        if font_family:
            self.set_global_font(font_family, refresh_ui=False)

        self.samples_dir = os.path.join(DATA_DIR, "samples")
        self.available_samples = self._load_sample_list()
        self.slot_combos = []

        # 분석 결과 원본 데이터 보관 (상세 보기 연동용)
        self.general_data = []
        self.mega_data = []

        self._setup_styles()
        self._build_ui()

    def set_global_font(self, new_font_family: str, refresh_ui: bool = True):
        """실행 중 또는 초기화 시 전체 글꼴을 일괄 변경하는 메서드"""
        global FONT_FAMILY
        FONT_FAMILY = new_font_family
        FONTS["title"] = (FONT_FAMILY, 18, "bold")
        FONTS["subtitle"] = (FONT_FAMILY, 14, "bold")
        FONTS["body"] = (FONT_FAMILY, 12)
        FONTS["body_bold"] = (FONT_FAMILY, 12, "bold")
        FONTS["small"] = (FONT_FAMILY, 11)
        FONTS["tree_heading"] = (FONT_FAMILY, 11, "bold")
        FONTS["tree_row"] = (FONT_FAMILY, 11)

        if refresh_ui:
            self._setup_styles()
            self._apply_font_recursive(self)

    def _apply_font_recursive(self, widget):
        """하위 위젯들의 폰트를 재귀적으로 업데이트"""
        for child in widget.winfo_children():
            try:
                if isinstance(child, ctk.CTkLabel):
                    current_font = child.cget("font")
                    if isinstance(current_font, tuple):
                        size = current_font[1]
                        weight = current_font[2] if len(current_font) > 2 else "normal"
                        child.configure(font=(FONT_FAMILY, size, weight))
                    else:
                        child.configure(font=FONTS["body"])
                elif isinstance(child, (ctk.CTkButton, ctk.CTkComboBox, ctk.CTkEntry)):
                    child.configure(font=FONTS["body"])
                elif isinstance(child, ctk.CTkTextbox):
                    child.configure(font=FONTS["small"])
                elif isinstance(child, ctk.CTkTabview):
                    child._segmented_button.configure(font=FONTS["body_bold"])
            except Exception:
                pass
            self._apply_font_recursive(child)

    def _setup_styles(self):
        """ttk.Treeview 스타일 및 글꼴 설정"""
        style = ttk.Style()
        style.theme_use("default")

        style.configure(
            "Party.Treeview",
            background="#2b2b2b",
            foreground="#ffffff",
            fieldbackground="#2b2b2b",
            rowheight=30,
            font=FONTS["tree_row"],
            borderwidth=0,
        )
        style.configure(
            "Party.Treeview.Heading",
            background="#1f538d",
            foreground="#ffffff",
            font=FONTS["tree_heading"],
            relief="flat",
        )
        style.map("Party.Treeview", background=[("selected", "#144870")])

    def _load_sample_list(self):
        """samples 폴더에서 사용 가능한 포켓몬 샘플 목록 로드"""
        if not os.path.exists(self.samples_dir):
            return []
        files = [os.path.splitext(f)[0] for f in os.listdir(self.samples_dir) if f.endswith(".csv")]
        return sorted(files)

    def refresh_samples(self):
        """샘플 목록 새로고침"""
        self.available_samples = self._load_sample_list()
        values = ["(선택 안함)"] + self.available_samples
        for combo in self.slot_combos:
            current = combo.get()
            combo.configure(values=values)
            if current not in values:
                combo.set("(선택 안함)")

    def _build_ui(self):
        """전체 레이아웃 구성 (좌측: 파티 구성 / 우측: 분석 및 추천 결과)"""
        self.grid_columnconfigure(0, weight=1, minsize=310)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        # ==================== 좌측 패널: 파티 멤버 선택 ====================
        left_panel = ctk.CTkFrame(self, corner_radius=10)
        left_panel.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        left_panel.grid_columnconfigure(0, weight=1)

        header_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_frame, text="파티 구성 (최대 6마리)", font=FONTS["title"], anchor="w"
        ).grid(row=0, column=0, sticky="w")

        refresh_btn = ctk.CTkButton(
            header_frame,
            text="새로고침",
            width=70,
            height=28,
            font=FONTS["small"],
            command=self.refresh_samples,
        )
        refresh_btn.grid(row=0, column=1, sticky="e")

        # 6개 슬롯 콤보박스 생성
        combo_values = ["(선택 안함)"] + self.available_samples
        for i in range(6):
            slot_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
            slot_frame.grid(row=i + 1, column=0, padx=15, pady=6, sticky="ew")
            slot_frame.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                slot_frame, text=f"슬롯 {i + 1}", font=FONTS["body_bold"], width=55, anchor="w"
            ).grid(row=0, column=0, padx=(0, 8))

            combo = ctk.CTkComboBox(
                slot_frame,
                values=combo_values,
                font=FONTS["body"],
                dropdown_font=FONTS["body"],
                state="readonly",
            )
            combo.set("(선택 안함)")
            combo.grid(row=0, column=1, sticky="ew")
            self.slot_combos.append(combo)

        # 옵션: 자속 공격 추천 반영 개수
        option_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        option_frame.grid(row=7, column=0, padx=15, pady=(15, 5), sticky="ew")
        option_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            option_frame, text="추천 공격타입 기준:", font=FONTS["small"], anchor="w"
        ).grid(row=0, column=0, padx=(0, 8))

        self.top_n_var = ctk.StringVar(value="상위 3개 타입")
        self.top_n_combo = ctk.CTkComboBox(
            option_frame,
            values=["상위 1개 타입", "상위 2개 타입", "상위 3개 타입", "상위 5개 타입"],
            variable=self.top_n_var,
            font=FONTS["small"],
            dropdown_font=FONTS["small"],
            state="readonly",
        )
        self.top_n_combo.grid(row=0, column=1, sticky="ew")

        # 실행 및 초기화 버튼
        self.analyze_btn = ctk.CTkButton(
            left_panel,
            text="파티 분석 및 보완 추천 실행",
            height=42,
            font=FONTS["body_bold"],
            command=self.start_analysis,
        )
        self.analyze_btn.grid(row=8, column=0, padx=15, pady=(15, 8), sticky="ew")

        clear_btn = ctk.CTkButton(
            left_panel,
            text="슬롯 전체 초기화",
            height=32,
            fg_color="#555555",
            hover_color="#444444",
            font=FONTS["small"],
            command=self._clear_slots,
        )
        clear_btn.grid(row=9, column=0, padx=15, pady=(0, 10), sticky="ew")

        self.status_label = ctk.CTkLabel(
            left_panel, text="샘플을 선택한 뒤 분석을 실행하세요.", font=FONTS["small"], text_color="#aaaaaa"
        )
        self.status_label.grid(row=10, column=0, padx=15, pady=(5, 15), sticky="w")

        # ==================== 우측 패널: 분석 결과 탭 뷰 ====================
        right_panel = ctk.CTkFrame(self, corner_radius=10)
        right_panel.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(right_panel)
        self.tabview.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.tabview._segmented_button.configure(font=FONTS["body_bold"])

        self.tab_summary = self.tabview.add("파티 상성 요약")
        self.tab_general = self.tabview.add("일반 포켓몬 추천 (Top 100)")
        self.tab_mega = self.tabview.add("메가진화 포켓몬 추천")

        self._build_summary_tab()
        self._build_recommendation_tabs()

    def _build_summary_tab(self):
        """[탭 1] 파티 방어 취약점 및 공격 일관성 요약 UI"""
        self.tab_summary.grid_columnconfigure(0, weight=1)
        self.tab_summary.grid_columnconfigure(1, weight=1)
        self.tab_summary.grid_rowconfigure(0, weight=1)
        self.tab_summary.grid_rowconfigure(1, weight=1)

        # 1. 방어 취약점 (공통 약점 / 반감 불가)
        def_box = ctk.CTkFrame(self.tab_summary)
        def_box.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        def_box.grid_columnconfigure(0, weight=1)
        def_box.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(def_box, text="🛡️ 파티 방어 취약 타입 분석 현황", font=FONTS["subtitle"], anchor="w").grid(
            row=0, column=0, padx=12, pady=(10, 5), sticky="w"
        )
        self.def_textbox = ctk.CTkTextbox(def_box, font=FONTS["small"], wrap="word")
        self.def_textbox.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.def_textbox.configure(state="disabled")

        # 2. 추천 공격 타입 및 기술 분포
        atk_box = ctk.CTkFrame(self.tab_summary)
        atk_box.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        atk_box.grid_columnconfigure(0, weight=1)
        atk_box.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(atk_box, text="⚔️ 파티 추천 공격 타입 및 기술 분포", font=FONTS["subtitle"], anchor="w").grid(
            row=0, column=0, padx=12, pady=(10, 5), sticky="w"
        )
        self.atk_textbox = ctk.CTkTextbox(atk_box, font=FONTS["small"], wrap="word")
        self.atk_textbox.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.atk_textbox.configure(state="disabled")

        # 3. 약점 타격 불가 방어 조합 리스트
        unweak_box = ctk.CTkFrame(self.tab_summary)
        unweak_box.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        unweak_box.grid_columnconfigure(0, weight=1)
        unweak_box.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            unweak_box, text="⚠️ 약점(또는 1배 4만 이상) 타격 불가 방어 타입 조합", font=FONTS["subtitle"], anchor="w"
        ).grid(row=0, column=0, padx=12, pady=(10, 5), sticky="w")
        self.unweak_textbox = ctk.CTkTextbox(unweak_box, font=FONTS["small"], wrap="word")
        self.unweak_textbox.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.unweak_textbox.configure(state="disabled")

    def _build_recommendation_tabs(self):
        """[탭 2, 3] 일반 및 메가진화 추천 포켓몬 Treeview + 하단 상세 패널 구성"""
        self.general_tree, self.general_detail_box = self._create_recommend_panel(
            self.tab_general, is_mega=False
        )
        self.mega_tree, self.mega_detail_box = self._create_recommend_panel(
            self.tab_mega, is_mega=True
        )

    def _create_recommend_panel(self, parent, is_mega: bool):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=3)
        parent.grid_rowconfigure(1, weight=1, minsize=125)

        # 상단 표 프레임
        table_frame = ctk.CTkFrame(parent, fg_color="transparent")
        table_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5, 2))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        columns = (
            "rank",
            "name",
            "types",
            "total_score",
            "safety",
            "weak_cnt",
            "not_res_cnt",
            "atk_cnt",
            "def_cover",
            "atk_cover",
        )
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="Party.Treeview")

        headings = {
            "rank": ("순위", 42, "center"),
            "name": ("포켓몬 (특성)", 145, "w"),
            "types": ("타입", 95, "center"),
            "total_score": ("총점", 60, "center"),
            "safety": ("방어안전성", 75, "center"),
            "weak_cnt": ("약점커버", 65, "center"),
            "not_res_cnt": ("반감불가커버", 85, "center"),
            "atk_cnt": ("자속보완", 65, "center"),
            "def_cover": ("🛡️ 방어 보완 타입", 160, "w"),
            "atk_cover": ("⚔️ 자속 공격 보완", 120, "w"),
        }

        for col, (text, width, anchor) in headings.items():
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor=anchor)

        v_scroll = ctk.CTkScrollbar(table_frame, orientation="vertical", command=tree.yview)
        h_scroll = ctk.CTkScrollbar(table_frame, orientation="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        # 하단 선택 항목 상세 정보 카드 (test_recommend_combined 출력 형식 그대로 정돈)
        detail_frame = ctk.CTkFrame(parent)
        detail_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(4, 5))
        detail_frame.grid_columnconfigure(0, weight=1)
        detail_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            detail_frame,
            text="📋 선택한 포켓몬 상세 점수 및 보완 내역 (목록에서 항목을 클릭하세요)",
            font=FONTS["body_bold"],
            anchor="w",
        ).grid(row=0, column=0, padx=10, pady=(6, 2), sticky="w")

        detail_box = ctk.CTkTextbox(detail_frame, font=FONTS["small"], height=95, wrap="word")
        detail_box.grid(row=1, column=0, padx=10, pady=(0, 8), sticky="nsew")
        detail_box.insert("1.0", "분석 실행 후 표에서 포켓몬을 선택하면 세부 점수 내역이 여기에 표시됩니다.")
        detail_box.configure(state="disabled")

        # 선택 이벤트 바인딩
        tree.bind(
            "<<TreeviewSelect>>",
            lambda event, t=tree, b=detail_box, m=is_mega: self._on_tree_select(t, b, m),
        )

        return tree, detail_box

    def _on_tree_select(self, tree: ttk.Treeview, detail_box: ctk.CTkTextbox, is_mega: bool):
        """표에서 행 선택 시 test_recommend_combined 스타일의 상세 정보를 하단에 출력"""
        selected = tree.selection()
        if not selected:
            return

        values = tree.item(selected[0], "values")
        if not values:
            return

        rank = int(values[0])
        data_source = self.mega_data if is_mega else self.general_data
        if rank - 1 >= len(data_source):
            return

        item = data_source[rank - 1]
        p_name = item["name"]
        p_types = "/".join(item["types"])
        c_types = ", ".join(item["covered_types"]) if item["covered_types"] else "없음"
        o_types = ", ".join(item["matched_offense_types"]) if item["matched_offense_types"] else "없음"

        detail_text = (
            f"✨ {rank}위. [{p_name}]  (타입: {p_types})\n"
            f"  🛡️ 방어 보완: {c_types}\n"
            f"  ⚔️ 자속 공격 보완: {o_types}\n"
            f"  📊 점수 내역: 총점 {item['total_score']:.1f}점  "
            f"(방어안전성: {item['safety_score']:.0f}점 / 약점커버: {item['weakness_score']}개 / "
            f"반감불가커버: {item['not_resisted_score']}개 / 자속공격보완: {item['offense_score']}개)"
        )
        self._set_textbox_content(detail_box, detail_text)

    def _clear_slots(self):
        for combo in self.slot_combos:
            combo.set("(선택 안함)")
        self.status_label.configure(text="슬롯이 초기화되었습니다.", text_color="#aaaaaa")

    def start_analysis(self):
        """백그라운드 스레드에서 파티 분석 실행"""
        selected_samples = [
            combo.get() for combo in self.slot_combos if combo.get() and combo.get() != "(선택 안함)"
        ]

        if not selected_samples:
            messagebox.showwarning("입력 오류", "최소 1마리 이상의 포켓몬 샘플을 선택해주세요.")
            return

        top_n_str = self.top_n_var.get()
        top_n = int(top_n_str.split(" ")[1].replace("개", ""))

        self.analyze_btn.configure(state="disabled")
        self.status_label.configure(text="파티 상성 및 추천 포켓몬 분석 중...", text_color="#4da6ff")

        thread = threading.Thread(
            target=self._run_analysis_worker, args=(selected_samples, top_n), daemon=True
        )
        thread.start()

    def _run_analysis_worker(self, selected_samples, top_n):
        try:
            analyzer = TeamAnalyzer(selected_samples)
            offense_result = analyzer.analyze_party_offense()

            selector = PokemonSelector()
            (
                general_top100,
                mega_list,
                common_weaknesses,
                common_not_resisted,
                recommended_attack_types,
            ) = selector.recommend_pokemon_combined(selected_samples, top_n_offense=top_n)

            self.after(
                0,
                self._update_ui_results,
                offense_result,
                general_top100,
                mega_list,
                common_weaknesses,
                common_not_resisted,
                recommended_attack_types,
                top_n,
            )
        except Exception as e:
            self.after(0, self._handle_error, str(e))

    def _handle_error(self, err_msg):
        self.analyze_btn.configure(state="normal")
        self.status_label.configure(text="분석 중 오류가 발생했습니다.", text_color="#ff5555")
        messagebox.showerror("분석 오류", f"파티 분석 중 에러가 발생했습니다:\n{err_msg}")

    def _set_textbox_content(self, textbox: ctk.CTkTextbox, text: str):
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        textbox.insert("1.0", text)
        textbox.configure(state="disabled")

    def _update_ui_results(
        self,
        offense_result,
        general_top100,
        mega_list,
        common_weaknesses,
        common_not_resisted,
        recommended_attack_types,
        top_n,
    ):
        self.general_data = general_top100
        self.mega_data = mega_list

        # 1. 방어 취약 타입 텍스트 업데이트 (test 코드 포맷 반영)
        def_lines = ["• 공통 약점 타입 (1순위 보완 대상):"]
        if common_weaknesses:
            for w_type, cnt in common_weaknesses.items():
                def_lines.append(f"    - {w_type}: {cnt}마리")
        else:
            def_lines.append("    - 없음")

        def_lines.append("\n• 반감 불가 타입 (2순위 보완 대상):")
        if common_not_resisted:
            for nr_type, cnt in common_not_resisted.items():
                def_lines.append(f"    - {nr_type}: {cnt}마리")
        else:
            def_lines.append("    - 없음")

        self._set_textbox_content(self.def_textbox, "\n".join(def_lines))

        # 2. 파티 추천 공격 타입 및 기술 분포 업데이트 (test 코드 포맷 반영)
        atk_lines = [f"• 추천 공격 타입 (자속 반영 대상 상위 {top_n}개):"]
        if recommended_attack_types:
            for idx, rec in enumerate(recommended_attack_types[:top_n], 1):
                atk_lines.append(f"    {idx}. {rec['타입']} (커버 가능한 방어 조합 수: {rec['커버가능조합수']}개)")
        else:
            atk_lines.append("    - 추천 공격 타입 없음")

        atk_lines.append("\n• 물리 / 특수 기술 비율:")
        ratios = offense_result.get("category_ratios", {})
        if ratios:
            for cat, info in ratios.items():
                atk_lines.append(f"    - {cat}: {info['개수']}개 ({info['비율(%)']}%)")

        atk_lines.append("\n• 파티 보유 공격 기술 타입:")
        type_to_moves = offense_result.get("type_to_moves", {})
        for t, moves in type_to_moves.items():
            atk_lines.append(f"    - {t}: {', '.join(moves)}")

        self._set_textbox_content(self.atk_textbox, "\n".join(atk_lines))

        # 3. 약점 타격 불가 조합 업데이트
        unweak_list = offense_result.get("unweakened_combinations", [])
        unweak_lines = []
        if unweak_list:
            for item in unweak_list:
                combo_str = "/".join(item["combination"])
                weak_str = ", ".join(item["weakness_types"][:5])
                unweak_lines.append(f" • [{combo_str}]  →  유효 약점: {weak_str}")
        else:
            unweak_lines.append(" • 사각지대 방어 타입 조합이 없습니다.")

        self._set_textbox_content(self.unweak_textbox, "\n".join(unweak_lines))

        # 4. 추천 포켓몬 Treeview 갱신 (세부 점수 컬럼 모두 포함)
        self._populate_tree(self.general_tree, general_top100)
        self._populate_tree(self.mega_tree, mega_list)

        # 첫 번째 항목 자동 선택하여 하단 상세 내역 즉시 표시
        if general_top100:
            first_id = self.general_tree.get_children()[0]
            self.general_tree.selection_set(first_id)
            self._on_tree_select(self.general_tree, self.general_detail_box, is_mega=False)
        else:
            self._set_textbox_content(self.general_detail_box, "조건을 만족하는 일반 포켓몬이 없습니다.")

        if mega_list:
            first_mega_id = self.mega_tree.get_children()[0]
            self.mega_tree.selection_set(first_mega_id)
            self._on_tree_select(self.mega_tree, self.mega_detail_box, is_mega=True)
        else:
            self._set_textbox_content(self.mega_detail_box, "조건을 만족하는 메가진화 포켓몬이 없습니다.")

        self.analyze_btn.configure(state="normal")
        self.status_label.configure(
            text=f"완료! (일반 {len(general_top100)}마리 / 메가 {len(mega_list)}마리 추천)",
            text_color="#55ff55",
        )

    def _populate_tree(self, tree: ttk.Treeview, data_list: list):
        for item in tree.get_children():
            tree.delete(item)

        for idx, item in enumerate(data_list, 1):
            p_name = item["name"]
            p_types = "/".join(item["types"])
            total = f"{item['total_score']:.1f}점"
            safety = f"{item['safety_score']:.0f}점"
            weak_cnt = f"{item['weakness_score']}개"
            not_res_cnt = f"{item['not_resisted_score']}개"
            atk_cnt = f"{item['offense_score']}개"
            c_types = ", ".join(item["covered_types"]) if item["covered_types"] else "없음"
            o_types = ", ".join(item["matched_offense_types"]) if item["matched_offense_types"] else "없음"

            tree.insert(
                "",
                "end",
                values=(
                    idx,
                    p_name,
                    p_types,
                    total,
                    safety,
                    weak_cnt,
                    not_res_cnt,
                    atk_cnt,
                    c_types,
                    o_types,
                ),
            )
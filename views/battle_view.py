import os
import csv
from tkinter import ttk
import customtkinter as ctk
from pokeCSVbuilder import BattleCSVbuilder

DATA_DIR = os.path.join(os.path.expanduser("~"), "PokemonDATA", "data")

class BattleView:
    def __init__(self, parent_tab):
        self.tab = parent_tab
        self.create_widgets()

    def create_widgets(self):
        title = ctk.CTkLabel(self.tab, text="샘플 배틀 시트 생성기", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(anchor="w", padx=20, pady=(15, 2))

        info_label = ctk.CTkLabel(self.tab, text="두 개의 포켓몬 샘플을 비교하는 배틀 시트(CSV)를 생성하고 결과를 확인합니다.")
        info_label.pack(anchor="w", padx=20, pady=(0, 10))

        # --- 상단 입력 필드 프레임 ---
        input_frame = ctk.CTkFrame(self.tab, fg_color="transparent")
        input_frame.pack(anchor="w", padx=20, pady=5, fill="x")

        # 포켓몬 샘플 1 선택/입력
        lbl1 = ctk.CTkLabel(input_frame, text="포켓몬 샘플 1:", width=110, anchor="w")
        lbl1.grid(row=0, column=0, sticky="w", pady=4)
        
        self.sample1_combo = ctk.CTkComboBox(input_frame, values=self.get_sample_list(), width=220)
        self.sample1_combo.grid(row=0, column=1, padx=10, pady=4)

        # 포켓몬 샘플 2 선택/입력
        lbl2 = ctk.CTkLabel(input_frame, text="포켓몬 샘플 2:", width=110, anchor="w")
        lbl2.grid(row=1, column=0, sticky="w", pady=4)
        
        self.sample2_combo = ctk.CTkComboBox(input_frame, values=self.get_sample_list(), width=220)
        self.sample2_combo.grid(row=1, column=1, padx=10, pady=4)

        # 저장할 결과 파일 이름 입력
        lbl3 = ctk.CTkLabel(input_frame, text="결과 파일 이름:", width=110, anchor="w")
        lbl3.grid(row=2, column=0, sticky="w", pady=4)
        
        self.filename_entry = ctk.CTkEntry(input_frame, width=220)
        self.filename_entry.grid(row=2, column=1, padx=10, pady=4)
        self.filename_entry.insert(0, "battle_sheet")

        # 새로고침 및 실행 버튼
        btn_refresh = ctk.CTkButton(input_frame, text="목록 새로고침", width=120, command=self.refresh_samples)
        btn_refresh.grid(row=0, column=2, padx=15, pady=4)

        self.btn_run = ctk.CTkButton(input_frame, text="배틀 시트 생성 및 결과 보기", fg_color="#0284c7", width=180, command=self.on_submit)
        self.btn_run.grid(row=2, column=2, padx=15, pady=4)

        # 상태 안내 레이블
        self.status_lbl = ctk.CTkLabel(self.tab, text="상태: 준비 완료", text_color="gray", font=ctk.CTkFont(size=12))
        self.status_lbl.pack(anchor="w", padx=20, pady=(8, 0))

        # --- 💡 [표 위젯(Treeview) 프레임 구축] ---
        table_frame = ctk.CTkFrame(self.tab)
        table_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # ttk 스타일 설정 (표 디자인)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background="#FFFFFF",
                        foreground="#000000",
                        rowheight=24,
                        fieldbackground="#FFFFFF",
                        font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"), background="#E0F2FE", foreground="#0369A1")

        # 14개 열 생성 (배틀 시트 CSV 열 개수인 14개 기준)
        self.col_names = [f"C{i+1}" for i in range(14)]
        
        self.tree = ttk.Treeview(table_frame, columns=self.col_names, show="headings", selectmode="browse")
        
        # 각 열 너비 및 헤더 초기화
        for col in self.col_names:
            self.tree.heading(col, text="")
            self.tree.column(col, width=65, anchor="center")

        # 스크롤바 추가 (가로/세로)
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

    def get_sample_list(self):
        """저장된 샘플(.csv) 목록을 불러옵니다."""
        sample_path = os.path.join(DATA_DIR, 'samples')
        if not os.path.exists(sample_path):
            return ["test_sample"]
        
        files = [f[:-4] for f in os.listdir(sample_path) if f.endswith('.csv')]
        return files if files else ["test_sample"]

    def refresh_samples(self):
        """샘플 목록 콤보박스를 갱신합니다."""
        sample_list = self.get_sample_list()
        self.sample1_combo.configure(values=sample_list)
        self.sample2_combo.configure(values=sample_list)
        self.status_lbl.configure(text="상태: 샘플 목록이 새로고침 되었습니다.", text_color="#0284c7")

    def display_csv_in_table(self, file_path):
        """CSV 파일을 읽어서 표(Treeview) 위젯에 삽입합니다."""
        # 기존 데이터 삭제
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            with open(file_path, mode='r', encoding='utf-8-sig') as f:
                reader = list(csv.reader(f))

            if not reader:
                return

            for row in reader:
                padded_row = row + [""] * (14 - len(row))
                self.tree.insert("", "end", values=padded_row)

            self.status_lbl.configure(text=f"상태: 성공적으로 표를 불러왔습니다. ({os.path.basename(file_path)})", text_color="green")
        except Exception as e:
            self.status_lbl.configure(text=f"오류: {str(e)}", text_color="red")

    def on_submit(self):
        try:
            pkm_sample1 = self.sample1_combo.get().strip()
            pkm_sample2 = self.sample2_combo.get().strip()
            filename = self.filename_entry.get().strip()

            if not pkm_sample1 or not pkm_sample2:
                raise ValueError("비교할 두 포켓몬 샘플을 모두 선택해주세요.")
            if not filename:
                raise ValueError("저장할 파일 이름을 입력해주세요.")

            sheet_builder = BattleCSVbuilder(pkm_sample1, pkm_sample2)
            sheet_builder.write_battle_sheet(filename)

            # 저장된 실제 파일 경로로 표 업데이트
            saved_file_name = os.path.basename(sheet_builder.output_path)
            self.display_csv_in_table(sheet_builder.output_path)
            self.status_lbl.configure(text=f"상태: 저장 및 표 출력 완료 -> {saved_file_name}", text_color="#0284c7")

        except Exception as e:
            self.status_lbl.configure(text=f"오류 발생: {str(e)}", text_color="red")
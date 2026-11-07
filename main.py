import os
import customtkinter as ctk
from PIL import Image

from views.calculator_view import CalculatorView
from views.sample_view import SampleView
from views.battle_view import BattleView
from views.optimizer_view import OptimizerView
from views.spd_calc_view import SpdCalculatorView

DATA_DIR = os.path.join(os.path.expanduser("~"), "PokemonDATA", "data")

# ==========================================
# [전체 디자인 설정 영역]
# ==========================================
MAIN_UI_CONFIG = {
    "font_family": "Malgun Gothic",
    "tab_selected_bg": "#0284C7",
    "tab_selected_hover": "#0369A1",
    "tab_unselected_bg": "#93C5FD",
    "tab_unselected_hover": "#60A5FA",
    "tab_text_selected": "#FFFFFF",
    "tab_text_unselected": "#1E3A8A",
}
# ==========================================

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

class BTAssistanceApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Pokemon Battle Assistance")
        self.geometry("1100x750")
        self.resizable(False, False)

        bg_image_path = os.path.join(DATA_DIR, 'images', 'bg_lg_img.png')

        if os.path.exists(bg_image_path):
            pil_img = Image.open(bg_image_path).resize((1100, 750), Image.Resampling.LANCZOS)
            self.bg_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(1100, 750))
            
            self.bg_label = ctk.CTkLabel(self, image=self.bg_image, text="")
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        else:
            self.configure(fg_color="#3B82F6")

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(padx=15, pady=(150, 10), fill="both", expand=True)

        self.card_box = ctk.CTkFrame(
            self.main_container,
            fg_color="#E0F2FE",
            corner_radius=10,
            border_width=2,
            border_color="#0284C7"
        )
        self.card_box.pack(fill="both", expand=True, padx=0, pady=0)

        self.tab_button_frame = ctk.CTkFrame(self.card_box, fg_color="transparent")
        self.tab_button_frame.pack(side="left", anchor="n", padx=(10, 5), pady=10)

        tab_info = [
            ("1. 배틀 계산기", "calculator"),
            ("2. 스피드 비교", "spd_calc"),
            ("3. 샘플 생성기", "sample"),
            ("4. 배틀 시트", "battle"),
            ("5. 스탯 최적화", "optimizer")
        ]

        self.tab_buttons = {}

        for label_text, tab_key in tab_info:
            btn = ctk.CTkButton(
                self.tab_button_frame,
                text=label_text,
                command=lambda key=tab_key: self._select_tab(key),
                font=ctk.CTkFont(family=MAIN_UI_CONFIG["font_family"], weight="bold", size=13),
                width=130,
                height=38,
                corner_radius=8,
                fg_color=MAIN_UI_CONFIG["tab_unselected_bg"],
                hover_color=MAIN_UI_CONFIG["tab_unselected_hover"],
                text_color=MAIN_UI_CONFIG["tab_text_unselected"]
            )
            btn.pack(side="top", pady=(0, 6), fill="x")
            self.tab_buttons[tab_key] = btn

        self.content_container = ctk.CTkFrame(self.card_box, fg_color="transparent")
        self.content_container.pack(side="right", fill="both", expand=True, padx=(0, 10), pady=10)

        # 각 탭용 프레임 생성
        self.tab_calculator = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.tab_spd_calc = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.tab_sample = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.tab_battle = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.tab_optimizer = ctk.CTkFrame(self.content_container, fg_color="transparent")

        self._tabs = {
            "calculator": self.tab_calculator,
            "spd_calc": self.tab_spd_calc,
            "sample": self.tab_sample,
            "battle": self.tab_battle,
            "optimizer": self.tab_optimizer
        }

        # 뷰 인스턴스 연결
        self.calculator_view = CalculatorView(self.tab_calculator)
        self.spd_calc_view = SpdCalculatorView(self.tab_spd_calc)
        self.sample_view = SampleView(self.tab_sample)
        self.battle_view = BattleView(self.tab_battle)
        self.optimizer_view = OptimizerView(self.tab_optimizer)

        self._select_tab("calculator")

    def _select_tab(self, selected_key):
        for key, btn in self.tab_buttons.items():
            if key == selected_key:
                btn.configure(
                    fg_color=MAIN_UI_CONFIG["tab_selected_bg"],
                    hover_color=MAIN_UI_CONFIG["tab_selected_hover"],
                    text_color=MAIN_UI_CONFIG["tab_text_selected"]
                )
            else:
                btn.configure(
                    fg_color=MAIN_UI_CONFIG["tab_unselected_bg"],
                    hover_color=MAIN_UI_CONFIG["tab_unselected_hover"],
                    text_color=MAIN_UI_CONFIG["tab_text_unselected"]
                )

        for key, frame in self._tabs.items():
            if key == selected_key:
                frame.pack(fill="both", expand=True, padx=0, pady=0)
            else:
                frame.pack_forget()

if __name__ == "__main__":
    app = BTAssistanceApp()
    app.mainloop()
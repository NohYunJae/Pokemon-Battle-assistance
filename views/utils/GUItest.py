import tkinter as tk


def calculate(*args):
  try:
    # 입력된 값을 가져와서 실시간 계산
    val = float(entry_var.get())
    result_var.set(f"계산 결과: {val * 2}")
  except ValueError:
    result_var.set("올바른 숫자를 입력하세요.")


root = tk.Tk()
root.title("실시간 계산기 테스트")
root.geometry("300x200")

# 입력값 변수 (값이 바뀔 때마다 감지)
entry_var = tk.StringVar()
entry_var.trace_add("write", calculate)  # 값이 수정될 때마다 calculate 함수 실행

# UI 구성
label_guide = tk.Label(root, text="숫자를 입력하세요:")
label_guide.pack(pady=10)

entry = tk.Entry(root, textvariable=entry_var, font=("Arial", 14))
entry.pack(pady=5)

result_var = tk.StringVar(value="계산 결과: ")
label_result = tk.Label(
    root, textvariable=result_var, font=("Arial", 14, "bold")
)
label_result.pack(pady=20)

root.mainloop()
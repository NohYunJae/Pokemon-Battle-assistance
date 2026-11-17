from pathlib import Path

# 변환 대상 폴더
DATA_DIR = Path.home() / "PokemonDATA" / "data" / "samples"

csv_files = list(DATA_DIR.rglob("*.csv"))

success = 0
failed = 0

for csv_path in csv_files:
    try:
        # 기존 UTF-8 파일 읽기
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            content = f.read()

        # UTF-8 with BOM으로 덮어쓰기
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(content)

        success += 1
        print(f"[완료] {csv_path.name}")

    except Exception as e:
        failed += 1
        print(f"[실패] {csv_path.name}: {e}")

print("\n===== 변환 결과 =====")
print(f"전체 파일: {len(csv_files)}개")
print(f"성공: {success}개")
print(f"실패: {failed}개")

from PIL import Image
from pathlib import Path

import requests
import os

# 현재 파이썬 파일이 있는 폴더에 이미지 저장
SAVE_DIR = os.path.join(os.path.expanduser("~"), "PokemonDATA", "data", "images")

# PokéAPI 공식 스프라이트 저장소
BASE_URL = (
    "https://raw.githubusercontent.com/PokeAPI/sprites/"
    "master/sprites/pokemon/other/official-artwork"
)

TOTAL_POKEMON = 1025
TIMEOUT = 15

def image_converter():
    # 1. 배경 이미지와 로고 불러오기
    bg = Image.open("/Users/yunjae/PokemonDATA/gui_img/bg_img.png").convert("RGBA")
    logo = Image.open("/Users/yunjae/PokemonDATA/gui_img/logo_del_bg.png").convert("RGBA")

    # 2. 로고 크기 조절 (원하는 크기로)
    logo = logo.resize((350, 250), Image.Resampling.LANCZOS)

    # 3. 배경 이미지의 중앙 상단(위에서 1/8 지점) 좌표 계산
    # 배경 크기가 1100x750일 때 가로 중앙, 세로 약 93px 지점
    x = (bg.width - logo.width) // 2
    y = int(bg.height * 1/10) - (logo.height // 2)

    # 4. 합성 후 저장
    bg.paste(logo, (x, y), logo)
    bg.save("/Users/yunjae/PokemonDATA/gui_img/bg_lg_img.png")
    print("로고와 배경이 완벽하게 합성되었습니다!")


def download_pokemon_images():
    success_count = 0
    skipped_count = 0
    failed_count = 0

    with requests.Session() as session:
        for pokedex_id in range(1, TOTAL_POKEMON + 1):
            save_path = SAVE_DIR / f"{pokedex_id:04d}.png"

            # 이미 다운로드한 파일은 건너뛰기
            if save_path.exists() and save_path.stat().st_size > 0:
                skipped_count += 1
                continue

            url = f"{BASE_URL}/{pokedex_id}.png"

            try:
                response = session.get(url, timeout=TIMEOUT)

                if response.status_code == 404:
                    print(f"[이미지 없음] 전국도감 {pokedex_id}")
                    failed_count += 1
                    continue

                response.raise_for_status()

                # PNG 파일 저장
                save_path.write_bytes(response.content)
                success_count += 1

                print(
                    f"[다운로드 {pokedex_id}/{TOTAL_POKEMON}] "
                    f"{save_path.name}"
                )

            except requests.RequestException as error:
                print(f"[다운로드 실패] {pokedex_id}: {error}")
                failed_count += 1

    print("\n===== 다운로드 결과 =====")
    print(f"새로 다운로드: {success_count}")
    print(f"이미 존재함: {skipped_count}")
    print(f"실패 또는 이미지 없음: {failed_count}")
    print(f"저장 위치: {SAVE_DIR}")


if __name__ == "__main__":
    download_pokemon_images()


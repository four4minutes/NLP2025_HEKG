# scrape_multiple_pages.py

import os
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin
import hashlib
from scrape_to_json import scrape_to_json

def create_safe_filename(name):
    '''
    文字列をハッシュ化して安全なファイル名に変換する関数。
    - name : ハッシュ化したい文字列
    戻り値はハッシュ値(.json)を付与したファイル名となる。
    '''
    hash_object = hashlib.sha256(name.encode('utf-8'))
    return hash_object.hexdigest() + ".json"

def get_safe_filename(name):
    '''
    名前として使えない文字が含まれる場合、create_safe_filenameでハッシュに変換し、
    問題なければ "名前.json" のまま使用する関数。
    - name : ファイルとして使用予定の文字列
    戻り値は使用可能な安全なファイル名。
    '''
    try:
        # (1) テストファイルを作成して削除し、名前の有効性をチェック
        test_filename = f"{name}.test"
        with open(test_filename, 'w') as f:
            f.write("test")
        os.remove(test_filename)
        return f"{name}.json"
    except Exception:
        # (2) 名前に問題がある場合はハッシュで置き換える
        return create_safe_filename(name)

def scrape_multiple_pages(base_url, main_page_url, category_folder_path):
    '''
    指定されたメインページ(main_page_url)から下層ページのリンクを抽出し、
    各ページをスクレイピングしたJSONを保存してまとめる関数。
    - base_url : 相対パスを絶対URLに変換するためのベースURL
    - main_page_url : カテゴリ用ページのURL
    - category_folder_path : JSONファイルを保存するフォルダパス
    戻り値は 下層ページ名 -> 解析結果(JSONデータ) 形式のディクショナリ。
    '''
    try:
        # (1) メインページにリクエストを行い、パースする
        response = requests.get(main_page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')

        # (2) 下層ページのリンクを抽出
        links = soup.select('ul.list_all li a')
        print(f"Found {len(links)} sub-pages.")

        # (3) 結果を保存するディクショナリを初期化
        results = {}

        # (4) 各下層ページを巡回しながら処理
        for i, link in enumerate(links):
            page_name = link.get_text(strip=True)
            relative_url = link['href']
            print(f"[{i+1}/{len(links)}] Now processing sub page '{page_name}'...")

            # (5) URLを結合して絶対URLにする
            full_url = urljoin(base_url + "/", relative_url.lstrip("./"))

            # (6) 安全なファイル名を作成
            safe_filename = get_safe_filename(page_name)
            individual_json_file = os.path.join(category_folder_path, safe_filename)

            try:
                # (7) 下層ページのJSONを作成
                scrape_to_json(full_url, individual_json_file)

                # (8) 一時的に保存したJSONを読み込んでマージ
                with open(individual_json_file, 'r', encoding='utf-8') as f:
                    page_content = json.load(f)

                # (9) ページ名をキーにしてresultsに格納
                results[page_name] = page_content
                print(f"Sub page '{page_name}' is processed successfully.")
            except Exception as e:
                print(f"[ERROR] An error occurred while processing sub page '{page_name}': {e}")
                continue

        return results

    except Exception as e:
        print(f"[ERROR] Exception occurred in scrape_multiple_pages: {e}")
        return {}

# (メイン実行例)
# if __name__ == "__main__":
#     base_url = "https://www.shippai.org/fkd"
#     main_page_url = "https://www.shippai.org/fkd/lis/cat001.html"
#     category_folder_path = "some_path"
#     scrape_multiple_pages(base_url, main_page_url, category_folder_path)

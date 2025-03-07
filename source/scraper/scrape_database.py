# scrape_database.py

import os
import json  
import sys 
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import shutil
from scrape_multiple_pages import scrape_multiple_pages

def scrape_categories(main_page_url, base_url):
    '''
    メインページにアクセスし、カテゴリ一覧を取得してフォルダを作成しながら、
    各カテゴリの詳細を下層ページからスクレイピングし、最終的にJSONファイルとして保存する関数。
    - main_page_url : カテゴリ一覧が掲載されているメインページのURL
    - base_url : 相対リンクを絶対リンクに変換する際に用いるベースURL
    処理が完了すると、ルートフォルダにカテゴリ別のJSONファイルが生成される。
    '''
    try:
        # (1) メインページへリクエストし、HTMLを解析
        response = requests.get(main_page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')

        # (2) ルートフォルダ(失敗知識データベース)の絶対パスを作成
        root_folder_name = "失敗知識データベース"
        root_folder_path = os.path.abspath(root_folder_name)

        # (3) 既にフォルダが存在する場合は削除して再作成
        if os.path.exists(root_folder_path):
            print(f"Root folder '{root_folder_path}' already exists. Removing existing data...")
            shutil.rmtree(root_folder_path)
        os.makedirs(root_folder_path, exist_ok=True)

        # (4) tableタグ内のclass='list'を探し、各カテゴリリンクを抽出
        category_table = soup.find('table', class_='list')
        if not category_table:
            print("[ERROR] 'table.list' not found in the HTML structure.")
            return

        category_links = category_table.find_all('a', href=True)
        print(f"Found {len(category_links)} categories in total.")

        # (5) 各カテゴリ用フォルダを作成して、下層ページを処理
        for i, category in enumerate(category_links):
            category_name = category.get_text(strip=True)
            category_url = urljoin(base_url, category['href'].lstrip("./"))
            print(f"[{i+1}/{len(category_links)}] Now processing category '{category_name}'...")

            # (6) カテゴリフォルダの絶対パスを作成
            category_folder_path = os.path.join(root_folder_path, category_name)
            os.makedirs(category_folder_path, exist_ok=True)

            # (7) 下層ページをクローリング
            results = scrape_multiple_pages(base_url, category_url, category_folder_path)

            # (8) カテゴリごとの統合JSONファイルを生成
            category_json_path = os.path.join(root_folder_path, f"{category_name}.json")
            with open(category_json_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            
            print(f"Category '{category_name}' data has been saved to '{category_json_path}'.")

        print(f"All category data has been saved in '{root_folder_path}'.")

    except Exception as e:
        print(f"[ERROR] Exception occurred: {e}")
        sys.exit(f"[ERROR] Program terminated: {e}")


# (メイン実行)
if __name__ == "__main__":
    main_page_url = "https://www.shippai.org/fkd/index.php"  # メインページURL
    base_url = "https://www.shippai.org/fkd"                 # ベースURL

    scrape_categories(main_page_url, base_url)

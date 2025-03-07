# scrape_to_json.py

import requests
from bs4 import BeautifulSoup
import json

def scrape_to_json(url, output_file):
    '''
    指定されたURLに対してHTMLをパースし、特定の<table>や<tr>構造から
    key-value形式のデータを抽出してJSONに変換する関数。
    - url : スクレイピング対象となるページのURL
    - output_file : 生成したJSONを保存するファイルパス
    '''
    try:
        # (1) ウェブページをリクエストしてHTMLを解析
        response = requests.get(url)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')

        # (2) すべての<tr>タグを探し、データを格納する辞書を用意
        rows = soup.find_all('tr')
        result = {}
        print(f"Total <tr> tags found: {len(rows)}")

        for i, row in enumerate(rows):
            # (3) class='marginL' の<td>があれば、そこをキーとして取得
            header_cell = row.find('td', class_='marginL')
            if header_cell:
                key = header_cell.get_text(strip=True)
                data_cell = header_cell.find_next_sibling('td')
                rowspan = header_cell.get('rowspan')
                values = []

                # (4) "マルチメディアファイル" 項目を処理
                if rowspan and rowspan.isdigit() and key == "マルチメディアファイル":
                    rows_to_collect = int(rowspan) - 1

                    # (4-1) 現在の行から最初のデータを抽出
                    if data_cell:
                        link_tag = data_cell.find('a')
                        if link_tag:
                            link_text = link_tag.get_text(strip=True)
                            values.append(link_text)

                    # (4-2) 続く兄弟行から追加データを抽出
                    for offset in range(1, rows_to_collect + 1):
                        if i + offset < len(rows):
                            sibling_row = rows[i + offset]
                            data_cell = sibling_row.find('td', class_='marginL') or sibling_row.find('td')
                            if data_cell:
                                link_tag = data_cell.find('a')
                                if link_tag:
                                    link_text = link_tag.get_text(strip=True)
                                    values.append(link_text)

                    result[key] = values

                # (5) 「シナリオ」項目を処理
                elif key == "シナリオ" and data_cell:
                    scenario_table = data_cell.find('table')
                    scenario_data = {}

                    if scenario_table:
                        for scenario_row in scenario_table.find_all('tr'):
                            cells = scenario_row.find_all('td')
                            if len(cells) == 2:
                                sub_key = cells[0].get_text(strip=True)
                                sub_value = cells[1].get_text(strip=True)
                                sub_value_list = [item.strip() for item in sub_value.split("、")]
                                scenario_data[sub_key] = sub_value_list

                    result[key] = scenario_data

                # (6) その他の一般的な項目（<br>分割など）を処理
                elif key != "主シナリオ" and data_cell:
                    raw_content = data_cell.decode_contents()
                    if '<br' in raw_content:
                        split_values = [item.strip() for item in data_cell.get_text(separator='|').split('|')]
                        split_values = [value for value in split_values if value]
                        result[key] = split_values
                    else:
                        value_text = data_cell.get_text(strip=True)
                        result[key] = value_text

        # (7) 解析結果をJSONファイルに保存
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        print(f"JSON file saved successfully: {output_file}")

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error occurred while requesting web page: {e}")
    except Exception as e:
        print(f"[ERROR] Exception in scrape_to_json: {e}")


# (メイン実行例)
# if __name__ == "__main__":
# url = "https://www.shippai.org/fkd/cf/CZ0200802.html"
# output_file = "output.json"
# scrape_to_json(url, output_file)

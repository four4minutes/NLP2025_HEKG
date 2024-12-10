import requests
from bs4 import BeautifulSoup # type: ignore
import json


def scrape_to_json(url, output_file):
    try:
        # 웹페이지 요청 및 HTML 소스 가져오기
        response = requests.get(url)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')

        # 모든 <tr> 태그 가져오기
        rows = soup.find_all('tr')
        result = {}

        print("총 <tr> 태그 개수:", len(rows))  # 디버깅용 출력

        for i, row in enumerate(rows):
            header_cell = row.find('td', class_='marginL')  # 항목 이름 셀 찾기
            if header_cell:
                key = header_cell.get_text(strip=True)  # 항목 이름
                data_cell = header_cell.find_next_sibling('td')  # 데이터 셀 찾기
                rowspan = header_cell.get('rowspan')  # rowspan 값 확인
                values = []

                # "マルチメディアファイル" 항목 처리
                if rowspan and rowspan.isdigit() and key == "マルチメディアファイル":
                    #print(f"'{key}' 항목 처리 시작")  # 디버깅 메시지
                    rows_to_collect = int(rowspan) - 1  # rowspan 값에서 현재 행 제외

                    # 1. 현재 행에서 첫 번째 데이터 추출
                    if data_cell:
                        link_tag = data_cell.find('a')  # <a> 태그 찾기
                        if link_tag:
                            link_text = link_tag.get_text(strip=True)
                            # print("추출한 내용 (현재 행):", link_text)  # 디버깅용 출력
                            values.append(link_text)

                    # 2. 이후 형제 행에서 추가 데이터 추출
                    for offset in range(1, rows_to_collect + 1):
                        if i + offset < len(rows):
                            sibling_row = rows[i + offset]  # 다음 <tr> 가져오기
                            # print(f"현재 처리 중인 <tr>:\n{sibling_row.prettify()}")  # 디버깅용 출력
                            data_cell = sibling_row.find('td', class_='marginL') or sibling_row.find('td')
                            if data_cell:
                                link_tag = data_cell.find('a')  # <a> 태그 찾기
                                if link_tag:
                                    link_text = link_tag.get_text(strip=True)
                                    # print("추출한 내용:", link_text)  # 디버깅용 출력
                                    values.append(link_text)

                    # 결과 저장
                    # print(f"{key} 항목의 최종 값:", values)  # 디버깅용 출력
                    result[key] = values

                # "シナリオ" 항목 처리
                elif key == "シナリオ" and data_cell:
                    #print(f"'{key}' 항목 처리 시작")  # 디버깅 메시지
                    scenario_table = data_cell.find('table')  # <table> 태그 탐색
                    scenario_data = {}

                    if scenario_table:
                        for scenario_row in scenario_table.find_all('tr'):
                            cells = scenario_row.find_all('td')
                            if len(cells) == 2:  # 항목-내용 구조 확인
                                sub_key = cells[0].get_text(strip=True)  # 표의 첫 번째 셀
                                sub_value = cells[1].get_text(strip=True)  # 표의 두 번째 셀

                                # 콤마로 구분된 값을 리스트로 변환
                                sub_value_list = [item.strip() for item in sub_value.split("、")]
                                # print(f"추출한 시나리오 데이터: {sub_key} -> {sub_value_list}")  # 디버깅 출력
                                scenario_data[sub_key] = sub_value_list

                    result[key] = scenario_data

                # 일반적인 항목 처리 (중복 방지)
                elif key != "主シナリオ" and data_cell:
                    # <br>로 분리하여 리스트로 저장
                    raw_content = data_cell.decode_contents()  # 태그 포함 원본 가져오기
                    if '<br' in raw_content:
                        split_values = [item.strip() for item in data_cell.get_text(separator='|').split('|')]
                        split_values = [value for value in split_values if value] # 빈 문자열 제거
                        #print(f"'{key}' 항목: <br> 처리된 값 -> {split_values}")  # 디버깅 메시지
                        result[key] = split_values
                    else:
                        value_text = data_cell.get_text(strip=True)
                        result[key] = value_text

        # JSON 파일 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        print(f"JSONファイルが正常に保存されました: {output_file}")

    except requests.exceptions.RequestException as e:
        print(f"ウェブページのリクエスト中にエラーが発生しました: {e}")
    except Exception as e:
        print(f"エラーが発生しました: {e}")


# 사용 예시
#url = "https://www.shippai.org/fkd/cf/CZ0200802.html"  # 크롤링할 URL
#output_file = "output.json"  # 저장할 JSON 파일 경로
#scrape_to_json(url, output_file)
import os
import json  
import sys 
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import shutil
from scrape_multiple_pages import scrape_multiple_pages

# scrape_categories 함수 정의 그대로
def scrape_categories(main_page_url, base_url):
    try:
        # 메인 페이지 요청 및 HTML 파싱
        response = requests.get(main_page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')

        # 최상위 폴더 생성 (절대 경로 사용)
        root_folder_name = "失敗知識データベース"
        root_folder_path = os.path.abspath(root_folder_name)  # 절대 경로로 설정
        if os.path.exists(root_folder_path):
            print(f"최상위 폴더 '{root_folder_path}'가 이미 존재합니다. 기존 데이터를 삭제합니다...")
            shutil.rmtree(root_folder_path)
        os.makedirs(root_folder_path, exist_ok=True)

        # table.list 내부의 링크 추출
        category_table = soup.find('table', class_='list')
        if not category_table:
            print("'table.list' 테이블을 찾을 수 없습니다. HTML 구조를 다시 확인하세요.")
            return

        category_links = category_table.find_all('a', href=True)
        print(f"총 {len(category_links)}개의 카테고리를 찾았습니다.")

        for i, category in enumerate(category_links):
            category_name = category.get_text(strip=True)
            category_url = urljoin(base_url, category['href'].lstrip("./"))

            print(f"[{i+1}/{len(category_links)}] 카테고리 '{category_name}'를 처리 중...")
            
            # 카테고리 폴더 생성 (절대 경로 사용)
            category_folder_path = os.path.join(root_folder_path, category_name)
            os.makedirs(category_folder_path, exist_ok=True)

            # 카테고리별 하위 데이터를 가져와 저장
            results = scrape_multiple_pages(base_url, category_url, category_folder_path)

            # 카테고리별 통합 JSON 파일 생성
            category_json_path = os.path.join(root_folder_path, f"{category_name}.json")
            with open(category_json_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            
            print(f"카테고리 '{category_name}'의 데이터가 통합되어 '{category_json_path}'에 저장되었습니다.")

        print(f"모든 카테고리 데이터가 '{root_folder_path}'에 저장되었습니다.")

    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        sys.exit(f"프로그램을 종료합니다: {e}")


# 사용 예시
if __name__ == "__main__":
    main_page_url = "https://www.shippai.org/fkd/index.php"  # 메인 페이지 URL
    base_url = "https://www.shippai.org/fkd"  # 베이스 URL

    scrape_categories(main_page_url, base_url)
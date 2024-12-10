import os
import shutil
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin
import hashlib
from scrape_to_json import scrape_to_json
import sys


def create_safe_filename(name):
    """긴 파일 이름을 안전한 해시 값으로 변환"""
    hash_object = hashlib.sha256(name.encode('utf-8'))
    return hash_object.hexdigest() + ".json"


def get_safe_filename(name):
    """파일 이름이 유효하면 그대로 사용하고, 유효하지 않으면 해시로 변환"""
    try:
        # 테스트로 파일을 생성했다가 삭제하여 유효성을 확인
        test_filename = f"{name}.test"
        with open(test_filename, 'w') as f:
            f.write("test")
        os.remove(test_filename)
        return f"{name}.json"
    except Exception:
        # 파일 이름이 유효하지 않으면 해시로 대체
        return create_safe_filename(name)


def scrape_multiple_pages(base_url, main_page_url, category_folder_path):
    try:
        # 메인 페이지 요청 및 HTML 파싱
        response = requests.get(main_page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')  # 인코딩 명시

        # 하위 페이지 링크 추출
        links = soup.select('ul.list_all li a')
        print(f"총 {len(links)}개의 하위 페이지를 찾았습니다.")

        # 결과를 저장할 딕셔너리 초기화
        results = {}

        # 각 하위 페이지 크롤링
        for i, link in enumerate(links):
            page_name = link.get_text(strip=True)
            relative_url = link['href']
            print(f"[{i+1}/{len(links)}] '{page_name}' 페이지를 처리 중...")

            # URL 결합: base_url과 상대 URL을 결합
            full_url = urljoin(base_url + "/", relative_url.lstrip("./"))

            # 안전한 파일 이름 생성
            safe_filename = get_safe_filename(page_name)
            individual_json_file = os.path.join(category_folder_path, safe_filename)

            try:
                # 하위 페이지 JSON 저장
                scrape_to_json(full_url, individual_json_file)

                # 임시 JSON 파일 로드 및 결과 병합
                with open(individual_json_file, 'r', encoding='utf-8') as f:
                    page_content = json.load(f)

                # 원래 페이지 이름과 데이터 저장
                results[page_name] = page_content
                print(f"'{page_name}' 페이지가 처리되었습니다.")
            except Exception as e:
                print(f"하위 페이지 처리 중 오류가 발생했습니다: {e}")
                continue

        return results

    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        return {}

# 사용 예시
#if __name__ == "__main__":
#    base_url = "https://www.shippai.org/fkd"  # 베이스 URL
#    main_page_url = "https://www.shippai.org/fkd/lis/cat001.html"  # 메인 페이지 URL
#            category_folder_path = os.path.join(root_folder_path, category_name)
#            os.makedirs(category_folder_path, exist_ok=True)
#
#    scrape_multiple_pages(base_url, category_url, category_folder_path)
# main.py

import re
import json

# ----------- 기존 import 유지 -----------
from source.document_parsing.logger import initialize_logger, log_to_file, log_and_print_final_results
from source.document_parsing.node_maker import (
    get_category, 
    get_entity_structure, 
    get_predicate_structure
)
from source.document_parsing.edge_maker import get_edge

# ----- JSON 처리 로직을 옮긴 모듈 임포트 -----
from json_processor import process_json

# 로그 초기화 (프로그램 실행 시 한 번만 호출)
initialize_logger()

# JSON 데이터 로드 (동일)
with open('test.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# JSON 전체 처리 시작
process_json(data)

# 최종 결과 배열을 logger.py로 옮긴 log_and_print_final_results에서 출력
category = get_category()
entity_structure = get_entity_structure()
predicate_structure = get_predicate_structure()
edge = get_edge()

log_and_print_final_results(category, entity_structure, predicate_structure, edge)
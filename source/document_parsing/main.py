# main.py

import json
from source.document_parsing.logger import (
    initialize_logger, 
    log_and_print_final_results,
    produce_similarity_report
)
from source.document_parsing.node_maker import (
    get_category,
    get_entity_structure,
    get_predicate_structure
)
from source.document_parsing.edge_maker import get_edge
from json_processor import process_json

# 1) 로그 초기화
initialize_logger()

# 2) JSON 데이터 로드
with open('test.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# 3) JSON 전체 처리
process_json(data)

# 4) 최종 결과 출력 (Category, Entity, Predicate, Edge)
category = get_category()
entity_structure = get_entity_structure()
predicate_structure = get_predicate_structure()
edge = get_edge()

log_and_print_final_results(category, entity_structure, predicate_structure, edge)

# 5) 내림차순 유사도 보고(참고자료)
produce_similarity_report(entity_structure, predicate_structure)
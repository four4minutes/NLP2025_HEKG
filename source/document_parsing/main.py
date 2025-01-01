# main.py

import json

from source.document_parsing.logger import initialize_logger, log_to_file, log_and_print_final_results
from source.document_parsing.node_maker import (
    get_category, 
    get_entity_structure, 
    get_predicate_structure
)
from source.document_parsing.edge_maker import get_edge

# JSON 처리
from json_processor import process_json

# 예: similarity_calculation 모듈 (코사인 유사도 검사)
from source.document_parsing.similarity_calculation import (
    run_similarity_check,
    create_equivalent_edges
)

# 1) 로그 초기화
initialize_logger()

# 2) JSON 데이터 로드
with open('test.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# 3) JSON 전체 처리
process_json(data)

# 4) 유사도 검사 (코사인 유사도) 
# -> 모든 노드가 생성된 시점
category = get_category()
entity_structure = get_entity_structure()
predicate_structure = get_predicate_structure()

# run_similarity_check: 
run_similarity_check(entity_structure, predicate_structure)

# create_equivalent_edges:
create_equivalent_edges()

################################
# 5) 최종 결과 출력
################################
edge = get_edge()
log_and_print_final_results(category, entity_structure, predicate_structure, edge)
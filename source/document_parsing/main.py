# main.py

import json
import os
from source.document_parsing.logger import initialize_logger
from source.document_parsing.node_maker import (
    get_category_structure,
    get_entity_structure,
    get_predicate_structure
)
from source.document_parsing.edge_maker import get_edge
from json_processor import process_json
from csv_exporter import export_to_csv

# 1) 로그 초기화
initialize_logger()

# 2) JSON 데이터 로드
input_filename = "test.json"
filename_only = os.path.splitext(input_filename)[0]
with open(input_filename, 'r', encoding='utf-8') as file:
    data = json.load(file)

# 3) JSON 전체 처리
process_json(data, filename_only)

# 4) 처리 완료 후, 최종적으로 CSV로 내보내기
category_list = get_category_structure()
entity_list = get_entity_structure()
predicate_list = get_predicate_structure()
edge_list = get_edge()
export_to_csv(category_list, entity_list, predicate_list, edge_list, "results")
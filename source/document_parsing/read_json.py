import re
import json
from source.document_parsing.time_and_place_extraction import extract_time_and_place, remove_expressions
from source.document_parsing.predicate_extraction import extract_predicates, extract_predicate_argument_structure
from source.document_parsing.residue_extraction import process_sentence_with_residue_removal
from source.document_parsing.logger import initialize_logger, log_to_file

# 로그 초기화 (프로그램 실행 시 한 번만 호출)
initialize_logger()

# JSON 데이터 로드
with open('test.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

def is_heading(item: str) -> bool:
    item_normalized = re.sub(r'[０-９]', lambda x: chr(ord(x.group(0)) - 0xFEE0), item)
    return bool(re.match(r'^\d+\.|^[・（）注]+', item_normalized))

# 전역변수 및 배열 초기화
index_number_node = 1  # 전역 인덱스 변수
category = []  # 카테고리 정보를 저장할 배열
entity_structure = []  # 엔티티 정보를 저장할 배열
predicate_structure = []  # 술어항 구조 정보를 저장할 배열

def append_category_info(key):
    global index_number_node
    category_info = {
        'index': index_number_node,
        'hierarchical_level': 0,
        'category_type': '項目名',
        'category_title': key
    }
    category.append(category_info)
    index_number_node += 1

def append_entity_info(entity_value):
    global index_number_node
    if isinstance(entity_value, list):
        entity_value = entity_value[0]  # 리스트일 경우 첫 번째 요소만 추출
    entity_info = {
        'index': index_number_node,
        'hierarchical_level': 0,
        'entity': entity_value
    }
    entity_structure.append(entity_info)
    index_number_node += 1

def append_predicate_structure(predicate_argument_structure):
    global index_number_node
    for structure in predicate_argument_structure:
        predicate_match = re.match(r'(.*?)(\(述語\))', structure)
        agent_match = re.search(r'(\S+?\(ガ格\))', structure)
        modifier_match = re.search(r'(\S+?\(修飾\))', structure)
        arguments = re.findall(r'(\S+?\((?!ガ格|述語|修飾)\S+?\))', structure)  # 괄호까지 포함

        predicate_info = {
            'index': index_number_node,
            'hierarchical_level': 0,
            'agent_argument': agent_match.group(0) if agent_match else "",
            'predicate': predicate_match.group(0) if predicate_match else "",
            'argument': arguments,
            'modifier': modifier_match.group(0) if modifier_match else ""
        }
        predicate_structure.append(predicate_info)
        index_number_node += 1

def process_item(key, value):
    if key:
        log_to_file(f"카테고리 : {key}")
        append_category_info(key)

    if isinstance(value, list):
        for sub_item in value:
            process_item("", sub_item)

    elif isinstance(value, dict):
        for sub_key, sub_value in value.items():
            process_item(sub_key, sub_value)

    elif isinstance(value, str):
        if is_heading(value):
            heading_match = re.match(r'^(?P<heading>\d+\.|[・（）注]+)(?P<content>.*)', value)
            if heading_match:
                heading = heading_match.group("heading").strip()
                content = heading_match.group("content").strip()
                if "。" in content:
                    log_to_file(f"엔티티: {heading}")
                    append_entity_info(heading)
                    process_sentence(content)
                else:
                    log_to_file(f"엔티티: {heading}{content}")
                    append_entity_info(f"{heading}{content}")
        else:
            if "。" in value:
                process_sentence(value)
            else:
                log_to_file(f"엔티티: {value}")
                append_entity_info(value)

def process_sentence(sentence: str):
    log_to_file(f"\n문장: {sentence}")
    time_and_place = extract_time_and_place(sentence + "。")

    if time_and_place['time']:
        log_to_file(f"추출된 시간 표현: {time_and_place['time']}")
        append_entity_info(time_and_place['time'])

    if time_and_place['place']:
        log_to_file(f"추출된 장소 표현: {time_and_place['place']}")
        append_entity_info(time_and_place['place'])

    expressions_to_remove = time_and_place['time'] + time_and_place['place']
    modified_sentence = remove_expressions(sentence, expressions_to_remove) if expressions_to_remove else sentence
    if expressions_to_remove:
        log_to_file(f"시간 및 장소 표현 제거 후: {modified_sentence}")

    # extract_predicates에서 두 리스트 반환
    event_predicates, entity_predicates = extract_predicates(modified_sentence + "。")
    log_to_file(f"----------------------------\n추출된 사상 술어: {event_predicates if event_predicates else '추출되지 않음'}")
    log_to_file(f"추출된 개념 술어: {entity_predicates if entity_predicates else '추출되지 않음'}")

    # 두 리스트를 extract_predicate_argument_structure에 넘김
    predicate_argument_structures, entities = extract_predicate_argument_structure(modified_sentence + "。", event_predicates, entity_predicates)
    
    # 술어항 구조 출력
    log_to_file("------추출된 述語項構造------")
    for i, structure in enumerate(predicate_argument_structures, 1):
        log_to_file(f"({i}) {structure}")

    # 술어항 구조를 predicate_structure 리스트에 추가
    append_predicate_structure(predicate_argument_structures)

    # 엔티티 출력 및 처리
    log_to_file("--------추출된 엔티티--------")
    for i, entity in enumerate(entities, 1):
        log_to_file(f"({i}) {entity}")

        # 엔티티를 entity_structure 리스트에 추가
        append_entity_info(entity)

    log_to_file("----------------------------")

    if predicate_argument_structures:
        final_sentence = process_sentence_with_residue_removal(modified_sentence, predicate_argument_structures)
        log_to_file(f"술어항 구조 표현 제거 후: {final_sentence}")
    else:
        log_to_file("[DEBUG] 술어항 구조가 생성되지 않았습니다. 수정 작업을 생략합니다.")

def process_json(data):
    for key, value in data.items():
        process_item(key, value)

process_json(data)

def log_and_print_final_results():
    log_to_file("\n=== Category 배열 ===")
    for item in category:
        log_to_file(str(item))

    log_to_file("\n=== Entity Structure 배열 ===")
    for item in entity_structure:
        log_to_file(str(item))

    log_to_file("\n=== Predicate Structure 배열 ===")
    for item in predicate_structure:
        log_to_file(str(item))

log_and_print_final_results()
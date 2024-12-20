import re
import json
from source.document_parsing.time_and_place_extraction import extract_time_and_place
from source.document_parsing.predicate_extraction import extract_predicates, extract_entity_and_predicate_structures
from source.document_parsing.residue_extraction import process_sentence_with_residue_removal
from source.document_parsing.logger import initialize_logger, log_to_file, log_and_print_final_results
from node_maker import append_category_info, append_entity_info, append_predicate_structure, get_category, get_entity_structure, get_predicate_structure

# 로그 초기화 (프로그램 실행 시 한 번만 호출)
initialize_logger()

# JSON 데이터 로드
with open('test.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

def is_heading(item: str) -> bool:
    item_normalized = re.sub(r'[０-９]', lambda x: chr(ord(x.group(0)) - 0xFEE0), item)
    return bool(re.match(r'^\d+\.|^[・（）注]+', item_normalized))

def process_sentence(sentence: str):
    log_to_file(f"\n문장: {sentence}")
    time_and_place = extract_time_and_place(sentence + "。")

    if time_and_place['time']:
        log_to_file(f"추출된 시간 표현: {time_and_place['time']}")
        for t_expr in time_and_place['time']:
            append_entity_info(t_expr)

    if time_and_place['place']:
        log_to_file(f"추출된 장소 표현: {time_and_place['place']}")
        for p_expr in time_and_place['place']:
            append_entity_info(p_expr)

    # extract_predicates에서 두 리스트 반환
    event_predicates, entity_predicates = extract_predicates(sentence)
    log_to_file(f"----------------------------\n추출된 사상 술어: {event_predicates if event_predicates else '추출되지 않음'}")
    log_to_file(f"추출된 개념 술어: {entity_predicates if entity_predicates else '추출되지 않음'}")

    # 두 리스트를 extract_entity_and_predicate_structures에 넘김
    predicate_argument_structures, entities = extract_entity_and_predicate_structures(sentence, event_predicates, entity_predicates, time_and_place['time'], time_and_place['place'])
    
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
        append_entity_info(entity)

    log_to_file("----------------------------")

    if predicate_argument_structures:
        final_sentence = process_sentence_with_residue_removal(sentence, predicate_argument_structures)
        log_to_file(f"술어항 구조 표현 제거 후: {final_sentence}")
    else:
        log_to_file("[DEBUG] 술어항 구조가 생성되지 않았습니다. 수정 작업을 생략합니다.")

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

def process_json(data):
    for key, value in data.items():
        process_item(key, value)

process_json(data)

# 최종 결과 배열을 logger.py로 옮긴 log_and_print_final_results에서 출력
category = get_category()
entity_structure = get_entity_structure()
predicate_structure = get_predicate_structure()

log_and_print_final_results(category, entity_structure, predicate_structure)
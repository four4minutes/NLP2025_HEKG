import re
import json
from source.document_parsing.time_and_place_extraction import extract_time_and_place, remove_expressions
from source.document_parsing.predicate_extraction import extract_predicates, extract_predicate_argument_structure
from source.document_parsing.residue_extraction import process_sentence_with_residue_removal

# JSON 데이터 로드
with open('test.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

def is_heading(item: str) -> bool:
    """
    문자열이 항목(특수 문자나 숫자로 시작)인지 판단.
    """
    # 전각 숫자(全角数字)와 반각 숫자(半角数字)를 모두 처리
    item_normalized = re.sub(r'[０-９]', lambda x: chr(ord(x.group(0)) - 0xFEE0), item)
    return bool(re.match(r'^\d+\.|^[・（）注]+', item_normalized))

def process_item(key, value):
    """
    JSON 값(value)을 처리하여 출력.
    """
    if key:
        print(f"카테고리 : {key}")

    if isinstance(value, list):
        for sub_item in value:
            process_item("", sub_item)

    elif isinstance(value, dict):
        for sub_key, sub_value in value.items():
            process_item(sub_key, sub_value)

    elif isinstance(value, str):
        if is_heading(value):  # 항목 판단
            heading_match = re.match(r'^(?P<heading>\d+\.|[・（）注]+)(?P<content>.*)', value)
            if heading_match:
                heading = heading_match.group("heading").strip()
                content = heading_match.group("content").strip()
                if "。" in content:  # 문장 처리
                    print(f"엔티티: {heading}")
                    process_sentence(content)
                else:  # 명사구 처리
                    print(f"엔티티: {heading}{content}")
        else:  # 항목이 아닌 경우
            if "。" in value:  # 문장 처리
                process_sentence(value)
            else:  # 명사구 처리
                print(f"엔티티: {value}")

def process_sentence(sentence: str):
    """
    문장을 1단계에서 6단계까지 처리.
    """
    print("\n문장:", sentence)
    
    # 1단계: 시간 및 장소 표현 추출
    time_and_place = extract_time_and_place(sentence + "。")
    if time_and_place['time']:
        print(f"추출된 시간 표현: {time_and_place['time']}")
    if time_and_place['place']:
        print(f"추출된 장소 표현: {time_and_place['place']}")

    # 2단계: 시간 및 장소 표현 제거
    expressions_to_remove = time_and_place['time'] + time_and_place['place']
    modified_sentence = remove_expressions(sentence, expressions_to_remove) if expressions_to_remove else sentence
    if expressions_to_remove:
        print(f"시간 및 장소 표현 제거 후: {modified_sentence}")
    
    # 3단계: 술어 추출
    predicates = extract_predicates(modified_sentence + "。")
    print("---------------------------")
    print(f"추출된 술어: {predicates if predicates else '추출되지 않음'}")  # 빈 리스트 처리

    # 4단계: 述語項構造 생성
    predicate_argument_structures = extract_predicate_argument_structure(modified_sentence + "。", predicates)
    print("-----추출된 述語項構造-----")
    for i, structure in enumerate(predicate_argument_structures, 1):  # 번호 추가
        print(f"({i}) {structure}")
    print("---------------------------")
    
    # 5단계: 술어항 구조 표현 제거
    if predicate_argument_structures:
        final_sentence = process_sentence_with_residue_removal(modified_sentence, predicate_argument_structures)
        print(f"술어항 구조 표현 제거 후: {final_sentence}")
    else:
        print("[DEBUG] 술어항 구조가 생성되지 않았습니다. 수정 작업을 생략합니다.")

    # 6단계: 인과관계 추출
    """
    causal_relationships = process_sentence(final_sentence)
    if causal_relationships["causal_cue_present"]:
        if causal_relationships["causal_relationships"]:
            print("-----추출된 인과관계-----")
            for i, relationship in enumerate(causal_relationships["causal_relationships"], 1):
                print(f"({i}) 手がかり 표현: {relationship['cue']}")
                print(f"    원인: {relationship['cause']}")
                print(f"    결과: {relationship['effect']}")
        else:
            print(f"手がかり 표현이 인식되었지만, 인과관계가 추출되지 않았습니다: {causal_relationships['detected_causal_cues']}")
    """

def process_json(data):
    """
    JSON 데이터 순회하며 데이터를 처리.
    """
    for key, value in data.items():
        process_item(key, value)

# JSON 데이터 처리 실행
process_json(data)
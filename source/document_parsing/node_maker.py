# node_maker.py
# 노드(카테고리, 엔티티, 술어항 구조) 관리를 담당하는 모듈

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
    current_index = index_number_node
    index_number_node += 1

    return current_index

def append_entity_info(entity_value):
    global index_number_node
    if isinstance(entity_value, list):
        entity_value = entity_value[0]  # 리스트일 경우 첫 번째 요소만 사용
    entity_info = {
        'index': index_number_node,
        'hierarchical_level': 0,
        'entity': entity_value
    }
    entity_structure.append(entity_info)
    current_index = index_number_node
    index_number_node += 1

    return current_index

def append_predicate_structure(predicate_argument_structures):
    global index_number_node
    import re

    created_node_indexes = []  # 생성된 술어항 노드들의 인덱스 모음

    for structure in predicate_argument_structures:
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
        created_node_indexes.append(index_number_node)
        index_number_node += 1

    return created_node_indexes

def get_category():
    return category

def get_entity_structure():
    return entity_structure

def get_predicate_structure():
    return predicate_structure

def get_node_content_by_index(node_index: int):
    """
    node_index에 해당하는 노드(category/entity/predicate_structure)를 찾아
    사람이 알아보기 쉬운 문자열을 리턴한다.
    """
    # 1) 카테고리에서 검색
    for cat in category:
        if cat["index"] == node_index:
            # 예: "事例名称" (category_title)
            return cat.get("category_title", f"category_idx:{node_index}")

    # 2) 엔티티에서 검색
    for ent in entity_structure:
        if ent["index"] == node_index:
            # 예: "エキスポランド　ジェットコースター事故"
            return ent.get("entity", f"entity_idx:{node_index}")

    # 3) 술어항 구조에서 검색
    for pred in predicate_structure:
        if pred["index"] == node_index:
            # 예: "脱輪し(述語)"
            return pred.get("predicate", f"predicate_idx:{node_index}")

    # 그래도 못 찾으면
    return f"unknown_idx:{node_index}"
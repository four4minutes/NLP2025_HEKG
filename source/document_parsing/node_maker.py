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
    index_number_node += 1

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
    index_number_node += 1

def append_predicate_structure(predicate_argument_structures):
    global index_number_node
    import re
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
        index_number_node += 1

def get_category():
    return category

def get_entity_structure():
    return entity_structure

def get_predicate_structure():
    return predicate_structure
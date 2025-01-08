# time_evolution_extraction.py

from source.document_parsing.logger import log_to_file
from source.document_parsing.edge_maker import append_edge_info

def calculate_event_evolution_relationship(entity_nodes, predicate_nodes,doc_created_edge_indexes):
    """
    항목(레벨=1)이 마무리되는 시점에, 그 항목 내 엔티티/술어 노드를 받아
    원하는 이벤트 진화 관계를 부여한다.
    
    아래 예시는 'predicate_nodes'의 index 오름차순으로 
    next_TimeStamp 관계를 선형 연결하는 로직입니다.
    
    entity_nodes는 추후 다른 관계(예: entity vs. predicate 연결) 등에 활용할 수 있습니다.
    """
    log_to_file("----------------------------")

    # 1) predicate_nodes를 index 오름차순 정렬
    sorted_predicates = sorted(predicate_nodes, key=lambda x: x["index"])
    
    # 2) 선형으로 next_TimeStamp 연결
    for i in range(len(sorted_predicates) - 1):
        from_idx = sorted_predicates[i]["index"]
        to_idx   = sorted_predicates[i+1]["index"]
        append_edge_info("next_TimeStamp", from_idx, to_idx,doc_created_edge_indexes)

    log_to_file("----------------------------")
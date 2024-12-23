# edge_maker.py
# 엣지 관리를 담당하는 모듈
from source.document_parsing.node_maker import get_node_content_by_index
from source.document_parsing.logger import log_to_file

index_number_edge = 1  # 전역 인덱스 변수
edge = []              # 모든 엣지를 저장할 리스트

def append_edge_info(edge_type, from_node_index, to_node_index):
    """
    새로운 엣지를 edge 리스트에 추가하고, index_number_edge를 1씩 증가시킵니다.
    
    :param edge_type: 엣지 관계명 (str)
    :param from_node_index: 엣지 출발 노드의 인덱스 번호 (int)
    :param to_node_index: 엣지 도착 노드의 인덱스 번호 (int)
    """
    global index_number_edge
    edge_info = {
        'index': index_number_edge,
        'type': edge_type,
        'from': from_node_index,
        'to': to_node_index
    }
    edge.append(edge_info)
    
    from_content = get_node_content_by_index(from_node_index)
    to_content = get_node_content_by_index(to_node_index)
    # 예: [事例概要] --(sub)--> [脱輪し(述語)]
    log_to_file(f"[{from_content}] --({edge_type})--> [{to_content}]")

    index_number_edge += 1
    index_number_edge += 1

def get_edge():
    """
    edge 리스트를 반환합니다.
    """
    return edge

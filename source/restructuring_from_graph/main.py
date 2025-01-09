# main.py

import os
from collections import defaultdict

# result_file_parser 모듈 import
from result_file_parser import (
    category_structure, 
    entity_structure, 
    predicate_structure, 
    edges,
    find, 
    union,
    load_category_structure, 
    load_entity_structure, 
    load_predicate_structure, 
    load_edges
)

# text_utils 모듈 import
from text_utils import predicate_to_text

def main():
    base_dir = "results/archive"
    
    # 1) CSV 파일 경로 설정
    category_path  = os.path.join(base_dir, "category_structure_node.csv")
    entity_path    = os.path.join(base_dir, "entity_structure_node.csv")
    predicate_path = os.path.join(base_dir, "predicate_structure_node.csv")
    edge_path      = os.path.join(base_dir, "edge.csv")

    # 2) CSV 파일 로드
    #    (result_file_parser의 전역 구조에 저장)
    global category_structure, entity_structure, predicate_structure, edges
    category_structure   = load_category_structure(category_path)
    entity_structure     = load_entity_structure(entity_path)
    predicate_structure  = load_predicate_structure(predicate_path)
    edges                = load_edges(edge_path)

    # 3) 계층(level)이 0인 노드만 필터
    entity_0 = {k:v for k,v in entity_structure.items() if v['level'] == 0}
    predicate_0 = {k:v for k,v in predicate_structure.items() if v['level'] == 0}

    # 4) Union-Find 초기화
    node_indices = list(entity_0.keys()) + list(predicate_0.keys())
    node_indices = list(set(node_indices))  # 중복 제거

    parent = {}
    rank = {}
    for idx in node_indices:
        parent[idx] = idx
        rank[idx] = 0

    # 'equivalent' 엣지로 묶기
    for e in edges:
        if e['type'] == 'equivalent':
            from_idx = e['from']
            to_idx   = e['to']
            if from_idx in parent and to_idx in parent:
                union(parent, rank, from_idx, to_idx)

    # 대표 갱신
    for idx in node_indices:
        find(parent, idx)

    # 그룹화
    groups = defaultdict(list)
    for idx in node_indices:
        root = parent[idx]
        groups[root].append(idx)

    # 5) 그룹별로 출력
    #    - 그룹 내부 노드들은 equivalent로 묶임
    #    - 각 노드가 predicate 노드라면 predicate_to_text 함수로 문자열 변환
    #    - entity 노드라면 entity 값 그대로
    #    - 그리고 info_SpecificTime, info_SpecificPlace, explain_details 엣지 표시
    used_edges = set(["info_SpecificTime", "info_SpecificPlace", "explain_details"])

    group_count = 0
    for root_idx, node_list in groups.items():
        group_count += 1
        print(f"({group_count})")
        
        # (A) 같은 그룹의 노드들 출력
        for node_id in node_list:
            if node_id in entity_0:
                text = entity_0[node_id]['entity']
            elif node_id in predicate_0:
                text = predicate_to_text(predicate_0[node_id])
            else:
                text = f"(Node {node_id})"
            print(f"  {text}")

        # (B) 그룹 내 노드에서 특정 엣지(used_edges)로 연결된 것 표시
        for node_id in node_list:
            for e in edges:
                if e['from'] == node_id and e['type'] in used_edges:
                    to_id = e['to']
                    # 만약 to_id가 같은 그룹 내라면 'equivalent'로 이미 묶인 노드일 수도
                    # 일단 예시에서는 그룹 밖 노드만 별도로 표시
                    if to_id not in node_list:
                        label = f"[{e['type']}]"
                        if to_id in entity_0:
                            text = entity_0[to_id]['entity']
                        elif to_id in predicate_0:
                            text = predicate_to_text(predicate_0[to_id])
                        else:
                            text = f"(Node {to_id})"
                        print(f"  {label} {text}")

        print()

if __name__ == "__main__":
    main()

# json_processor.py

from source.document_parsing.logger import (
    log_to_file,
    produce_similarity_report,
    log_and_print_final_results
)
from source.document_parsing.node_maker import (
    append_category_info,
    append_entity_info,
    get_entity_structure,
    get_predicate_structure,
    get_category_structure
)
from source.document_parsing.edge_maker import (
    append_edge_info,
    get_edge
)
from source.document_parsing.sentence_parser import process_sentence
from source.document_parsing.similarity_based_equivalent_extraction import (
    run_similarity_check,
    create_equivalent_edges
)
from source.document_parsing.text_utils import is_heading_start, split_heading_and_rest


def process_item(key, value, parent_category_index=None, hierarchical_level=0, doc_created_node_indexes=None):
    """
    기존 main.py에서 작성되었던 process_item 함수 그대로 옮김.
    - key 있으면 => 카테고리
    - dict, list, str 분기
    - heading 판별, split_heading_and_rest
    - "。" 포함시 문장 해석 -> process_sentence
    - sub 관계 연결
    """
    current_category_index = parent_category_index

    # 1) key 있으면 => 카테고리
    if key:
        log_to_file(f"[category(level={hierarchical_level})] {key}")
        current_category_index = append_category_info(
            key,
            level=hierarchical_level,
            cat_type='項目名',
            doc_created_node_indexes=doc_created_node_indexes
        )
        if parent_category_index is not None and parent_category_index != current_category_index:
            append_edge_info("sub", parent_category_index, current_category_index, doc_created_node_indexes)

    # 2) 타입 분기
    if isinstance(value, dict):
        for sub_key, sub_val in value.items():
            process_item(sub_key, sub_val, current_category_index, hierarchical_level, doc_created_node_indexes)
        return

    if isinstance(value, list):
        for sub_item in value:
            process_item("", sub_item, current_category_index, hierarchical_level, doc_created_node_indexes)
        return

    if isinstance(value, str):
        # (A) heading 검사: "1. ..." "・..." 등
        if not value.strip():
            log_to_file("[DEBUG] 빈 문자열 발견, 처리 건너뜀.")
            return
        
        if is_heading_start(value):
            # heading prefix & rest 분리
            heading_prefix, rest = split_heading_and_rest(value)
            if heading_prefix is None:
                pass  # fallback
            else:
                # 1) heading prefix만 엔티티
                log_to_file(f"[entity(only heading prefix)] {heading_prefix}")
                h_idx = append_entity_info(heading_prefix, doc_created_node_indexes)
                if current_category_index:
                    append_edge_info("sub", current_category_index, h_idx, doc_created_node_indexes)

                # 2) rest에 문장('。')이 있으면 => 문장 해석
                if rest and "。" in rest:
                    sentences = rest.split("。")
                    for s in sentences:
                        s = s.strip()
                        if not s:
                            continue
                        # 문장 해석
                        created_nodes = process_sentence(s + "。")
                        if current_category_index and created_nodes:
                            for cn in created_nodes:
                                append_edge_info("sub", current_category_index, cn, doc_created_node_indexes)
                else:
                    # rest에 '。'가 없으면 => 전체(heading prefix + rest)를 엔티티로
                    if rest:
                        e_val = heading_prefix + rest
                        log_to_file(f"[entity(with heading)] {e_val}")
                        e_idx = append_entity_info(e_val, doc_created_node_indexes)
                        if current_category_index:
                            append_edge_info("sub", current_category_index, e_idx, doc_created_node_indexes)
                return

        # (B) heading이 아닐 때
        #     만약 "。"가 있다면 => 문장 해석
        if "。" in value:
            sentences = value.split("。")
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                created_nodes = process_sentence(s + "。")
                if current_category_index and created_nodes:
                    for cn in created_nodes:
                        append_edge_info("sub", current_category_index, cn, doc_created_node_indexes)
        else:
            # (C) 마침표 없음 => 엔티티
            log_to_file(f"[entity] {value}")
            e_idx = append_entity_info(value, doc_created_node_indexes)
            if current_category_index:
                append_edge_info("sub", current_category_index, e_idx, doc_created_node_indexes)


def process_json(data, filename):
    """
    1) JSON -> 노드 생성
    2) 유사도 검사 + equivalent 엣지
    3) '유사도등록' 로그를 logger에 기록
    """
    # (1) 루트 카테고리 노드 생성
    root_category_index = append_category_info(
        key=filename,
        level=3,
        cat_type='カテゴリ名',
        doc_created_node_indexes=None
    )
    log_to_file(f"[category] '{filename}' (level=3, カテゴリ名)")

    # (2) 문서 카테고리 노드 생성
    for doc_name, doc_value in data.items():
        doc_created_node_indexes = set()
        doc_category_index = append_category_info(
            key=doc_name,
            level=2,
            cat_type='文書名',
            doc_created_node_indexes=doc_created_node_indexes
        )
        log_to_file(f"[category] '{doc_name}' (level=2, 文書名)")
        append_edge_info("sub", root_category_index, doc_category_index)
        # (2-1) 문서 하위항목 처리 및 노드 생성
        process_item("", doc_value, parent_category_index=doc_category_index, hierarchical_level=1,doc_created_node_indexes=doc_created_node_indexes)

        # (2-2) 문서단위 노드 및 엣지 불러오기
        entity_nodes_global = get_entity_structure()
        predicate_nodes_global = get_predicate_structure()
        category_nodes_global = get_category_structure()
        edge_global = get_edge()
        doc_category_nodes = [
            e for e in category_nodes_global 
            if e["index"] in doc_created_node_indexes
        ]
        doc_entity_nodes = [
            e for e in entity_nodes_global 
            if e["index"] in doc_created_node_indexes
        ]
        doc_predicate_nodes = [
            p for p in predicate_nodes_global
            if p["index"] in doc_created_node_indexes
        ]
        doc_edges = [
            p for p in edge_global
            if p["index"] in doc_created_node_indexes
        ]
        # (2-2) 유사도 검사 + equivalent
        run_similarity_check(doc_entity_nodes, doc_predicate_nodes)
        create_equivalent_edges()

        # (2-3) 문서단위 분석 결과 출력
        log_and_print_final_results(doc_name, doc_category_nodes, doc_entity_nodes, doc_predicate_nodes, doc_edges)
        # (2-4) 내림차순 유사도 보고(참고자료)
        produce_similarity_report(doc_entity_nodes, doc_predicate_nodes)
    
    #클러스터링 방식의 equivalent 관계 부여
    #cluster_equivalent_edges(entity_nodes, predicate_nodes, n_clusters=5)
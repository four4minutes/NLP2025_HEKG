# json_processor.py

import re
from source.document_parsing.logger import (
    log_to_file,
    record_similarity_logs
)
from source.document_parsing.node_maker import (
    append_category_info,
    append_entity_info,
    get_entity_structure,
    get_predicate_structure
)
from source.document_parsing.edge_maker import append_edge_info
from source.document_parsing.sentence_parser import process_sentence
from source.document_parsing.similarity_based_equivalent_extraction import (
    run_similarity_check,
    create_equivalent_edges
)
from source.document_parsing.text_utils import is_heading_start, split_heading_and_rest


def process_item(key, value, parent_category_index=None):
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
        log_to_file(f"[카테고리] {key}")
        current_category_index = append_category_info(key)

    # 2) 타입 분기
    if isinstance(value, dict):
        for sub_key, sub_value in value.items():
            process_item(sub_key, sub_value, current_category_index)
        return

    if isinstance(value, list):
        for sub_item in value:
            process_item("", sub_item, current_category_index)
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
                log_to_file(f"[엔티티(heading prefix)] {heading_prefix}")
                h_idx = append_entity_info(heading_prefix)
                if current_category_index:
                    append_edge_info("sub", current_category_index, h_idx)

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
                                append_edge_info("sub", current_category_index, cn)
                else:
                    # rest에 '。'가 없으면 => 전체(heading prefix + rest)를 엔티티로
                    if rest:
                        e_val = heading_prefix + rest
                        log_to_file(f"[엔티티(heading 전체)] {e_val}")
                        e_idx = append_entity_info(e_val)
                        if current_category_index:
                            append_edge_info("sub", current_category_index, e_idx)
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
                        append_edge_info("sub", current_category_index, cn)
        else:
            # (C) 마침표 없음 => 엔티티
            log_to_file(f"[엔티티] {value}")
            e_idx = append_entity_info(value)
            if current_category_index:
                append_edge_info("sub", current_category_index, e_idx)


def process_json(data):
    """
    1) JSON -> 노드 생성
    2) 유사도 검사 + equivalent 엣지
    3) '유사도등록' 로그를 logger에 기록
    """
    # 1) 모든 JSON 항목 순회 -> 노드 생성
    for key, value in data.items():
        process_item(key, value, parent_category_index=None)

    # 2) 유사도 검사 + equivalent
    entity_nodes = get_entity_structure()
    predicate_nodes = get_predicate_structure()
    run_similarity_check(entity_nodes, predicate_nodes)
    create_equivalent_edges()
    
    #클러스터링 방식의 equivalent 관계 부여
    #cluster_equivalent_edges(entity_nodes, predicate_nodes, n_clusters=5)
# json_processor.py

import re
from source.document_parsing.logger import log_to_file
from source.document_parsing.node_maker import (
    append_category_info,
    append_entity_info
)
from source.document_parsing.edge_maker import append_edge_info

# ----- 문장 해석 로직(기존 process_sentence)을 옮긴 모듈 임포트 -----
from sentence_parser import process_sentence

def is_heading_start(item: str) -> bool:
    """
    '１．' '1.' '2.' 등등, 혹은 '注' 같은 패턴에 매칭되면 heading 으로 판정
    (기존 main.py의 is_heading_start 그대로)
    """
    item_normalized = re.sub(r'[０-９]', lambda x: chr(ord(x.group(0)) - 0xFEE0), item)
    return bool(re.match(r'^\d+\.|^[・（）注]+', item_normalized))

def split_heading_and_rest(value: str):
    """
    value가 heading에 해당하면, heading prefix와 나머지(rest)를 분리해서 반환.
    (기존 main.py의 split_heading_and_rest 그대로)
    """
    item_normalized = re.sub(r'[０-９]', lambda x: chr(ord(x.group(0)) - 0xFEE0), value)
    pattern = r'^(\d+\.|[・（）注]+)\s?(.*)$'
    match = re.match(pattern, item_normalized)
    if match:
        heading_prefix = match.group(1).strip()
        rest = match.group(2).strip()
        return heading_prefix, rest
    else:
        return None, None

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
    기존 main.py 하단의 process_json(data) 그대로.
    최상위 JSON 키/값 순회
    """
    for key, value in data.items():
        process_item(key, value, parent_category_index=None)
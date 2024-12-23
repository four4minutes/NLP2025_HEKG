# sentence_parser.py

import re
from source.document_parsing.logger import log_to_file
from source.document_parsing.node_maker import append_entity_info, append_predicate_structure
from source.document_parsing.edge_maker import append_edge_info
from source.document_parsing.time_and_place_extraction import extract_time_and_place
from source.document_parsing.predicate_extraction import (
    extract_predicates,
    extract_entity_and_predicate_structures
)
from source.document_parsing.residue_extraction import process_sentence_with_residue_removal

def process_sentence(sentence: str):
    """
    기존 main.py의 process_sentence 함수 그대로.
    1) 시간/장소 추출
    2) 술어항 구조, 엔티티 추출
    3) info_SpecificTime / info_SpecificPlace 엣지 부여
    4) 잔여어 처리
    5) 생성된 노드 인덱스 반환
    """
    log_to_file(f"\n문장: {sentence}")

    # (A) 시간/장소 추출
    time_and_place = extract_time_and_place(sentence + "。")
    time_expressions = time_and_place['time']
    place_expressions = time_and_place['place']

    created_details = []

    # 1) 시간 표현 노드
    if time_expressions:
        log_to_file(f"추출된 시간 표현: {time_expressions}")
        for t_expr in time_expressions:
            offset = sentence.find(t_expr)
            if offset < 0:
                offset = 999999
            node_idx = append_entity_info(t_expr)
            created_details.append({
                "index": node_idx,
                "text": t_expr,
                "offset": offset,
                "type": "time"
            })

    # 2) 장소 표현 노드
    if place_expressions:
        log_to_file(f"추출된 장소 표현: {place_expressions}")
        for p_expr in place_expressions:
            offset = sentence.find(p_expr)
            if offset < 0:
                offset = 999999
            node_idx = append_entity_info(p_expr)
            created_details.append({
                "index": node_idx,
                "text": p_expr,
                "offset": offset,
                "type": "place"
            })

    # (B) 술어항 구조 & 엔티티
    event_predicates, entity_predicates = extract_predicates(sentence)
    log_to_file(f"----------------------------\n추출된 사상 술어: {event_predicates if event_predicates else '추출되지 않음'}")
    log_to_file(f"추출된 개념 술어: {entity_predicates if entity_predicates else '추출되지 않음'}")

    predicate_argument_structures, entities = extract_entity_and_predicate_structures(
        sentence,
        event_predicates,
        entity_predicates,
        time_expressions,
        place_expressions
    )

    log_to_file("------추출된 述語項構造------")
    for i, structure in enumerate(predicate_argument_structures, 1):
        log_to_file(f"({i}) {structure}")

    created_predicate_indexes = append_predicate_structure(predicate_argument_structures)

    # 술어항 구조 노드의 offset
    for idx, struct_str in zip(created_predicate_indexes, predicate_argument_structures):
        main_pred_match = re.search(r'^(.*?)\(述語\)', struct_str)
        if main_pred_match:
            main_pred_text = main_pred_match.group(1).strip()
        else:
            main_pred_text = struct_str

        offset = sentence.find(main_pred_text)
        if offset < 0:
            offset = 999999

        created_details.append({
            "index": idx,
            "text": main_pred_text,
            "offset": offset,
            "type": "predicate"
        })

    # 추가 엔티티 노드
    log_to_file("--------추출된 엔티티--------")
    for i, entity_str in enumerate(entities, 1):
        log_to_file(f"({i}) {entity_str}")

    for ent_str in entities:
        offset = sentence.find(ent_str)
        if offset < 0:
            offset = 999999
        ent_idx = append_entity_info(ent_str)
        created_details.append({
            "index": ent_idx,
            "text": ent_str,
            "offset": offset,
            "type": "entity"
        })

    log_to_file("----------------------------")

    # 잔여어 처리
    if predicate_argument_structures:
        final_sentence = process_sentence_with_residue_removal(sentence, predicate_argument_structures)
        log_to_file(f"술어항 구조 표현 제거 후: {final_sentence}")
    else:
        log_to_file("[DEBUG] 술어항 구조가 생성되지 않았습니다. 수정 작업을 생략합니다.")

    # (C) info_SpecificTime / info_SpecificPlace 엣지
    created_details_sorted = sorted(created_details, key=lambda x: x["offset"])

    for i, c in enumerate(created_details_sorted):
        if c["type"] in ("time", "place"):
            from_node_type_candidates = ("predicate", "entity")
            min_dist = 999999
            chosen_idx = None

            for j in range(i+1, len(created_details_sorted)):
                nxt = created_details_sorted[j]
                if nxt["type"] not in from_node_type_candidates:
                    continue

                dist = nxt["offset"] - c["offset"]
                if dist >= 0 and dist < min_dist:
                    min_dist = dist
                    chosen_idx = nxt["index"]

            if chosen_idx is not None:
                edge_type = "info_SpecificTime" if c["type"] == "time" else "info_SpecificPlace"
                append_edge_info(edge_type, from_node_index=chosen_idx, to_node_index=c["index"])

    all_created_indexes = [d["index"] for d in created_details]
    return all_created_indexes
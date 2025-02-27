# sentence_parser.py

import re
from source.document_parsing.logger import log_to_file
from source.document_parsing.node_maker import append_entity_info, append_predicate_structure, get_predicate_structure
from source.document_parsing.edge_maker import append_edge_info
from source.document_parsing.time_and_place_extraction import extract_time_and_place
from source.document_parsing.predicate_extraction import (
    extract_predicates,
    extract_entity_and_predicate_structures
)
from source.document_parsing.text_utils import process_sentence_with_residue_removal, convert_predicate_to_text
from causal_relationship_extraction import extract_causal_relationship

def process_sentence(sentence: str, doc_created_indexes=None):
    # 1) 문장 로깅
    log_to_file("\n----------------------------")
    log_to_file(f"문장: {sentence}")

    # 2) [노드] 시간/장소 표현 추출
    #    sentence + "。" 로 extract_time_and_place 호출 -> time_expressions, place_expressions
    time_and_place = extract_time_and_place(sentence + "。")
    time_expressions = time_and_place['time']
    place_expressions = time_and_place['place']

    # created_nodes_in_sentence는 문장 내에서 추출한 "노드"들의 정보를 담아두는 리스트
    # - 노드 정보: 텍스트(text), 노드 타입(type: time/place/predicate/entity 등), 
    #   문장 내 시작 위치(offset), 노드 인덱스(index) 등을 저장합니다.
    # - offset은 해당 텍스트가 문장 내에서 시작하는 인덱스로, 노드 정렬 및 
    #   노드 간 거리 계산(엣지 연결)에 활용
    created_nodes_in_sentence = []

    # 3) [노드] 시간 표현 노드 생성
    #    추출된 time_expressions 각각에 대해 append_entity_info -> time 노드 생성
    if time_expressions:
        log_to_file(f"추출된 시간 표현: {time_expressions}")
        for t_expr in time_expressions:
            offset = sentence.find(t_expr)
            if offset < 0:
                offset = 999999
            node_idx = append_entity_info(t_expr)
            created_nodes_in_sentence.append({
                "index": node_idx,
                "text": t_expr,
                "offset": offset,
                "type": "time"
            })

    # 4) [노드] 장소 표현 노드 생성
    #    추출된 place_expressions 각각에 대해 append_entity_info -> place 노드 생성
    if place_expressions:
        log_to_file(f"추출된 장소 표현: {place_expressions}")
        for p_expr in place_expressions:
            offset = sentence.find(p_expr)
            if offset < 0:
                offset = 999999
            node_idx = append_entity_info(p_expr)
            created_nodes_in_sentence.append({
                "index": node_idx,
                "text": p_expr,
                "offset": offset,
                "type": "place"
            })

    # 5) [노드] 술어항 구조, 추가 엔티티 추출
    #    extract_predicates -> (event_predicates, entity_predicates)
    #    extract_entity_and_predicate_structures -> (predicate_argument_structures, entities)
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

    # 6) [노드] 술어항 구조 노드 생성
    #    -> append_predicate_structure -> predicate 노드 인덱스 목록 반환
    created_predicate_indexes = append_predicate_structure(predicate_argument_structures)

    #    + 해당 노드들의 offset 계산
    for idx, struct_str in zip(created_predicate_indexes, predicate_argument_structures):
        main_pred_match = re.search(r'^(.*?)\(述語\)', struct_str)
        if main_pred_match:
            main_pred_text = main_pred_match.group(1).strip()
        else:
            main_pred_text = struct_str

        offset = sentence.find(main_pred_text)
        if offset < 0:
            offset = 999999
        
        pred_dict = next((p for p in get_predicate_structure() if p["index"] == idx), None)
        if pred_dict is not None:
            text = convert_predicate_to_text(pred_dict).strip()
            print(text)
        else:
            text = main_pred_text
        
        created_nodes_in_sentence.append({
            "index": idx,
            "text": text,
            "offset": offset,
            "type": "predicate"
        })

    # 7) [노드] 추가 엔티티 노드 생성
    #    -> extract_entity_and_predicate_structures 로 추출된 entities
    log_to_file("--------추출된 엔티티--------")
    for i, entity_str in enumerate(entities, 1):
        log_to_file(f"({i}) {entity_str}")

    for ent_str in entities:
        offset = sentence.find(ent_str)
        if offset < 0:
            offset = 999999
        ent_idx = append_entity_info(ent_str)
        created_nodes_in_sentence.append({
            "index": ent_idx,
            "text": ent_str,
            "offset": offset,
            "type": "entity"
        })

    log_to_file("----------------------------")

    # 8) 잔여어 처리 (술어항 구조 표현 제거)
    #    -> process_sentence_with_residue_removal
    if predicate_argument_structures:
        final_sentence = process_sentence_with_residue_removal(sentence, predicate_argument_structures)
        log_to_file(f"술어항 구조 표현 제거 후: {final_sentence}")
    else:
        log_to_file("[DEBUG] 술어항 구조가 생성되지 않았습니다. 수정 작업을 생략합니다.")

    # 9) [엣지] info_SpecificTime / info_SpecificPlace 엣지 생성
    #    문장 내 offset 순으로 노드들을 정렬 -> time/place 노드는 뒤쪽에 있는 predicate/entity 중 가장 가까운 노드와 연결
    created_nodes_sorted = sorted(created_nodes_in_sentence, key=lambda x: x["offset"])

    for i, c in enumerate(created_nodes_sorted):
        if c["type"] in ("time", "place"):
            from_node_type_candidates = ("predicate", "entity")
            min_dist = 999999
            chosen_idx = None

            for j in range(i+1, len(created_nodes_sorted)):
                nxt = created_nodes_sorted[j]
                if nxt["type"] not in from_node_type_candidates:
                    continue

                dist = nxt["offset"] - c["offset"]
                if dist >= 0 and dist < min_dist:
                    min_dist = dist
                    chosen_idx = nxt["index"]

            if chosen_idx is not None:
                edge_type = "info_SpecificTime" if c["type"] == "time" else "info_SpecificPlace"
                append_edge_info(edge_type, from_node_index=chosen_idx, to_node_index=c["index"], doc_created_edge_indexes=doc_created_indexes)

    # 10) 문장 + 노드 정보를 이용해 인과관계 추출
    causal_node_list = []
    for n in created_nodes_in_sentence:
        if n["type"] in ("predicate", "entity"):
            causal_node_list.append({"index": n["index"], "text": n["text"]})   

    extract_causal_relationship(sentence, causal_node_list, doc_created_indexes)

    # 11) 최종적으로 생성된 노드들의 인덱스 리스트를 반환
    all_created_indexes = [d["index"] for d in created_nodes_in_sentence]
    return all_created_indexes
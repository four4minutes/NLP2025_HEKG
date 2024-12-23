import re
import json
from source.document_parsing.time_and_place_extraction import extract_time_and_place
from source.document_parsing.predicate_extraction import extract_predicates, extract_entity_and_predicate_structures
from source.document_parsing.residue_extraction import process_sentence_with_residue_removal
from source.document_parsing.logger import initialize_logger, log_to_file, log_and_print_final_results
from source.document_parsing.node_maker import append_category_info, append_entity_info, append_predicate_structure, get_category, get_entity_structure, get_predicate_structure
from source.document_parsing.edge_maker import append_edge_info, get_edge

# 로그 초기화 (프로그램 실행 시 한 번만 호출)
initialize_logger()

# JSON 데이터 로드
with open('test.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

def is_heading(item: str) -> bool:
    item_normalized = re.sub(r'[０-９]', lambda x: chr(ord(x.group(0)) - 0xFEE0), item)
    return bool(re.match(r'^\d+\.|^[・（）注]+', item_normalized))

def process_sentence(sentence: str):
    log_to_file(f"\n문장: {sentence}")

    # --------------------- (A) 시간/장소 추출 ---------------------
    time_and_place = extract_time_and_place(sentence + "。")
    time_expressions = time_and_place['time']    # 예: ['ゴールデンウィークの午後']
    place_expressions = time_and_place['place']  # 예: ['千里万博公園「エキスポランド」のジェットコースター']

    created_details = []  # 노드 + 오프셋 정보: [{"index":..., "text":..., "offset":..., "type":"time|place|predicate|entity"}]

    # 1) 시간 표현 노드 생성
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

    # 2) 장소 표현 노드 생성
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

    # --------------------- (B) 술어항 구조 & 엔티티 추출 ---------------------
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

    # (B-1) 술어항 구조 노드 생성
    log_to_file("------추출된 述語項構造------")
    for i, structure in enumerate(predicate_argument_structures, 1):
        log_to_file(f"({i}) {structure}")
    created_predicate_indexes = append_predicate_structure(predicate_argument_structures)

    import re
    for idx, struct_str in zip(created_predicate_indexes, predicate_argument_structures):
        # 예: "脱輪し(述語), ジェットコースターの車輪(ガ格), 레ール(カラ格)"
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

    # (B-2) 추가 엔티티 노드 생성
    log_to_file("--------추출된 엔티티--------")
    for i, entity_str in enumerate(entities, 1):
        log_to_file(f"({i}) {entity_str}")

    created_entity_indexes = []
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

    # (B-3) 잔여어 처리 후 로그
    if predicate_argument_structures:
        final_sentence = process_sentence_with_residue_removal(sentence, predicate_argument_structures)
        log_to_file(f"술어항 구조 표현 제거 후: {final_sentence}")
    else:
        log_to_file("[DEBUG] 술어항 구조가 생성되지 않았습니다. 수정 작업을 생략합니다.")

    # --------------------- (C) info_SpecificTime / info_SpecificPlace 엣지 부여 ---------------------
    # 1) offset 기준으로 정렬
    created_details_sorted = sorted(created_details, key=lambda x: x["offset"])

    # 2) time/place 노드가 있는 위치(i) → 뒤쪽(j)에 있는 from 후보(오직 'predicate' 또는 'entity') 중
    #    가장 가까운 노드를 찾아 엣지 부여
    for i, c in enumerate(created_details_sorted):
        if c["type"] in ("time", "place"):
            from_node_type_candidates = ("predicate", "entity")  # from은 이 둘만 허용
            min_dist = 999999
            chosen_idx = None

            for j in range(i+1, len(created_details_sorted)):
                nxt = created_details_sorted[j]
                # 'time'/'place'는 from 대상에서 제외
                if nxt["type"] not in from_node_type_candidates:
                    continue

                dist = nxt["offset"] - c["offset"]
                if dist >= 0 and dist < min_dist:
                    min_dist = dist
                    chosen_idx = nxt["index"]

            if chosen_idx is not None:
                edge_type = "info_SpecificTime" if c["type"] == "time" else "info_SpecificPlace"
                # from=chosen_idx, to=c["index"]
                append_edge_info(edge_type, from_node_index=chosen_idx, to_node_index=c["index"])

    # 모든 노드 인덱스 반환
    all_created_indexes = [d["index"] for d in created_details]
    return all_created_indexes

def process_item(key, value, parent_category_index=None):
    """
    key: JSON의 속성명
    value: 그에 대응하는 값 (str, dict, list)
    parent_category_index: 상위 카테고리 노드 인덱스 (없으면 None)
    """
    current_category_index = parent_category_index

    # key가 비어있지 않으면 => 새 카테고리 노드
    if key:
        log_to_file(f"カテゴリー : {key}")
        current_category_index = append_category_info(key)

    # value가 dict인 경우
    if isinstance(value, dict):
        for sub_key, sub_value in value.items():
            process_item(sub_key, sub_value, current_category_index)

    # value가 list인 경우
    elif isinstance(value, list):
        for sub_item in value:
            process_item("", sub_item, current_category_index)

    # value가 문자열인 경우
    elif isinstance(value, str):
        if is_heading(value):
            # heading 형식 처리
            heading_match = re.match(r'^(?P<heading>\d+\.|[・（）注]+)(?P<content>.*)', value)
            if heading_match:
                heading = heading_match.group("heading").strip()
                content = heading_match.group("content").strip()

                # heading 부분 엔티티
                ent_idx = append_entity_info(heading)
                # sub 관계
                if current_category_index:
                    append_edge_info("sub", current_category_index, ent_idx)

                # content 문장 분석
                if "。" in content:
                    created_nodes = process_sentence(content)
                    if current_category_index:
                        for idx in created_nodes:
                            append_edge_info("sub", current_category_index, idx)
                else:
                    # 단순 엔티티
                    sub_ent_idx = append_entity_info(content)
                    if current_category_index:
                        append_edge_info("sub", current_category_index, sub_ent_idx)

            else:
                # 혹시 match 안 될 경우
                ent_idx = append_entity_info(value)
                if current_category_index:
                    append_edge_info("sub", current_category_index, ent_idx)

        else:
            # 일반 문자열 처리
            if "。" in value:
                # 문장 해석
                created_nodes = process_sentence(value)
                # 해석으로 생성된 노드들과 sub 관계
                if current_category_index:
                    for idx in created_nodes:
                        append_edge_info("sub", current_category_index, idx)
            else:
                # 단순 엔티티
                ent_idx = append_entity_info(value)
                if current_category_index:
                    append_edge_info("sub", current_category_index, ent_idx)

def process_json(data):
    for key, value in data.items():
        process_item(key, value, parent_category_index=None)

# JSON 파싱 시작
process_json(data)

# 최종 결과 배열을 logger.py로 옮긴 log_and_print_final_results에서 출력
category = get_category()
entity_structure = get_entity_structure()
predicate_structure = get_predicate_structure()
edge = get_edge()

log_and_print_final_results(category, entity_structure, predicate_structure, edge)
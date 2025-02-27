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
from time_evolution_extraction import calculate_event_evolution_relationship

# 항목 캐시: 현재 항목에 속한 노드 정보를 임시로 저장
_current_item_cache = {
    "item_name": None,  # 레벨=1 항목명
    "nodes": [],         # [{ "index": 10, "type": "predicate" }, ...]
    "original_sentences" : ""
}

def finalize_current_item(doc_created_edge_indexes=None):
    """
    항목(레벨=1) 캐시에 모인 노드들에 대해,
    time_evolution_extraction.calculate_event_evolution_relationship 함수를 호출하여
    next_TimeStamp 관계를 생성(혹은 다른 이벤트 관계도 생성 가능).
    """
    # 항목이 설정되지 않았거나 캐시가 비어 있으면 스킵
    if not _current_item_cache["item_name"]:
        return

    if len(_current_item_cache["nodes"]) >= 2:
        # 캐시에서 entity/predicate의 인덱스만 추출
        item_entity_indexes = [ x["index"] for x in _current_item_cache["nodes"] if x["type"] == "entity" ]
        item_predicate_indexes = [ x["index"] for x in _current_item_cache["nodes"] if x["type"] == "predicate" ]

        # 실제 node 객체로 필터링
        all_entities   = get_entity_structure()
        all_predicates = get_predicate_structure()
        item_entity_nodes = [ e for e in all_entities   if e["index"] in item_entity_indexes ]
        item_predicate_nodes = [ p for p in all_predicates if p["index"] in item_predicate_indexes ]

        original_sentences = _current_item_cache["original_sentences"]

        # 2) time_evolution_extraction 모듈에 넘겨서 관계 생성
        calculate_event_evolution_relationship(item_entity_nodes, item_predicate_nodes, original_sentences, doc_created_edge_indexes)

    # 3) 캐시 비우기
    _current_item_cache["item_name"] = None
    _current_item_cache["nodes"].clear()
    _current_item_cache["original_sentences"] = ""

def start_new_item(item_name: str,doc_created_edge_indexes=None):
    """
    새로운 항목(레벨=1)을 시작:
    - 이전 항목을 finalize
    - 캐시를 새 항목으로 갱신
    """
    # 1) 이전 항목 마무리
    finalize_current_item(doc_created_edge_indexes)
    # 2) 새 항목 이름
    _current_item_cache["item_name"] = item_name

def add_node_to_current_item(node_index: int, node_type: str):
    """
    항목 캐시에 노드 등록: type = "entity", "predicate", "category" 등
    """
    _current_item_cache["nodes"].append({
        "index": node_index,
        "type": node_type
    })

def add_original_sentence_to_current_item(sentence:str):
    _current_item_cache["original_sentences"] = _current_item_cache["original_sentences"]+sentence

def process_item(key, value, parent_category_index=None, hierarchical_level=0, doc_created_indexes=None):
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
        if hierarchical_level == 1:
            start_new_item(key,doc_created_indexes)  # 이전 항목 finalize + 새 항목 cache 준비
        log_to_file(f"\n[category(level={hierarchical_level})] {key}")
        current_category_index = append_category_info(
            key,
            level=hierarchical_level,
            cat_type='項目名',
            doc_created_node_indexes=doc_created_indexes
        )
        if parent_category_index is not None and parent_category_index != current_category_index:
            append_edge_info("sub", parent_category_index, current_category_index, doc_created_indexes)

    # 2) 타입 분기
    if isinstance(value, dict):
        for sub_key, sub_val in value.items():
            process_item(sub_key, sub_val, current_category_index, hierarchical_level, doc_created_indexes)
        return

    if isinstance(value, list):
        for sub_item in value:
            process_item("", sub_item, current_category_index, hierarchical_level, doc_created_indexes)
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
                h_idx = append_entity_info(heading_prefix, doc_created_indexes)
                add_original_sentence_to_current_item(value)
                add_node_to_current_item(h_idx, "entity") 
                if current_category_index:
                    append_edge_info("sub", current_category_index, h_idx, doc_created_indexes)

                # 2) rest에 문장('。')이 있으면 => 문장 해석
                if rest and "。" in rest:
                    sentences = rest.split("。")
                    for s in sentences:
                        s = s.strip()
                        if not s:
                            continue
                        # 문장 해석
                        add_original_sentence_to_current_item(s)
                        created_nodes = process_sentence(s + "。",doc_created_indexes)
                        if current_category_index and created_nodes:
                            for cn in created_nodes:
                                add_node_to_current_item(cn, "predicate")
                                append_edge_info("sub", current_category_index, cn, doc_created_indexes)
                else:
                    # rest에 '。'가 없으면 => 전체(heading prefix + rest)를 엔티티로
                    if rest:
                        e_val = heading_prefix + rest
                        log_to_file(f"[entity(with heading)] {e_val}")
                        e_idx = append_entity_info(e_val, doc_created_indexes)
                        add_original_sentence_to_current_item(e_val)
                        add_node_to_current_item(e_idx, "entity")
                        if current_category_index:
                            append_edge_info("sub", current_category_index, e_idx, doc_created_indexes)
                return

        # (B) heading이 아닐 때
        #     만약 "。"가 있다면 => 문장 해석
        if "。" in value:
            sentences = value.split("。")
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                add_original_sentence_to_current_item(s)
                created_nodes = process_sentence(s + "。",doc_created_indexes)
                if current_category_index and created_nodes:
                    for cn in created_nodes:
                        add_node_to_current_item(cn, "predicate")
                        append_edge_info("sub", current_category_index, cn, doc_created_indexes)
        else:
            # (C) 마침표 없음 => 엔티티
            log_to_file(f"[entity] {value}")
            e_idx = append_entity_info(value, doc_created_indexes)
            add_original_sentence_to_current_item(value)
            add_node_to_current_item(e_idx, "entity")
            if current_category_index:
                append_edge_info("sub", current_category_index, e_idx, doc_created_indexes)


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
        doc_created_indexes = set()
        doc_category_index = append_category_info(
            key=doc_name,
            level=2,
            cat_type='文書名',
            doc_created_node_indexes=doc_created_indexes
        )
        finalize_current_item(doc_created_indexes)
        log_to_file(f"\n[category] '{doc_name}' (level=2, 文書名)")
        append_edge_info("sub", root_category_index, doc_category_index)
        # (2-1) 문서 하위항목 처리 및 노드 생성
        process_item("", doc_value, parent_category_index=doc_category_index, hierarchical_level=1,doc_created_indexes=doc_created_indexes)

        # (2-2) 문서단위 노드 불러오기
        entity_nodes_global = get_entity_structure()
        predicate_nodes_global = get_predicate_structure()
        category_nodes_global = get_category_structure()
        
        doc_category_nodes = [ e for e in category_nodes_global if e["index"] in doc_created_indexes ]
        doc_entity_nodes   = [ e for e in entity_nodes_global  if e["index"] in doc_created_indexes ]
        doc_predicate_nodes= [ p for p in predicate_nodes_global if p["index"] in doc_created_indexes ]
        
        # (2-2) 유사도 검사 + equivalent
        run_similarity_check(doc_entity_nodes, doc_predicate_nodes)
        create_equivalent_edges(doc_created_indexes)

        # (2-3) 문서단위 분석 결과 출력
        edge_global = get_edge()
        doc_edges = [ p for p in edge_global if p["index"] in doc_created_indexes ]
        log_and_print_final_results(doc_name, doc_category_nodes, doc_entity_nodes, doc_predicate_nodes, doc_edges)
        # (2-4) 내림차순 유사도 보고(참고자료)
        produce_similarity_report(doc_entity_nodes, doc_predicate_nodes)
    
    finalize_current_item(doc_created_indexes)
    
    #클러스터링 방식의 equivalent 관계 부여
    #cluster_equivalent_edges(entity_nodes, predicate_nodes, n_clusters=5)
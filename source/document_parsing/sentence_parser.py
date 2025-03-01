# sentence_parser.py
# 一つの文を分析するモジュール

import re
from source.document_parsing.logger import log_to_file
from source.document_parsing.node_maker import append_entity_info, append_predicate_structure, get_predicate_structure
from source.document_parsing.edge_maker import append_edge_info
from source.document_parsing.time_and_place_extraction import extract_time_and_place
from source.document_parsing.predicate_extraction import extract_predicates, extract_entity_and_predicate_structures
from source.document_parsing.text_utils import process_sentence_with_residue_removal, convert_predicate_to_text
from source.document_parsing.causal_relationship_extraction import extract_causal_relationship
from source.document_parsing.detailed_info_relationship_extraction import extract_explain_details_relationship

def process_sentence(sentence: str, doc_created_indexes=None):
    '''
    1つの文を解析し、時間・場所ノードやエンティティ、述語構造ノード、そして
    それらの間の各種関係エッジを生成するメイン処理関数。
    - sentence : 対象の文
    - doc_created_indexes : 処理中に生成したノードやエッジのインデックスを追跡するためのセット
    - return : 生成されたノードのインデックス一覧
    '''
    # (1) 文ログ出力（デバッグ）
    log_to_file(f"\nProcessing sentence: {sentence}")

    # (2) 時間・場所表現の抽出
    time_and_place = extract_time_and_place(sentence + "。")
    time_expressions = time_and_place['time']
    place_expressions = time_and_place['place']

    # (3) 生成されたノード情報を一時的に格納するリスト
    created_nodes_in_sentence = []

    # (4) 時間表現ノードを作成
    if time_expressions:
        log_to_file(f"Extracted time expressions: {time_expressions}")
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

     # (5) 場所表現ノードを作成
    if place_expressions:
        log_to_file(f"Extracted place expressions: {place_expressions}")
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

    # (6) 述語（事象/概念）の抽出
    event_predicates, entity_predicates = extract_predicates(sentence)
    log_to_file(f"Extracted event predicates: {event_predicates if event_predicates else 'None'}")
    log_to_file(f"Extracted entity predicates: {entity_predicates if entity_predicates else 'None'}")

    # (7) 述語項構造と追加エンティティの抽出
    predicate_argument_structures, entities = extract_entity_and_predicate_structures(
        sentence,
        event_predicates,
        entity_predicates,
        time_expressions,
        place_expressions
    )

    log_to_file("Extracted predicate-argument structures:")
    for i, structure in enumerate(predicate_argument_structures, 1):
        log_to_file(f"  ({i}) {structure}")

    # (8) 述語ノードを生成
    created_predicate_indexes = append_predicate_structure(predicate_argument_structures)

    # 述語ノードの位置情報を設定
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
        else:
            text = main_pred_text
        
        created_nodes_in_sentence.append({
            "index": idx,
            "text": text,
            "offset": offset,
            "type": "predicate"
        })

    # (9) 追加エンティティノードを生成
    log_to_file("Extracted entities:")
    for i, entity_str in enumerate(entities, 1):
        log_to_file(f"  ({i}) {entity_str}")

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

    # (10) 述語項構造文字列を文から除去して残差を確認
    if predicate_argument_structures:
        final_sentence = process_sentence_with_residue_removal(sentence, predicate_argument_structures)
        log_to_file(f"After removing predicate structures: {final_sentence}")
    else:
        log_to_file("[DEBUG] No predicate structures found, skip residue removal.")

    # (11) 時間・場所ノードと他ノードを対応付ける (info_SpecificTime / info_SpecificPlace)
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

    # (12) ノードリストを用いて因果関係と説明関係を抽出 
    target_node_list = []
    for n in created_nodes_in_sentence:
        if n["type"] in ("predicate", "entity"):
            target_node_list.append({"index": n["index"], "text": n["text"]})   

    extract_causal_relationship(sentence, target_node_list, doc_created_indexes) #인과관계 추출
    extract_explain_details_relationship(sentence, target_node_list, doc_created_indexes) #설명관계 추출출

    # (13) 生成されたノードのインデックスをまとめて返す
    all_created_indexes = [d["index"] for d in created_nodes_in_sentence]
    return all_created_indexes
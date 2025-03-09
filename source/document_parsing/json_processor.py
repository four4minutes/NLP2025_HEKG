# json_processor.py

from source.document_parsing.logger import log_to_file, produce_similarity_report, log_and_print_final_results
from source.document_parsing.node_maker import append_category_info, append_entity_info, get_entity_structure, get_predicate_structure, get_category_structure
from source.document_parsing.edge_maker import append_edge_info, get_edge
from source.document_parsing.sentence_parser import process_sentence
from source.document_parsing.similarity_based_equivalent_extraction import run_similarity_check, create_equivalent_edges
from source.document_parsing.text_utils import is_heading_start, split_heading_and_rest
from source.document_parsing.time_evolution_extraction import calculate_event_evolution_relationship
from source.document_parsing.entity_realation_extraction import extract_entity_relationship

# 項目キャッシュ: 処理中の項目に属するノード情報を保持する
_current_item_cache = {
    "item_name": None,          # 項目名
    "nodes": [],                # ノード情報 [{ "index": 10, "type": "predicate" }, ...]
    "original_sentences" : ""   # 原文
}

#　除外条件に該当する関係リスト
EXCLUDE_RELATION_TARGETS = {
    "explain_reason",
    "info_SpecificTime",
    "info_SpecificPlace",
    "explain_details",
    "correspond_to"
}

def finalize_current_item(doc_created_edge_indexes=None):
    '''
    現在の項目情報をもとに、時系列の計算などを行って next_TimeStampエッジを生成する。
    - doc_created_edge_indexes : 生成したエッジのインデックスを追跡するためのセット
    '''
    # (1) 項目がない場合、キャッシュが空の場合はスキップ
    if not _current_item_cache["item_name"]:
        return

    if len(_current_item_cache["nodes"]) >= 2:
        # (2) 分析対象データの準備
        # (2-1) ノードの情報を取得
        all_entities   = get_entity_structure()
        all_predicates = get_predicate_structure()

        # (2-2) 項目キャッシュからインデックス情報を抽出
        item_entity_indexes = [ x["index"] for x in _current_item_cache["nodes"] if x["type"] == "entity" ]
        item_predicate_indexes = [ x["index"] for x in _current_item_cache["nodes"] if x["type"] == "predicate" ]

        # (2-3) 項目キャッシュから原文情報を抽出
        original_sentences = _current_item_cache["original_sentences"]

        # (3) next_TimeStamp関係を生成
        # (3-1) 除外条件に該当する関係を持つノードは分析から除外
        excluded_nodes = set()
        all_edges = get_edge()
        for e in all_edges:
            if e["type"] in EXCLUDE_RELATION_TARGETS:
                excluded_nodes.add(e["to"])

        # (3-2) インデックス情報からevent_evolution_relationship分析対象ノードを取得
        item_entity_for_event_indexes = [ idx for idx in item_entity_indexes if idx not in excluded_nodes]
        item_predicate_for_event_indexes = [ idx for idx in item_predicate_indexes if idx not in excluded_nodes]
        item_entity_nodes = [ e for e in all_entities   if e["index"] in item_entity_for_event_indexes ]
        item_predicate_nodes = [ p for p in all_predicates if p["index"] in item_predicate_for_event_indexes ]

        # (3-3) time_evolution_extractionモジュールに渡してnext_TimeStamp関係を生成
        calculate_event_evolution_relationship(item_entity_nodes, item_predicate_nodes, original_sentences, doc_created_edge_indexes)

        # (4) 自動生成関係を生成
        # (4-1) インデックス情報からextract_entity_relationship分析対象ノードを取得
        item_entity_nodes = [ e for e in all_entities   if e["index"] in item_entity_indexes ]
        item_predicate_nodes = [ p for p in all_predicates if p["index"] in item_predicate_indexes ]
        
        # (4-2) インデックス情報からextract_entity_relationship分析対象エッジを取得
        all_edges = get_edge()
        item_node_indexes = set(item_entity_indexes + item_predicate_indexes)
        item_edges = [edge for edge in all_edges if (edge["from"] in item_node_indexes or edge["to"] in item_node_indexes)]

        # (4-3) entity_realation_extractionモジュールに渡して自動生成関係を生成
        extract_entity_relationship(item_entity_nodes, item_predicate_nodes, item_edges, original_sentences, doc_created_edge_indexes)

    # (6) キャッシュをクリアする
    _current_item_cache["item_name"] = None
    _current_item_cache["nodes"].clear()
    _current_item_cache["original_sentences"] = ""

def start_new_item(item_name: str,doc_created_edge_indexes=None):
    '''
    新しい項目が始まるタイミングで、前の項目をfinalizeしてからキャッシュを更新する。
    - item_name : 新しい項目の名前
    '''
    finalize_current_item(doc_created_edge_indexes)
    _current_item_cache["item_name"] = item_name # 新しい項目名

def add_node_to_current_item(node_index: int, node_type: str):
    '''
    現在の項目キャッシュにノードを追加する。
    '''
    _current_item_cache["nodes"].append({"index": node_index, "type": node_type})

def add_original_sentence_to_current_item(sentence:str):
    '''
    現在の項目キャッシュに原文を追記する。
    '''
    _current_item_cache["original_sentences"] = _current_item_cache["original_sentences"]+sentence

def process_item(key, value, parent_category_index=None, hierarchical_level=0, doc_created_indexes=None):
    '''
    JSONのキーと値に応じて再帰的にノード生成や文解析を行う関数。
    - key : JSON上のキーがあれば文字列（なければ空文字）
    - value : キーに対応する値（文字列・リスト・辞書）
    - parent_category_index : 親カテゴリノードのインデックス
    - hierarchical_level : カテゴリの階層レベル
    - doc_created_indexes : 生成されたノードやエッジを追跡するためのセット
    '''
    current_category_index = parent_category_index

    # (1) json形式でのkeyの場合
    if key:
        # (1-1) 階層レベルが1の場合
        if hierarchical_level == 1:
            start_new_item(key,doc_created_indexes)  # 以前の項目から新しい項目
        log_to_file(f"\nFound category [category(level={hierarchical_level})] {key}")
        current_category_index = append_category_info(key, level=hierarchical_level, cat_type='項目名', doc_created_node_indexes=doc_created_indexes)
        # (1-2) 親カテゴリノードが存在する場合はsub関係の付与
        if parent_category_index is not None and parent_category_index != current_category_index:
            append_edge_info("sub", parent_category_index, current_category_index, doc_created_indexes)

    # (2) valueが階層構造を持つ場合は、process_itemを再帰的に呼び出して処理する
    if isinstance(value, dict):
        for sub_key, sub_val in value.items():
            process_item(sub_key, sub_val, current_category_index, hierarchical_level, doc_created_indexes)
        return
    if isinstance(value, list):
        for sub_item in value:
            process_item("", sub_item, current_category_index, hierarchical_level, doc_created_indexes)
        return

    # (3) valueが文字列の場合に分析を行う
    if isinstance(value, str):
        # (3-1) heading("1.", "・"など)の判断: 
        if not value.strip():
            log_to_file("[DEBUG] Empty string encountered, skip.")
            return
        
        # (3-2) headingがある場合
        if is_heading_start(value):
            heading_prefix, rest = split_heading_and_rest(value)# headingとその他を分離する
            if heading_prefix is None:
                pass 
            else:
                # (3-2-1) heading_prefixのみある場合 => heading_prefixをエンティティノードとして扱う
                log_to_file(f"Heading prefix entity: [entity(only heading prefix)] {heading_prefix}")
                h_idx = append_entity_info(heading_prefix, doc_created_indexes)
                add_original_sentence_to_current_item(value)
                add_node_to_current_item(h_idx, "entity") 
                if current_category_index:
                    append_edge_info("sub", current_category_index, h_idx, doc_created_indexes)

                # (3-2-2) restが文の場合("。"が含まれている) => 文の解析を行う
                if rest and "。" in rest:
                    sentences = rest.split("。")
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

                # (3-2-3) restが文でない場合("。"が含まれていない) => 全体(heading prefix + rest)をエンティティノードとして扱う
                else:
                    if rest:
                        e_val = heading_prefix + rest
                        log_to_file(f"Entity with heading: [entity(with heading)] {e_val}")
                        e_idx = append_entity_info(e_val, doc_created_indexes)
                        add_original_sentence_to_current_item(e_val)
                        add_node_to_current_item(e_idx, "entity")
                        if current_category_index:
                            append_edge_info("sub", current_category_index, e_idx, doc_created_indexes)
                return

        # (3-3) headingがない場合
        # (3-3-1) 文の場合("。"が含まれている) => 文の解析を行う
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
            # (3-3-2) 文でない場合("。"が含まれていない) => エンティティノードとして扱う
            log_to_file(f"[entity] {value}")
            e_idx = append_entity_info(value, doc_created_indexes)
            add_original_sentence_to_current_item(value)
            add_node_to_current_item(e_idx, "entity")
            if current_category_index:
                append_edge_info("sub", current_category_index, e_idx, doc_created_indexes)


def process_json(data, filename):
    '''
    JSONオブジェクトを受け取り、カテゴリノードを作って再帰的に処理を行った上で、
    類似度チェックや結果のログ出力をまとめて行う。
    - data : JSON形式のデータ
    - filename : ルートカテゴリの名前として使われる
    '''
    # (1) カテゴリ名(root)カテゴリノードを生成
    root_category_index = append_category_info(key=filename, level=3, cat_type='カテゴリ名', doc_created_node_indexes=None)
    log_to_file(f"Root category created: [category] '{filename}' (level=3, カテゴリ名)")

    # (2) 文書(doc)カテゴリノードを生成
    for doc_name, doc_value in data.items():
        doc_created_indexes = set()
        doc_category_index = append_category_info(key=doc_name,level=2, cat_type='文書名', doc_created_node_indexes=doc_created_indexes)
        finalize_current_item(doc_created_indexes)
        log_to_file(f"\nDocument category: [category] '{doc_name}' (level=2, 文書名)")
        append_edge_info("sub", root_category_index, doc_category_index)
        # (2-1) 文書カテゴリノードに含まれる下位構造を処理
        process_item("", doc_value, parent_category_index=doc_category_index, hierarchical_level=1,doc_created_indexes=doc_created_indexes)

        # (2-2) 文書ごとに作成されたノード情報を取得
        entity_nodes_global = get_entity_structure()
        predicate_nodes_global = get_predicate_structure()
        category_nodes_global = get_category_structure()
        
        doc_category_nodes = [ e for e in category_nodes_global if e["index"] in doc_created_indexes ]
        doc_entity_nodes   = [ e for e in entity_nodes_global  if e["index"] in doc_created_indexes ]
        doc_predicate_nodes= [ p for p in predicate_nodes_global if p["index"] in doc_created_indexes ]
        
        # (2-3) 類似度計算の後、equivalent関係の付与
        run_similarity_check(doc_entity_nodes, doc_predicate_nodes)
        create_equivalent_edges(doc_created_indexes)

        # (2-4) 文書ごとに得られた結果をログファイルに出力
        edge_global = get_edge()
        doc_edges = [ p for p in edge_global if p["index"] in doc_created_indexes ]
        log_and_print_final_results(doc_name, doc_category_nodes, doc_entity_nodes, doc_predicate_nodes, doc_edges)
        produce_similarity_report(doc_entity_nodes, doc_predicate_nodes) # 参考として類似度計算の結果
    
    finalize_current_item(doc_created_indexes)
    
    #クラスタリング方式のequivalent関係の付与
    #cluster_equivalent_edges(entity_nodes, predicate_nodes, n_clusters=5)
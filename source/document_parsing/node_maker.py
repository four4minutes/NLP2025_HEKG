# node_maker.py
# ノード(カテゴリ・エンティティ・述語構造)を管理するモジュール

index_number_node = 1  # グローバルインデックス用変数
category_structure = []  # カテゴリ情報を保存するリスト
entity_structure = []    # エンティティ情報を保存するリスト
predicate_structure = [] # 述語構造情報を保存するリスト

def append_category_info(key, level=0, cat_type='項目名', doc_created_node_indexes=None):
    '''
    カテゴリノードを生成し、category_structureに追加する関数。
    生成時にインデックスを一意に付与し、カテゴリレベルやタイトルなどの情報を保持する。
    - doc_created_node_indexes : 新しく生成されたノードのインデックスを記録するセット
    '''
    global index_number_node
    category_info = {
        'index': index_number_node,
        'hierarchical_level': level,
        'category_type': cat_type,
        'category_title': key
    }
    category_structure.append(category_info)
    if doc_created_node_indexes is not None:
        doc_created_node_indexes.add(index_number_node)

    current_index = index_number_node
    index_number_node += 1

    return current_index

def append_entity_info(entity_value, doc_created_node_indexes=None):
    '''
    エンティティノードを生成し、entity_structureに追加する関数。
    与えられた文字列やリスト（最初の要素）をエンティティとして登録する。
    - entity_value : エンティティとして扱いたい値（リストの場合は先頭のみ使用）
    - doc_created_node_indexes : 新しく生成されたノードのインデックスを記録するセット
    '''
    global index_number_node
    if isinstance(entity_value, list):
        entity_value = entity_value[0]  # リストの場合、先頭要素のみ使用
    entity_info = {
        'index': index_number_node,
        'hierarchical_level': 0,
        'entity': entity_value
    }
    entity_structure.append(entity_info)
    if doc_created_node_indexes is not None:
        doc_created_node_indexes.add(index_number_node)
    
    current_index = index_number_node
    index_number_node += 1

    return current_index

def append_predicate_structure(predicate_argument_structures, doc_created_node_indexes=None):
    '''
    述語構造（述語＋格要素など）を複数まとめて追加する関数。正規表現で述語や格要素を切り出し、
    predicate_structureリストに格納していく。
    - predicate_argument_structures : 複数の述語項構造文字列のリスト
    - doc_created_node_indexes : 生成したノードインデックスを保存しておくセット
    '''
    global index_number_node
    import re

    created_node_indexes = []

    for structure in predicate_argument_structures:
        # (1) 述語やガ格・修飾要素を正規表現で抽出
        predicate_match = re.match(r'(.*?)(\(述語\))', structure)
        agent_match = re.search(r'(\S+?\(ガ格\))', structure)
        modifier_match = re.search(r'(\S+?\(修飾\))', structure)
        arguments = re.findall(r'(\S+?\((?!ガ格|述語|修飾)\S+?\))', structure)

        # (2) 述語構造をまとめてdictionaryに格納
        predicate_info = {
            'index': index_number_node,
            'hierarchical_level': 0,
            'agent_argument': agent_match.group(0) if agent_match else "",
            'predicate': predicate_match.group(0) if predicate_match else "",
            'argument': arguments,
            'modifier': modifier_match.group(0) if modifier_match else ""
        }
        predicate_structure.append(predicate_info)
        if doc_created_node_indexes is not None:
            doc_created_node_indexes.add(index_number_node)
        
        created_node_indexes.append(index_number_node)
        index_number_node += 1

    return created_node_indexes

def get_category_structure():
    '''
    category_structureリスト（カテゴリノード情報）を返す。
    '''
    return category_structure

def get_entity_structure():
    '''
    entity_structureリスト（エンティティノード情報）を返す。
    '''
    return entity_structure

def get_predicate_structure():
    '''
    predicate_structureリスト（述語構造ノード情報）を返す。
    '''
    return predicate_structure

def get_node_content_by_index(node_index: int):
    '''
    ノードインデックスに対応するカテゴリ・エンティティ・述語の内容を取得して文字列として返す。
    見つからない場合は "unknown_idx" を返す。
    '''
    # (1) カテゴリで探索
    for cat in category_structure:
        if cat["index"] == node_index:
            return cat.get("category_title", f"category_idx:{node_index}")

    # (2) エンティティで探索
    for ent in entity_structure:
        if ent["index"] == node_index:
            return ent.get("entity", f"entity_idx:{node_index}")

    # (3) 述語構造で探索
    for pred in predicate_structure:
        if pred["index"] == node_index:
            return pred.get("predicate", f"predicate_idx:{node_index}")

    # いずれにも該当しない場合
    return f"unknown_idx:{node_index}"
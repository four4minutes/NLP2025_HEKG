# edge_maker.py
# ノード間のエッジを管理するモジュー

from source.document_parsing.node_maker import get_node_content_by_index
from source.document_parsing.logger import log_to_file

index_number_edge = 1  # グローバルエッジID
edge = []              # すべてのエッジを保存するリスト
auto_generated_edge_dictionary = []  #自動生成エッジ辞書

def append_edge_info(edge_type, from_node_index, to_node_index, doc_created_edge_indexes=None):
    '''
    新しいエッジを生成してedgeリストに追加する。
    - edge_type : エッジの種類 (str)
    - from_node_index : エッジの開始ノードインデックス (int)
    - to_node_index : エッジの終端ノードインデックス (int)
    - doc_created_edge_indexes : 生成したエッジのインデックスを記録するセット
    '''
    global index_number_edge
    edge_info = {
        'index': index_number_edge,
        'type': edge_type,
        'from': from_node_index,
        'to': to_node_index
    }
    edge.append(edge_info)

    if doc_created_edge_indexes is not None:
        doc_created_edge_indexes.add(index_number_edge)
    
    from_content = get_node_content_by_index(from_node_index)
    to_content = get_node_content_by_index(to_node_index)

    log_to_file(f"Creating edge : [{from_content}] --({edge_type})--> [{to_content}]")

    index_number_edge += 1

def get_edge():
    '''
    すべてのエッジリストを取得する。
    '''
    return edge

def get_auto_generated_edge_dictionary():
    """
    自動生成エッジのラベルや説明文をまとめた辞書を取得する。
    """
    return auto_generated_edge_dictionary

def add_auto_edge_label(label, explanation):
    """
    自動生成エッジ辞書に新しいラベルとその説明文を追加する。
    """
    for item in auto_generated_edge_dictionary:
        if item["label"] == label: # 既に存在するラベルならば何もせず終了
            return
    auto_generated_edge_dictionary.append({"label": label, "explanation": explanation})
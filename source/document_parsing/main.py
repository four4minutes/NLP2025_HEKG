# main.py

import json
import os
from source.document_parsing.logger import initialize_logger
from source.document_parsing.node_maker import get_category_structure, get_entity_structure, get_predicate_structure
from source.document_parsing.edge_maker import get_edge, get_auto_generated_edge_dictionary
from json_processor import process_json
from csv_exporter import export_to_csv

def main():
    '''
    メインエントリーポイントとなる関数。JSONファイルを読み込み、
    全体の処理を実行して最終的にCSVファイルへ結果を出力する。
    - JSONファイル名を指定し、読み込んだ後はprocess_jsonに渡す。
    - ノードやエッジの最終結果をCSVとして保存する。
    '''
    # (1) ロガー初期化
    initialize_logger()

    # (2) JSONデータのロード
    input_filename = "test.json"
    filename_only = os.path.splitext(input_filename)[0]
    with open(input_filename, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # (3) JSON全体の処理
    process_json(data, filename_only)

    # (4) 処理結果をCSV形式で出力
    category_list = get_category_structure()
    entity_list = get_entity_structure()
    predicate_list = get_predicate_structure()
    edge_list = get_edge()
    new_relation_list = get_auto_generated_edge_dictionary()

    export_to_csv(category_list, entity_list, predicate_list, edge_list, new_relation_list, "results")

if __name__ == "__main__":
    main()
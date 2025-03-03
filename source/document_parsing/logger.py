# logger.py

import os
from datetime import datetime


LOG_FILE_PATH = None # グローバル変数でログファイルの保存場所設定
TOKEN_USAGE_FILE = "token_usage.txt" # トークンの使用量記録用ログファイル

def initialize_logger():
    '''
    ロガーファイルを初期化し、logsディレクトリを作成した上で日付入りのログファイルを準備する。
    '''
    global LOG_FILE_PATH

    try:
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)


        # 現在時刻でログファイル名生成
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        LOG_FILE_PATH = os.path.join(log_dir, f"{current_time}.log")

    except Exception as e:
        print(f"Error initializing logger: {e}")

def log_to_file(message: str):
    '''
    デバッグや処理経過をログファイルに書き込むための関数。
    - message : 書き込む文字列（英語出力想定）
    '''
    try:
        if LOG_FILE_PATH is None:
            raise ValueError("Logger has not been initialized. Call 'initialize_logger()' first.")

        with open(LOG_FILE_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(message + "\n")

    except Exception as e:
        print(f"Error logging to file: {e}")

def log_token_usage(token_count: int):
    '''
    OpenAI APIのトークン使用量を記録する関数。既存のtotal値に加算してファイルに書き戻す。
    - token_count : 今回使用したトークン数
    '''
    try:
        lines = []
        total_tokens = 0
        try:
            # (1) ファイル読み込み
            with open(TOKEN_USAGE_FILE, "r", encoding="utf-8") as file:
                lines = file.readlines()

            # (2) 既存の情報取得
            updated_lines = []
            for line in lines:
                if line.startswith("総合トークン使用量 :"):
                    total_tokens = int(line.split(":")[1].strip()) 
                else:
                    updated_lines.append(line)
            lines = updated_lines

        except FileNotFoundError:
            pass

        # (3) 現在のトークン使用量を追加
        total_tokens += token_count
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_entry = f"{now} : {token_count}\n"

        # (4) ファイル書き込み
        with open(TOKEN_USAGE_FILE, "w", encoding="utf-8") as file:
            file.write(f"総合トークン使用量 : {total_tokens}\n")
            file.write(new_entry)
            file.writelines(lines)

    except Exception as e:
        print(f"Error logging token usage: {e}")

def log_and_print_final_results(doc_name,category_structure, entity_structure, predicate_structure, edge):
    '''
    カテゴリ・エンティティ・述語構造・エッジの最終結果をログファイルに記録するための関数。
    - doc_name : 処理対象のドキュメント名
    '''
    log_to_file(f"\n===== [parsing results for document: {doc_name}] =====")

    log_to_file("\n=== Category Structure List ===")
    for item in category_structure:
        log_to_file(str(item))

    log_to_file("\n=== Entity Structure List ===")
    for item in entity_structure:
        log_to_file(str(item))

    log_to_file("\n=== Predicate Structure List ===")
    for item in predicate_structure:
        log_to_file(str(item))

    log_to_file("\n=== Edge List ===")
    for item in edge:
        log_to_file(str(item))
        
    log_to_file("=============================================\n")

def produce_similarity_report(entity_nodes, predicate_nodes):
    '''
    エンティティ・述語ノードの類似度ログを出力する。
    '''
    from source.document_parsing.similarity_based_equivalent_extraction import (
        similarity_score_cache, similarity_registration_logs,
        gather_all_nodes, SIMILARITY_THRESHOLD_LOG
    )

    log_to_file("\n=== Similarity Calculation Report ===\n")
    for line in similarity_registration_logs:
        log_to_file(line)

    all_nodes = gather_all_nodes(entity_nodes, predicate_nodes)

    for node_i in all_nodes:
        idx_i = node_i["index"]
        text_i = node_i["text"]
        if idx_i not in similarity_score_cache:
            continue

        above_03 = [
            (sc, j, t) for (sc, j, t) in similarity_score_cache[idx_i]
            if sc >= SIMILARITY_THRESHOLD_LOG
        ]
        if not above_03:
            continue

        log_to_file(f"\n[base node idx={idx_i}, text='{text_i}'] :")
        for (sc, j_idx, j_text) in above_03:
            log_to_file(f"   -> score={sc:.3f}, idx={j_idx}, text='{j_text}'")

def record_similarity_logs(log_lines):
    '''
    similarity_calculation.run_similarity_check()からの類似度情報をログファイルに書き込む
    '''
    for line in log_lines:
        log_to_file(line)
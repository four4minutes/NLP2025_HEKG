# time_evolution_extraction.py
import re
import math
from collections import defaultdict, Counter
from openai import OpenAI
from source.document_parsing.logger import log_to_file
from source.document_parsing.edge_maker import append_edge_info
from source.document_parsing.text_utils import (
    convert_predicate_to_text,
    STOP_WORDS
)

client = OpenAI()

def tokenize_sentence(lines_for_tokenize):
    """
    1) lines_for_tokenize: ["(3) エスカレーターが逆走した", ...] 형태
    2) OpenAI API를 사용하여, 단어 토큰화 + 동사 기본형 변환
    3) 리턴: [(node_idx, [token1, token2, ...]), ...],  그리고 vocab_dict
    (프롬프트와 예제는 기존 로직 유지)
    """

    # (A) 예시(단일) 준비
    example = {
        "input": (
            "(1) 定員以上の乗客が乗り込んだ",
            "(2) エスカレーターが停止し",
            "(3) エスカレーターが逆走した",
            "(4) 客達が仰向けに折り重なる",
            "(5) 客達が倒れ",
            "(6) 10人がエスカレーターの段差に体をぶつけ",
            "(7) 10人が足首を切ったり",
            "(8) 10人が軽い打撲のけがをした",
            "(9) エスカレーターが自動停止し",
            "(10) ブレーキが効かず",
            "(11) エスカレーターが逆走・降下した",
            "(12) 停止",
            "(13) 逆走が発生した",
            "(14) エスカレーターが逆走",
            "(15) 皆が極めて高い密度で後ろ向きで折り重なる",
            "(16) 皆が倒れた",
            "(17) 群集雪崩が発生した"
        ),
        "output": (
            "(1) 定員 | 以上 | の | 乗客 | が | 乗り込む\n"
            "(2) エスカレーター | が | 停止 | する\n"
            "(3) エスカレーター | が | 逆走 | する\n"
            "(4) 客達 | が | 仰向け | に | 折り重なる\n"
            "(5) 客達 | が | 倒れる\n"
            "(6) 10人 | が | エスカレーター | の | 段差 | に | 体 | を | ぶつける\n"
            "(7) 10人 | が | 足首 | を | 切る\n"
            "(8) 10人 | が | 軽い | 打撲 | の | けが | を | する\n"
            "(9) エスカレーター | が | 自動 | 停止 | する\n"
            "(10) ブレーキ | が | 効く | ない\n"
            "(11) エスカレーター | が | 逆走 | ・ | 降下 | する\n"
            "(12) 停止\n"
            "(13) 逆走 | が | 発生 | する\n"
            "(14) エスカレーター | が | 逆走\n"
            "(15) 皆 | が | 極めて | 高い | 密度 | で | 後ろ向き | で | 折り重なる\n"
            "(16) 皆 | が | 倒れる\n"
            "(17) 群集雪崩 | が | 発生 | する"
        )
    }

    system_prompt = (
        "[指示]\n"
        "あなたは日本語の入力文を単語トークンに分割し、動詞の活用形を基本形に変換して返すアシスタントです。\n"
        "出力時には、(n) を行頭に付与したうえで、トークンを ' | ' で区切ってください。\n"
        "動詞が過去形・連用形の場合はできるだけ基本形に直してください。\n"
        "[入力形式] : 先頭の()にインデックス番号、その後にテキスト文\n"
        "(index) テキスト文\n"
        "(index) テキスト文\n"
        "[出力形式] : 先頭の()にインデックス番号(入力と同様に)、その後に処理結果\n"
        "(index) トークン | トークン | トークン\n"
        "(index) トークン | トークン | トークン\n"
    )

    messages = []
    # 1) system
    messages.append({"role": "system", "content": system_prompt})
    # 2) user - 예제의 input
    ex_input_text = (
        "以下は処理の例文です。\n\n"
        f"input:{example['input']}\n"
    )
    messages.append({"role": "user", "content": ex_input_text})
    # 3) assistant - 예제의 output
    ex_output_text = example["output"]
    messages.append({"role": "assistant", "content": ex_output_text})

    # (B) 실제 유저 요청 (토큰화할 노드들)
    user_prompt = (
        "上記の例を参考に、以下の各行をトークンに分割し、"
        "動詞は基本形に変換して出力してください。\n\n"
        + "\n".join(lines_for_tokenize)
    )
    messages.append({"role": "user", "content": user_prompt})

    # (C) API 호출
    client_api = client.chat.completions
    try:
        response = client_api.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
    except Exception as e:
        log_to_file(f"[ERROR] OpenAI API 호출失敗: {e}")
        log_to_file("----------------------------")
        return [], {}

    # (D) 결과 파싱
    output_lines = content.split("\n")
    result = []     # [(node_idx, [tokens...])]
    vocab_dict = {} # { token : 전역 등장 횟수 }

    index_pattern = re.compile(r'^\(\s*(\d+)\s*\)\s*(.*)$')

    for line_str in output_lines:
        line_str = line_str.strip()
        if not line_str:
            continue

        m = index_pattern.match(line_str)
        if m:
            node_idx = int(m.group(1))
            tokens_str = m.group(2)
        else:
            node_idx = 0
            tokens_str = line_str

        tokens_in_line = [t.strip() for t in tokens_str.split("|") if t.strip()]

        # stop words 제외, vocab_dict 갱신
        filtered = []
        for tk in tokens_in_line:
            if tk in STOP_WORDS:
                continue
            vocab_dict[tk] = vocab_dict.get(tk, 0) + 1
            filtered.append(tk)

        result.append((node_idx, filtered))

    return result, vocab_dict


def node_vector_space_model(result, vocab_dict, only_tf=False):
    """
    1) result: [(node_idx, [token1, token2, ...]), ...]
    2) vocab_dict: { token: 전역 등장 횟수 }
    3) only_tf=False => TF-IDF, only_tf=True => TF만
    
    리턴:
      - node_term_vector: { node_idx: [w_i1, w_i2, ..., w_ik] }
      - cos_sim_dict: { (a,b): cos_sim_val }
      - sorted_vocab: vocab 정렬 리스트 (필요시)
    """
    node_token_freq = defaultdict(Counter)
    node_indices = []
    for (nidx, tokens) in result:
        if nidx > 0:
            node_indices.append(nidx)
            for tk in tokens:
                node_token_freq[nidx][tk] += 1

    node_indices = list(set(node_indices))
    N = len(node_indices)

    # (A) node별 max freq
    node_max_freq = {}
    for n in node_indices:
        c = node_token_freq[n]
        node_max_freq[n] = max(c.values()) if c else 1

    # (B) df_x: 단어 x가 등장한 노드 수
    df_x_dict = defaultdict(int)
    for x in vocab_dict.keys():
        cnt = 0
        for (nidx, tokens) in result:
            if nidx == 0:
                continue
            if x in tokens:
                cnt += 1
        df_x_dict[x] = cnt

    # (C) vocab 정렬
    sorted_vocab = sorted(vocab_dict.keys())
    vocab_index_map = {tok: i for i, tok in enumerate(sorted_vocab)}

    # (D) 벡터화
    node_term_vector = {}
    for n in node_indices:
        freq_map = node_token_freq[n]
        max_freq_i = node_max_freq[n]
        vlen = len(sorted_vocab)
        weighted_vec = [0.0] * vlen

        for (token, freq_i_x) in freq_map.items():
            tf = freq_i_x / max_freq_i
            if only_tf:
                w_ix = tf
            else:
                df_x = df_x_dict[token] if token in df_x_dict else 1
                if df_x == 0:
                    df_x = 1
                idf = math.log(N / df_x)
                w_ix = tf * idf

            pos = vocab_index_map[token]
            weighted_vec[pos] = w_ix

        node_term_vector[n] = weighted_vec

    # (E) 코사인 유사도 계산
    def cos_sim(vecA, vecB):
        dot_val = 0.0
        normA = 0.0
        normB = 0.0
        for i in range(len(vecA)):
            dot_val += vecA[i] * vecB[i]
            normA += vecA[i] * vecA[i]
            normB += vecB[i] * vecB[i]
        if normA == 0 or normB == 0:
            return 0.0
        return dot_val / math.sqrt(normA * normB)

    cos_sim_dict = {}
    sorted_nodes = sorted(node_indices)
    for i in range(len(sorted_nodes)):
        for j in range(i+1, len(sorted_nodes)):
            a = sorted_nodes[i]
            b = sorted_nodes[j]
            sim_val = cos_sim(node_term_vector[a], node_term_vector[b])
            cos_sim_dict[(a, b)] = sim_val

    return node_term_vector, cos_sim_dict, sorted_vocab


def calculate_event_evolution_relationship(entity_nodes, predicate_nodes, original_sentences, doc_created_edge_indexes):
    """
    1) 술어/엔티티 노드 -> lines_for_tokenize
    2) tokenize_sentence(...) 호출 -> (result, vocab_dict) 받음
    3) node_vector_space_model(...) 호출 -> 벡터화 + 코사인 유사도 계산
    4) 이후 필요시 로깅, 혹은 결과를 반환
    """

    log_to_file("----------------------------")

    # (A) 술어 노드 정렬
    sorted_predicates = sorted(predicate_nodes, key=lambda x: x["index"])

    # (B) 노드 텍스트 모으기
    lines_for_tokenize = []
    for ent_node in entity_nodes:
        text_ent = ent_node.get("entity", "").strip()
        if text_ent:
            node_idx = ent_node["index"]
            lines_for_tokenize.append(f"({node_idx}) {text_ent}")
    for pred_node in sorted_predicates:
        pred_text = convert_predicate_to_text(pred_node).strip()
        if pred_text:
            node_idx = pred_node["index"]
            lines_for_tokenize.append(f"({node_idx}) {pred_text}")

    # 노드가 없다면 종료
    if not lines_for_tokenize:
        log_to_file("[INFO] 토큰화할 노드 텍스트가 없습니다.")
        log_to_file("----------------------------")
        return

    # (C) 토크나이즈 함수 호출
    result, vocab_dict = tokenize_sentence(lines_for_tokenize)
    if not result:
        log_to_file("[INFO] tokenization failed or empty result.")
        return

    # (D) node_vector_space_model 호출 (TF or TF-IDF 결정 가능)
    ONLY_TF_TERM_WEIGHT = False  # 혹은 True
    node_term_vector, cos_sim_dict, sorted_vocab = node_vector_space_model(result, vocab_dict, only_tf=ONLY_TF_TERM_WEIGHT)

    log_to_file("----------------------------")
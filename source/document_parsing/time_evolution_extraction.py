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

TIME_EVOLUTION_RELATIONSHIP_THRESHOLDING = 0.60

def tokenize_sentence(lines_for_tokenize, node_type_dict):
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

        if node_type_dict.get(node_idx) == "predicate" and filtered:
            filtered.pop()  # 마지막 토큰 제거

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

    return cos_sim_dict, sorted_nodes

def build_timestamp_info(item_nodes, item_edges):
    """
    1) info_SpecificTime 엣지로부터 timestamp 노드 찾기 (edge["from"]가 timestamp)
    2) item_node_indices를 이용하여 각 노드별 대표 timestamp 노드를 찾는다.
    3) timestamp 노드들을 정렬하여 rank를 부여.
    4) group_map[node_idx] = {
         "rep_node": 대표 timestamp 노드 인덱스 (또는 None),
         "rank": 대표 timestamp 노드의 rank (int),
         "group_size": 그 timestamp 그룹의 노드 수,
         "timestamp_count": 전체 timestamp 노드의 개수
       }
    => 이 구조만 넘겨주면, calculate_node_temporal_proximity에서 node a, b 각각을 보고
       d 계산에 필요한 모든 정보를 얻을 수 있음.
    """

    # (A) info_SpecificTime 관계의 출발점 -> timestamp 노드
    timestamp_nodes = set()
    for e in item_edges:
        if e["type"] == "info_SpecificTime" and e["from"] in item_nodes:
            timestamp_nodes.add(e["from"])

    # (B) timestamp_count
    timestamp_count = len(timestamp_nodes)

    # (C) timestamp 노드를 정렬, rank 부여
    sorted_timestamps = sorted(timestamp_nodes)
    timestamp_rank = {}
    for i, tnode in enumerate(sorted_timestamps):
        timestamp_rank[tnode] = i  # rank 0,1,2,...

    # (D) 각 노드별 대표 timestamp 찾기
    #     (인덱스가 작거나 같은 timestamp 노드 중 최댓값)
    rep_node = {}
    for idx in item_nodes:
        if idx in timestamp_nodes:
            rep_node[idx] = idx
        else:
            candidate = None
            for tnode in sorted_timestamps:
                if tnode <= idx:
                    candidate = tnode
                else:
                    break
            rep_node[idx] = candidate  # 없으면 None

    # (E) 같은 rep_node를 공유하는 노드끼리 그룹 -> group_map[rep_node_idx] = [node1,node2,...]
    from collections import defaultdict
    big_group_map = defaultdict(list)
    for idx in item_nodes:
        r = rep_node[idx]
        if r is not None:
            big_group_map[r].append(idx)

    # (F) group_map[node] = { "rep_node":..., "rank":..., "group_size":..., "timestamp_count":... }
    group_map = {}
    for idx in item_nodes:
        r = rep_node[idx]
        # rank: r이 None이면 0
        node_rank = timestamp_rank.get(r, 0) if r else 0
        # group_size: r가 있으면 big_group_map[r]의 길이, 없으면 0
        grp_size = len(big_group_map[r]) if r else 0

        group_map[idx] = {
            "rep_node": r,                 # None or idx of timestamp
            "rank": node_rank,             # int
            "group_size": grp_size,        # int
            "timestamp_count": timestamp_count
        }

    return group_map

def calculate_node_temporal_proximity(a_idx, b_idx, group_map, alpha=0.5):
    """
    group_map: build_timestamp_info(...)가 반환한 사전
      group_map[node_idx] = {
         "rep_node": ...,
         "rank": ...,
         "group_size": ...,
         "timestamp_count": ...
      }
    => 이를 통해 time_evolution_score 계산에 필요한 정보를 얻는다.

    규칙:
      1) timestamp_count = 0 -> return 1.0
      2) 같음timestamp => group_size>10 -> d= (1000/(group_size-1))*(b-a), else d=100*(b-a)
      3) 다른timestamp => d=100*(b-a)+1000*(|rankA-rankB|)
      4) T= timestamp_count*1000
      => exp(-alpha*(d/T))
    """
    # (A) timestamp_count
    timestamp_count = group_map[a_idx]["timestamp_count"]  # a,b 동일한 timestamp_count
    if timestamp_count == 0:
        return 1.0
    T = timestamp_count * 1000

    # (B) rep_node + rank + group_size
    a_rep = group_map[a_idx]["rep_node"]
    b_rep = group_map[b_idx]["rep_node"]
    a_rank = group_map[a_idx]["rank"]
    b_rank = group_map[b_idx]["rank"]
    group_size = group_map[a_idx]["group_size"]

    # (C) 인덱스 차
    m = b_idx - a_idx  # a_idx<b_idx라고 가정
    # 만약 a_idx>b_idx 가능성이 있으면 if m<0: m=-m

    # (D) d 계산
    if a_rep is not None and b_rep is not None and a_rep == b_rep:
        # 같은 timestamp
        if group_size > 10:
            d = (1000.0 / (group_size - 1)) * m
        else:
            d = 100*m
    else:
        # 다른 timestamp
        rank_diff = abs(b_rank - a_rank)
        d = 100*m + 1000*rank_diff

    # (E) 최종
    return math.exp(-alpha*(d / T))

def calculate_node_distributional_proximity(node_a_idx, node_b_idx, N, beta=0.5):
    """
    node_a_idx < node_b_idx 라고 가정.
    m = node_b_idx - node_a_idx
    distributional_proximity = e^((-1)*beta*(m/N))
    """
    m = node_b_idx - node_a_idx
    if m < 0:
        m = -m  # 혹시나 a_idx > b_idx인 경우를 방어적으로 처리
    dp = math.exp(-beta * (m / N))
    return dp

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
    node_text_dict = {}
    node_type_dict = {}
    agent_arg_dict = {}

    """
    for ent_node in entity_nodes:
        text_ent = ent_node.get("entity", "").strip()
        if text_ent:
            node_idx = ent_node["index"]
            lines_for_tokenize.append(f"({node_idx}) {text_ent}")
            node_text_dict[node_idx] = text_ent
            node_type_dict[node_idx] = "entity"
    """

    for pred_node in sorted_predicates:
        pred_text = convert_predicate_to_text(pred_node).strip()
        if pred_text:
            node_idx = pred_node["index"]
            lines_for_tokenize.append(f"({node_idx}) {pred_text}")
            node_text_dict[node_idx] = pred_text
            node_type_dict[node_idx] = "predicate"
        agent_arg = pred_node.get("agent_argument", "")
        match = re.match(r'^(.*)\(ガ格\)$', agent_arg.strip())
        if match:
            agent_arg_dict[node_idx] = match.group(1).strip()
        else:
            agent_arg_dict[node_idx] = agent_arg.strip()

    # 노드가 없다면 종료
    if not lines_for_tokenize:
        log_to_file("[INFO] 토큰화할 노드 텍스트가 없습니다.")
        log_to_file("----------------------------")
        return

    # (C) 토크나이즈 함수 호출
    result, vocab_dict = tokenize_sentence(lines_for_tokenize, node_type_dict)
    if not result:
        log_to_file("[INFO] tokenization failed or empty result.")
        return

    # (D) node_vector_space_model 호출 (TF or TF-IDF 결정 가능)
    ONLY_TF_TERM_WEIGHT = True 
    cos_sim_dict, sorted_nodes = node_vector_space_model(result, vocab_dict, only_tf=ONLY_TF_TERM_WEIGHT)

    # (F) 현재 item에 속한 edge 필터링
    from source.document_parsing.edge_maker import get_edge
    all_edges = get_edge()
    item_edges = [e for e in all_edges if (e["from"] in sorted_nodes or e["to"] in sorted_nodes)]
    group_map = build_timestamp_info(sorted_nodes, item_edges)

    for (a_idx,b_idx),cos_sim_val in sorted(cos_sim_dict.items()):

        time_evolution_score = 0

        # 인덱스 값의 차이가 1이라면 score에 보너스 0.3
        if (b_idx-a_idx==1):
            time_evolution_score += 0.3
            # 주어가 같다면 보너스 0.3
            if (agent_arg_dict.get(a_idx, "") != "" and agent_arg_dict[a_idx] == agent_arg_dict.get(b_idx, "")):
                time_evolution_score += 0.3

        # distributional_proximity 계산 (N은 node_indices 길이)
        temporal_prox = calculate_node_temporal_proximity(a_idx, b_idx, group_map, alpha=0.5)
        distributional_prox = calculate_node_distributional_proximity(a_idx, b_idx, N= len(sorted_nodes), beta=0.5)
        time_evolution_score += cos_sim_val * temporal_prox * distributional_prox


        if time_evolution_score >= TIME_EVOLUTION_RELATIONSHIP_THRESHOLDING:
            append_edge_info("next_TimeStamp", a_idx, b_idx, doc_created_edge_indexes)

        if time_evolution_score > 0:
            textA = node_text_dict.get(a_idx, "N/A")
            textB = node_text_dict.get(b_idx, "N/A")
            log_to_file(
                f"  Node#{a_idx}({textA}) -> Node#{b_idx}({textB}) | "
                f"cos_sim={cos_sim_val:.3f}, temp_prox={temporal_prox:.3f}, distr_prox={distributional_prox:.3f}, "
                f"time_evolution_score={time_evolution_score:.3f}"
            )

    log_to_file("----------------------------")
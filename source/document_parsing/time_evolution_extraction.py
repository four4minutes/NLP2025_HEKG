# time_evolution_extraction.py
# ノード間の時系列的な繋がりを推定し、next_TimeStampエッジを生成するモジュール

import re
import math
from collections import defaultdict, Counter
from openai import OpenAI
from source.document_parsing.logger import log_to_file
from source.document_parsing.edge_maker import append_edge_info
from source.document_parsing.text_utils import convert_predicate_to_text, STOP_WORDS

client = OpenAI()

TIME_EVOLUTION_RELATIONSHIP_THRESHOLDING = 0.60

def tokenize_sentence(lines_for_tokenize, node_type_dict):
    '''
    与えられたテキスト行それぞれに対してトークナイズと動詞の基本形変換を行う関数。
    - lines_for_tokenize : "(index) text" 形式の複数行
    - node_type_dict : ノード種別を追跡する辞書 {index: "predicate"/"entity"...}
    - return : (result, vocab_dict)
       result : [(node_idx, [tokens...]), ...]
       vocab_dict : 全トークンの登場回数などを管理する辞書
    '''

    # (1) GPTに与えるプロンプト
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
    messages = []
    messages.append({"role": "system", "content": system_prompt})
    
    ex_input_text = ("以下は処理の例文です。\n\n"f"input:{example['input']}\n")
    messages.append({"role": "user", "content": ex_input_text})
    
    ex_output_text = example["output"]
    messages.append({"role": "assistant", "content": ex_output_text})

    user_prompt = ("上記の例を参考に、以下の各行をトークンに分割し、""動詞は基本形に変換して出力してください。\n\n"+"\n".join(lines_for_tokenize))
    messages.append({"role": "user", "content": user_prompt})

    # (2) OpenAI APIを呼び出す
    client_api = client.chat.completions
    try:
        response = client_api.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
    except Exception as e:
        log_to_file(f"[ERROR] OpenAI API call failed: {e}")
        return [], {}

    # (3) 結果からトークンを抽出
    output_lines = content.split("\n")
    result = [] 
    vocab_dict = {} 

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

        filtered = []
        for tk in tokens_in_line:
            if tk in STOP_WORDS:
                continue
            vocab_dict[tk] = vocab_dict.get(tk, 0) + 1
            filtered.append(tk)

        if node_type_dict.get(node_idx) == "predicate" and filtered:
            filtered.pop() 

        result.append((node_idx, filtered))

    return result, vocab_dict


def node_vector_space_model(result, vocab_dict, only_tf=False):
    '''
    ノードごとにTFまたはTF-IDFベクトルを構築し、ノード間のコサイン類似度を計算する。
    - result: [(node_idx, [tokens...])]
    - vocab_dict: { token: 全体の出現数 }
    - only_tf: Trueの場合はTFのみ、FalseならTF-IDF
    - return: (cos_sim_dict, sorted_nodes)
    '''
    node_token_freq = defaultdict(Counter)
    node_indices = []
    for (nidx, tokens) in result:
        if nidx > 0:
            node_indices.append(nidx)
            for tk in tokens:
                node_token_freq[nidx][tk] += 1

    node_indices = list(set(node_indices))
    N = len(node_indices)

    # (1) nodeごとのnode_max_freqを計算する
    node_max_freq = {}
    for n in node_indices:
        c = node_token_freq[n]
        node_max_freq[n] = max(c.values()) if c else 1

    # (2) df_xを計算する: 単語xが出現するノードの数
    df_x_dict = defaultdict(int)
    for x in vocab_dict.keys():
        cnt = 0
        for (nidx, tokens) in result:
            if nidx == 0:
                continue
            if x in tokens:
                cnt += 1
        df_x_dict[x] = cnt

    sorted_vocab = sorted(vocab_dict.keys())
    vocab_index_map = {tok: i for i, tok in enumerate(sorted_vocab)}

    # (3) ノード単語ベクトルを生成する
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

    # (4) コサイン類似度を計算する関数
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

    # (5) ノード単語ベクトル間のコサイン類似度を計算する
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
    '''
    info_SpecificTimeエッジからタイムスタンプノードを抽出し、各ノードがどのタイムスタンプに属するかを決める。
    - item_nodes : ノードのインデックス一覧
    - item_edges : エッジリスト
    - return : group_map（各ノードに対応するタイムスタンプやランク情報を収めた辞書）
    '''

    # (1) タイムスタンプを持つノードを探す
    timestamp_nodes = set()
    for e in item_edges:
        if e["type"] == "info_SpecificTime" and e["from"] in item_nodes:
            timestamp_nodes.add(e["from"])

    timestamp_count = len(timestamp_nodes)

    sorted_timestamps = sorted(timestamp_nodes)
    timestamp_rank = {}
    for i, tnode in enumerate(sorted_timestamps):
        timestamp_rank[tnode] = i  # rank 0,1,2,...

    # (2) タイムスタンプ別に代表ノードを指定し、他のノードらをグループ化する
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
            rep_node[idx] = candidate 

    from collections import defaultdict
    big_group_map = defaultdict(list)
    for idx in item_nodes:
        r = rep_node[idx]
        if r is not None:
            big_group_map[r].append(idx)

    group_map = {}
    for idx in item_nodes:
        r = rep_node[idx]
        node_rank = timestamp_rank.get(r, 0) if r else 0
        grp_size = len(big_group_map[r]) if r else 0

        group_map[idx] = {
            "rep_node": r,                 
            "rank": node_rank,             
            "group_size": grp_size,        
            "timestamp_count": timestamp_count
        }

    return group_map

def calculate_node_temporal_proximity(a_idx, b_idx, group_map, alpha=0.5):
    '''
    タイムスタンプ情報をもとに、ノード間の時間的近さ(temporal_proximity)を推定する関数。
    - alpha : dに対する重み
    '''

    # (1) 計算の準備
    timestamp_count = group_map[a_idx]["timestamp_count"] 
    if timestamp_count == 0:
        return 1.0
    T = timestamp_count * 1000

    a_rep = group_map[a_idx]["rep_node"]
    b_rep = group_map[b_idx]["rep_node"]
    a_rank = group_map[a_idx]["rank"]
    b_rank = group_map[b_idx]["rank"]
    group_size = group_map[a_idx]["group_size"]

    m = b_idx - a_idx  

    # (2) temporal_proximityの計算
    if a_rep is not None and b_rep is not None and a_rep == b_rep:
        if group_size > 10:
            d = (1000.0 / (group_size - 1)) * m
        else:
            d = 100*m
    else:
        rank_diff = abs(b_rank - a_rank)
        d = 100*m + 1000*rank_diff

    return math.exp(-alpha*(d / T))

def calculate_node_distributional_proximity(node_a_idx, node_b_idx, N, beta=0.5):
    '''
    ノードインデックスの差を見て分布上の近さ(distributional_proximity)を評価する関数。
    - N : 全ノード数
    '''
    m = node_b_idx - node_a_idx
    if m < 0:
        m = -m  
    dp = math.exp(-beta * (m / N))
    return dp

def GPT_inspection(original_sentences, predicate_nodes, time_evolution_edges):
    '''
    GPTに対して、与えられた原文とノード、および既存の時間関係を入力し、
    見落としている時間関係が無いかチェックさせる関数。
    - original_sentences : 項目全体の原文文字列
    - predicate_nodes : 述語ノードのリスト [{'index':..., 'predicate':...}, ...]
    - time_evolution_edges : すでに検出済みの時間関係 (from_idx, to_idx) のリスト
    戻り値 : 新たに発見された(かもしれない)時間関係のリスト
    '''

    # (1) GPTに与えるプロンプト
    system_prompt = (
        "[指示]\n"
        "あなたは時間関係が適切に付与されているかを検査するアシスタントです。\n"
        "ここで言う「時間関係」とは、テキスト内に描写された事象を時間の流れに沿って並べ、"
        "どの順番で事象が起きたかを定義する関係を指します。\n"
        "例えば、「コンビニに行き、おにぎりとカップラーメンを買い、家に戻った。」という原文があるとします。\n"
        "ここでは (1)「コンビニに行き」、(2)「おにぎりとカップラーメンを買い」、(3)「家に戻った」の三つのノードがあると考えられ、"
        "それらの間には (1)→(2)→(3) という時間関係が想定されます。\n"
        "原文からノードへの分割やノード間の時間関係の付与は別のタスクで行われますが、必ずしも完璧とは限りません。\n"
        "そこで、あなたの仕事は、既に付与された時間関係を点検し、"
        "もし見落とされていると思われる関係があれば指摘することです。\n"
        "補足として、時間関係はノード間の直接的な時間関係だけを考えます。"
        "例えば先の例では (1)→(2)→(3) なので、(1)→(3) は時間的には正しい流れですが、(1)→(2) と (2)→(3) の 2 つの関係が存在している場合、"
        "(1) と (3) の間の時間関係は必ず (2) を介して表現することにします。\n\n"
        "[入力形式]\n"
        "- 原文、ノード、ノード間の時間関係が提示されます\n"
        "原文 : テキスト\n"
        "ノード : (index) テキスト, (index) テキスト, (index) テキスト\n"
        "→ 例： (1) コンビニに行く, (2) おにぎりを買う, (3) 家に戻る\n"
        "時間関係 : (index, index), (index, index)\n"
        "→ 例： (1,2), (2,3)\n"
        "各カッコの左側を「より早い事象」、右側を「より後の事象」として記述してください。"
        "複数のノード・関係はコンマ区切りで列挙します。\n\n"
        "[出力形式]\n"
        "- 追加で抽出（つまり見落とされていた）と思われる時間関係を列挙してください。\n"
        "- もし見落としが無い場合は「無し」とだけ出力してください。\n"
        "- 見落とされていると考えられる関係が複数ある場合は、(index, index)をコンマで並べて列挙してください。"
    )

    user_prompt = ""
    user_prompt += f"原文 : {original_sentences.strip()}\n\n"

    user_prompt += "ノード : "
    node_str_list = []
    for nd in predicate_nodes:
        idx = nd["index"]
        text_val = nd.get("predicate", nd.get("entity",""))
        node_str_list.append(f"({idx}) {text_val}")
    user_prompt += ", ".join(node_str_list) + "\n\n"

    user_prompt += "時間関係 : "
    if time_evolution_edges:
        edge_str_list = []
        for (f_idx, t_idx) in time_evolution_edges:
            edge_str_list.append(f"({f_idx}, {t_idx})")
        user_prompt += ", ".join(edge_str_list)
    else:
        user_prompt += "無し"
    user_prompt += "\n"

    # (2) OpenAI APIを呼び出す
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    client_api = client.chat.completions
    try:
        response = response = client_api.create(
            model="gpt-4o",  
            messages=messages,
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
    except Exception as e:
        log_to_file(f"[ERROR] GPT_inspection API call failed: {e}")
        return []

    # (3) 出力を解析し、見落としが無ければ[]、(x,y)形式であればリストに追加して返す
    if content.strip() == "無し": # 見落としなし
        return []  

    pair_pattern = re.compile(r'\(\s*(\d+)\s*,\s*(\d+)\s*\)') # 正規表現で抽出
    new_relations = []
    for match in pair_pattern.finditer(content):
        a_str = match.group(1)
        b_str = match.group(2)
        try:
            a_idx = int(a_str)
            b_idx = int(b_str)
            new_relations.append((a_idx, b_idx))
        except ValueError:
            pass

    return new_relations

def calculate_event_evolution_relationship(entity_nodes, predicate_nodes, original_sentences, doc_created_edge_indexes):
    '''
    ある項目（item）に含まれるノードを対象に、時間的な進行関係を推定し、next_TimeStampエッジを付与する。
    - entity_nodes : その項目に含まれるエンティティノード
    - predicate_nodes : その項目に含まれる述語ノード
    - original_sentences : 項目全体の元文など
    - doc_created_edge_indexes : 生成したエッジのインデックスを追跡するセット
    '''

    log_to_file("Starting time evolution relationship calculation...")

    # (1) ノードテキストを集めてトークナイズ
    sorted_predicates = sorted(predicate_nodes, key=lambda x: x["index"])
    lines_for_tokenize = []
    node_text_dict = {}
    node_type_dict = {}
    agent_arg_dict = {}

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


    if not lines_for_tokenize:
        log_to_file("[DEBUG] No nodes to tokenize.")
        return

    result, vocab_dict = tokenize_sentence(lines_for_tokenize, node_type_dict)
    if not result:
        log_to_file("[DEBUG] tokenization failed or empty result.")
        return

    # (2) TFベースのベクトル化 & コサイン類似度取得
    ONLY_TF_TERM_WEIGHT = True 
    cos_sim_dict, sorted_nodes = node_vector_space_model(result, vocab_dict, only_tf=ONLY_TF_TERM_WEIGHT)

    # (3) タイムスタンプ情報の構築
    from source.document_parsing.edge_maker import get_edge
    all_edges = get_edge()
    item_edges = [e for e in all_edges if (e["from"] in sorted_nodes or e["to"] in sorted_nodes)]
    group_map = build_timestamp_info(sorted_nodes, item_edges)
    time_evolution_relationship = []

    # (4) cos_sim と時間分布からスコアを計算して next_TimeStamp を付与
    for (a_idx,b_idx),cos_sim_val in sorted(cos_sim_dict.items()):

        time_evolution_score = 0

        # (5) ルールベースのスコア値にボナススコア
        if (b_idx-a_idx==1):
            time_evolution_score += 0.3 # インデックス番号の差が1の場合はscoreに加算(0.3)
            if (agent_arg_dict.get(a_idx, "") != "" and agent_arg_dict[a_idx] == agent_arg_dict.get(b_idx, "")):
                time_evolution_score += 0.3 # 主語が同じの場合はscoreに加算(0.3)

        # (6) temporal_proximity & distributional_proximityを計算
        temporal_prox = calculate_node_temporal_proximity(a_idx, b_idx, group_map, alpha=0.5)
        distributional_prox = calculate_node_distributional_proximity(a_idx, b_idx, N= len(sorted_nodes), beta=0.5)
        time_evolution_score += cos_sim_val * temporal_prox * distributional_prox


        # (7) next_TimeStamp関係を付与
        if time_evolution_score >= TIME_EVOLUTION_RELATIONSHIP_THRESHOLDING:
            append_edge_info("next_TimeStamp", a_idx, b_idx, doc_created_edge_indexes)
            time_evolution_relationship.append((a_idx,b_idx))

        if time_evolution_score > 0:
            textA = node_text_dict.get(a_idx, "N/A")
            textB = node_text_dict.get(b_idx, "N/A")
            log_to_file(
                f"  Node#{a_idx}({textA}) -> Node#{b_idx}({textB}) | "
                f"cos_sim={cos_sim_val:.3f}, temp_prox={temporal_prox:.3f}, distr_prox={distributional_prox:.3f}, "
                f"time_evolution_score={time_evolution_score:.3f}"
            )
        
    # (9) GPTモデルを使って見落とされたnext_TimeStamp関係を点検
    new_relations = GPT_inspection(original_sentences, predicate_nodes, time_evolution_relationship)

    # (10) 見落とし可能性のある(Next_TimeStamp)関係があればログ出力
    if new_relations:
        log_to_file("[Time Evolution] GPT found new Next_TimeStamp relationship candidates:")
        node_text_dict = {}
        for nd in predicate_nodes:
            idx = nd["index"]
            txt = nd.get("predicate", nd.get("entity",""))
            node_text_dict[idx] = txt

        for (a_idx, b_idx) in new_relations:
            txtA = node_text_dict.get(a_idx, "N/A")
            txtB = node_text_dict.get(b_idx, "N/A")
            log_to_file(f"  Node#{a_idx}({txtA}) => Node#{b_idx}({txtB})")
    else:
        log_to_file("[Time Evolution] No missing Next_TimeStamp relationships were detected")
        
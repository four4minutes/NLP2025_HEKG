import re
from openai import OpenAI
from source.document_parsing.logger import log_to_file
from source.document_parsing.edge_maker import append_edge_info
from source.document_parsing.text_utils import (
    convert_predicate_to_text,
    STOP_WORDS
)

client = OpenAI()

def calculate_event_evolution_relationship(entity_nodes, predicate_nodes, original_sentences, doc_created_edge_indexes):
    """
    - 기존 next_TimeStamp 로직은 주석처리.
    - 단 하나의 예제(example)만 사용하는 few-shot 구조.
    - user -> example input, assistant -> example output, 그 다음 user가 실제 요청을 보냄.
    - 동사 기본형(lemma) 변환, 불용어 제외 등의 지시를 프롬프트에 포함.
    """

    log_to_file("----------------------------\n")
    print("ORIGINAL SENTENCE")
    print(original_sentences)
    print("----------------")

    # (1) 술어 노드를 index 오름차순으로 정렬
    sorted_predicates = sorted(predicate_nodes, key=lambda x: x["index"])

    # --- 선형 관계 next_TimeStamp ---
    # for i in range(len(sorted_predicates) - 1):
    #     from_idx = sorted_predicates[i]["index"]
    #     to_idx   = sorted_predicates[i+1]["index"]
    #     append_edge_info("next_TimeStamp", from_idx, to_idx, doc_created_edge_indexes)
    # ---------------------------------------------------

    # (2) 노드 텍스트 수집
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

    if not lines_for_tokenize:
        log_to_file("[INFO] 토큰화할 노드 텍스트가 없습니다.")
        log_to_file("----------------------------")
        return
    print("INPUT")
    print(lines_for_tokenize)
    print("----------------")
    # (3) 예시(단일) 준비
    example = {
        "input": {
            "original_sentences": (
                "東京ビッグサイトのエスカレーターにおいて、定員以上の乗客が乗り込んだため、"
                "ガクッという音とショックの後エスカレーターは停止し逆走した。客達は、エスカレーターの乗り口付近で"
                "仰向けに折り重なるようにして倒れ、10人がエスカレーターの段差に体をぶつけ足首を切ったり、"
                "軽い打撲のけがをした。エスカレーターは、荷重オーバーで自動停止しさらにブレーキも効かず逆走・降下した。"
                "ただ、荷重オーバーによる停止を超えて、ブレーキ能力に限界があり逆走が発生したので、"
                "エスカレーターの機構にも問題がある可能性も考えられる。"
                "また、エスカレーターの逆走により、極めて高い密度で皆後ろ向きで乗り口付近で折り重なるように倒れたことから、"
                "「群集雪崩」が発生したとも考えられる。"
            ),
            "nodes": [
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
            ]
        },
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

    # (4) 메시지 구성
    system_prompt = (
        "あなたは日本語の入力文を単語トークンに分割し、動詞の活用形を基本形に変換して返すアシスタントです。\n"
        "出力時には、(n) を行頭に付与したうえで、トークンを ' | ' で区切ってください。\n"
        "不必要なトークン（例：が, で, した, に, する）は利用者が除外可能性があります。\n"
        "動詞が過去形・連用形の場合はできるだけ基本形に直してください。\n"
    )

    messages = []
    # 1) system
    messages.append({"role": "system", "content": system_prompt})
    # 2) user - 예제의 input
    ex_input_text = (
        "以下は例文です。\n\n"
        f"original_sentences:\n{example['input']['original_sentences']}\n"
        f"nodes:\n{example['input']['nodes']}\n"
    )
    messages.append({"role": "user", "content": ex_input_text})
    # 3) assistant - 예제의 output
    ex_output_text = example["output"]
    messages.append({"role": "assistant", "content": ex_output_text})

    # (5) 실제 유저 요청 (우리가 토큰화할 실제 노드들)
    user_prompt = (
        "上記の例を参考に、以下の各行をトークンに分割し、"
        "動詞は基本形に変換して出力してください。\n"
        "行頭に (n) がない場合は、そのままトークン化し、出力에도 (n)を付与しなくて構いません。\n\n"
        + "\n".join(lines_for_tokenize)
    )
    messages.append({"role": "user", "content": user_prompt})

    # (6) API 호출
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  
            messages=messages,
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
    except Exception as e:
        log_to_file(f"[ERROR] OpenAI API 호출失敗: {e}")
        log_to_file("----------------------------")
        return

    output_lines = content.strip().split("\n")
    result = []
    vocab_dict = {}
    print("OUTPUT")
    print(output_lines)
    print("----------------")

    # (n) 검출용 정규식
    index_pattern = re.compile(r'^\(\s*(\d+)\s*\)\s*(.*)$')

    for line_str in output_lines:
        line_str = line_str.strip()
        if not line_str:
            continue

        match = index_pattern.match(line_str)
        if match:
            node_idx = int(match.group(1))
            tokens_str = match.group(2)
        else:
            node_idx = 0
            tokens_str = line_str

        tokens_in_line = [t.strip() for t in tokens_str.split("|") if t.strip()]

        # 단어집 생성 (stop words 제외)
        filtered_tokens = []
        for token in tokens_in_line:
            if token in STOP_WORDS:
                # 불용어라면 vocab에서 제외
                continue
            # 그렇지 않으면 단어집에 추가
            vocab_dict[token] = vocab_dict.get(token, 0) + 1
            filtered_tokens.append(token)

        result.append((node_idx, filtered_tokens))

    # (8) 결과 로깅
    print("RESULT")
    print(result)
    print("----------------\n\n")

    log_to_file("[INFO] 현재까지의 단어집 (vocab_dict):")
    log_to_file(str(vocab_dict))

    log_to_file("----------------------------")
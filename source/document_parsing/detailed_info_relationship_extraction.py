# detailed_info_relationship_extraction.py

import re
from openai import OpenAI
from source.document_parsing.logger import log_token_usage, log_to_file
from source.document_parsing.edge_maker import append_edge_info, get_edge

client = OpenAI()

def extract_explain_details_relationship(sentence, node_list, doc_created_indexes):
    """
    - 설명관계 추출을 위한 단일 함수
    - 'sentence': str (문장 원문)
    - 'node_list': [{"index":..., "text":...}, ...] 형태 (노드 정보)
    - 내부에 프롬프트와 예시가 직접 포함되어 있음
    - OpenAI API 호출 후 결과를 파싱하여, explanation(설명) 엣지를 생성
    """

    try:
        prompt = (
            "[タスク目的]\n"
            "入力文に対して、文から抽出されたノード間に存在する説明関係を抽出する。\n"
            "[背景知識]\n"
            "1. ノード\n"
            "    他のタスクで文を区切り、ノードとしてまとめた要素を指す。本タスクでは、与えられたノード同士の間に「説明関係」があるかどうかを抽出することを目的とする。\n"
            "2. 説明関係\n"
            "    あるノードが別のノードの名詞または述語に対して詳細な説明を加えている場合、それらを「説明関係」と定義する。\n"
            "3. 説明ノードと被説明ノード（および説明対象）\n"
            "    説明関係において、詳しい情報を提供する側のノードを「説明ノード」、その説明を受けるノードを「被説明ノード」と呼ぶ。また、このとき説明ノードが説明しようとしている被説明ノード内の具体的な要素を「説明対象」と定義する。\n"
            "    たとえば、「昨日市場で買った肉は通常価格より半額で販売されていた」という文の場合、「昨日市場で買った」が説明ノード、「肉は通常価格より半額で販売されていた」が被説明ノード、「肉」が説明対象となる。\n"
            "4. 説明関係の種類\n"
            "    説明関係には大きく分けて2種類が存在する。\n"
            "    (1) あるノードが、他のノードに含まれる特定の名詞や述語について詳しく説明している場合\n"
            "    このケースでは、説明ノードが説明しようとしている対象を被説明ノード内で明確に特定できる。\n"
            "    - 例：「昨日市場で買った肉は通常価格より半額で販売されていた」\n"
            "    - 被説明ノード：「肉は通常価格より半額で販売されていた」\n"
            "    - 説明ノード：「昨日市場で買った」\n"
            "    - 説明対象：「肉」\n"
            "    (2) あるノードが、他のノードの内容全体や背景的情報を説明しているが、被説明ノード内の特定の要素としては識別できない場合\n"
            "    このケースでは、説明ノードが「被説明ノード全体」や「背景的な情報」を説明するため、具体的にどの名詞・述語に対応するか明確に分からない。\n"
            "    - 例：「レンタカーの利用時間は12時間であるが、交通渋滞のため予想時間より遅く到着したため、追加料金を支払った」\n"
            "    - 被説明ノード：「追加料金を支払った」\n"
            "    - 説明ノード：「レンタカーの利用時間は12時間」\n"
            "    - 説明対象：背景説明（特定しづらいため“背景”として扱う）\n"
            "    - この文には、(交通渋滞)-因果関係→(遅く到着)、(遅く到着)-因果関係→(追加料金の支払い)の２つ因果関係が存在するが、説明関係と因果関係は異なるものである。\n"
            "[留意点]\n"
            "1. 本タスクではあくまでノード単位で説明関係を判断する。つまり、入力文の文脈を踏まえつつ、与えられたノード同士のあいだに上記の説明関係が成立するかどうかだけに注目すればよい。\n"
            "[入力に関する説明]\n"
            "- 入力文: 分析対象の文\n"
            "- ノード: {\"index\": ノードのインデックス番号, \"text\": ノードのテキスト情報}\n"
            "[出力形式]\n"
            "以下の形式で、説明関係を出力する（複数ある場合は番号を振って列挙する）。\n"
            "[EXPLAIN_RELATION]\n"
            "(1) (被説明ノードindex, 説明ノードindex, 説明対象)\n"
            "(2) (被説明ノードindex, 説明ノードindex, 説明対象)\n"
            "...\n"
            "説明関係が存在しない場合は「無し」と記載する。\n"
            "[EXPLAIN_RELATION]\n"
            "無し\n"
            "[指示]\n"
            "入力文およびノード情報を参照し、ノード間に説明関係があれば抽出する。それ以外の関係は一切抽出せず、説明関係のみを対象とすること。\n"
        )
        examples = [
            {
                "input": {
                    "sentence": "東京ビッグサイト4階で開催されるアニメのフィギュアの展示・即売会場に直結するエスカレーターにおいて、開場にあたり警備員1人が先頭に立ち誘導し多くの客がエスカレーターに乗り始めた。",
                    "nodes": [
                        {"index": 1, "text": "東京ビッグサイト4階で開催されるアニメのフィギュアの展示・即売会"},
                        {"index": 2, "text": "警備員1人が先頭に立ち"},
                        {"index": 3, "text": "警備員1人が誘導し"},
                        {"index": 4, "text": "多くの客がエスカレーターに乗り始めた"},
                        {"index": 5, "text": "アニメのフィギュアの展示・即売会場に直結するエスカレーター"},
                        {"index": 6, "text": "エスカレーター"},
                        {"index": 7, "text": "開場"}
                    ]
                },
                "output": "[EXPLAIN_RELATION]\n(1) (5,1,'アニメのフィギュアの展示・即売会')\n(2) (6,5,'エスカレーター')"
            },
            {
                "input": {
                    "sentence": "周囲の人々が、倒れた人を引き起こしたり、移動させるなどの救助に協力した。",
                    "nodes": [
                        {"index": 8,  "text": "人が倒れた"},
                        {"index": 9,  "text": "周囲の人々が人を引き起こしたり"},
                        {"index": 10, "text": "周囲の人々が人を移動させる"},
                        {"index": 11, "text": "周囲の人々が救助に協力した"}
                    ]
                },
                "output": "[EXPLAIN_RELATION]\n(1) (9,8,'人')\n(2) (10,8,'人')"
            },
            {
                "input": {
                    "sentence": "このエスカレーターは、荷重制限が約7.5t、逆送防止用ブレーキ能力の限界が約9.3tであったのに対し、事故当時は約120人が乗車したことから、逆送防止用ブレーキ能力の限界荷重をもオーバーし自動停止しさらにブレーキも効かず逆走・降下した。",
                    "nodes": [
                        {"index": 12, "text": "約120人が乗車した"},
                        {"index": 13, "text": "エスカレーターが自動停止し"},
                        {"index": 14, "text": "ブレーキが効かず"},
                        {"index": 15, "text": "エスカレーターが逆走・降下した"},
                        {"index": 16, "text": "荷重制限が約7.5t"},
                        {"index": 17, "text": "逆送防止用ブレーキ能力の限界が約9.3tであった"},
                        {"index": 18, "text": "逆送防止用ブレーキ能力の限界荷重をもオーバー"}
                    ]
                },
                "output": "[EXPLAIN_RELATION]\n(1) (12,16,'[背景説明]')\n(2) (18,17,'逆送防止用ブレーキ能力の限界')"
            },
            {
                "input": {
                    "sentence": "ただ、荷重制限とブレーキ能力の限界までには、(9.3-7.5=）1.8tの余裕があるはずなのに、停止してすぐ逆走したことから、エスカレーターの機構にも問題がある可能性もある。",
                    "nodes": [
                        {"index": 19, "text": "停止して"},
                        {"index": 20, "text": "逆走した"},
                        {"index": 21, "text": "荷重制限とブレーキ能力の限界までには、(9.3-7.5=）1.8tの余裕がある"},
                        {"index": 22, "text": "エスカレーターの機構にも問題がある"}
                    ]
                },
                "output": "[EXPLAIN_RELATION]\n(1) (22,21,'[背景説明]')"
            },
            {
                "input": {
                    "sentence": "また、1段あたり3～4人乗車しており、「人口密度」は8.6人/平方メートルにも達している。",
                    "nodes": [
                        {"index": 23, "text": "3～4人が1段あたり乗車しており"},
                        {"index": 24, "text": "人口密度」は8.6人/平方メートルにも到達"}
                    ]
                },
                "output": "[EXPLAIN_RELATION]\n(1) (24,23,'[背景説明]')"
            },
            {
                "input": {
                    "sentence": "事故を起こしたエスカレーターは閉鎖された。",
                    "nodes": [
                        {"index": 25, "text": "事故を起こしたエスカレーター"},
                        {"index": 26, "text": "エスカレーターが閉鎖された"}
                    ]
                },
                "output": "[EXPLAIN_RELATION]\n(1) (26,25,'エスカレーター')"
            },
            {
                "input": {
                    "sentence": "一方エスカレーターとしても、逆走防止のブレーキ能力を上げ、荷重オーバー時の停止から逆走に至る間の余裕を拡大させるなどのより安全サイドに立った構造にすることも必要である。",
                    "nodes": [
                        {"index": 27, "text": "逆送防止のブレーキ能力向上"},
                        {"index": 28, "text": "荷重オーバー時の停止から逆走に至る間の余裕の拡大"},
                        {"index": 29, "text": "より安全サイドに立った構造"}
                    ]
                },
                "output": "[EXPLAIN_RELATION]\n(1) (28,27,'[背景説明]')\n(2) (29,28,'[背景説明]')"
            },
            {
                "input": {
                    "sentence": "また、エスカレーターの逆走により、極めて高い密度で皆後ろ向きで乗り口付近で折り重なるように倒れたことから、「群集雪崩」が発生したとも考えられる。",
                    "nodes": [
                        {"index": 30, "text": "エスカレーターが逆走"},
                        {"index": 31, "text": "皆が極めて高い密度で後ろ向きで折り重なる"},
                        {"index": 32, "text": "皆が倒れた"},
                        {"index": 33, "text": "群集雪崩が発生した"}
                    ]
                },
                "output": "[EXPLAIN_RELATION]\n無し"
            }
        ]

        # 2) messages 구성
        messages = [
            {
                "role": "system",
                "content": "You are an assistant that extracts explain details relationships between nodes."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # 3) few-shot 예시 추가
        for example in examples:
            example_sentence = example["input"]["sentence"]
            example_nodes = example["input"]["nodes"]
            example_node_str = "\n".join(
                f"{{index:{n['index']}, text:{n['text']}}}"
                for n in example_nodes
            )
            example_input_str = (
                f"文:{example_sentence}\n"
                f"ノード:{example_node_str}\n"
            )
            example_output_str = example["output"]
            messages.append({"role": "user", "content": example_input_str})
            messages.append({"role": "assistant", "content": example_output_str})

        # 4) 실제 입력 데이터(함수 파라미터)
        node_str = "\n".join(
            f"{{index:{n['index']}, text:{n['text']}}}"
            for n in node_list
        )
        final_input_str = (
            f"文: {sentence}\n"
            f"ノード:\n{node_str}\n\n"
        )
        messages.append({"role": "user", "content": final_input_str})

        # 5) API 호출
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()

        # 토큰로그
        if hasattr(response, "usage") and hasattr(response.usage, "total_tokens"):
            log_token_usage(response.usage.total_tokens)

        # 6) 결과 파싱 + Edge 생성
        #   출력형식 예시:
        #   [EXPLAIN_RELATION]
        #   (1) (被説明ノードindex, 説明ノードindex, 説明対象)
        #   (2) ...
        #   ... or "無し"
        lines = content.splitlines()
        in_section = False
        existing_edges = get_edge()

        for line in lines:
            line = line.strip()
            if "[EXPLAIN_RELATION]" in line:
                in_section = True
                continue
            if not in_section:
                continue
            if line == "無し":
                break

            # 정규식 예시: (1) (5,1,'アニメのフィギュア')
            match = re.match(r'^\(\d+\)\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*\'(.*?)\'\s*\)$', line)
            if match:
                be_explained_idx = int(match.group(1))   # 피설명 노드
                explain_idx = int(match.group(2))        # 설명 노드
                target_str = match.group(3)             # 설명대상
                
                cause_conflict = any(e['type'] == "explain_cause" and e['from'] == be_explained_idx and e['to'] == explain_idx for e in existing_edges)
                reason_conflict = any(e['type'] == "explain_reason" and e['from'] == be_explained_idx and e['to'] == explain_idx for e in existing_edges)
                
                if not (cause_conflict or reason_conflict):
                    # 설명대상을 로그로 남김
                    log_to_file(f"[ExplainTarget] {target_str}")
                    # (피설명노드) --(explain_details)--> (설명노드)
                    append_edge_info("explain_details", be_explained_idx, explain_idx, doc_created_indexes)


    except Exception as e:
        print(f"Error extracting explanation relation: {e}")
        return []
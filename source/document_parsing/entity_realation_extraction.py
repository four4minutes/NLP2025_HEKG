#entity_relation_extraction.py
# 自動生成エッジを生成するプログラムモジュール

import re
from openai import OpenAI
from source.document_parsing.edge_maker import append_edge_info, get_auto_generated_edge_dictionary, add_auto_edge_label
from source.document_parsing.logger import log_to_file, log_token_usage

client = OpenAI()

def extract_entity_relationship(entity_nodes, predicate_nodes, edges, original_sentences, doc_created_edge_indexes):
    """
    ノード間に付与すべき自動生成エッジを分析し、必要に応じて新たなエッジラベルを
    自動生成エッジ辞書へ追加したうえで、にノード間にエッジを付与する関数
    - entity_nodes : エンティティノードを格納したリスト
    - predicate_nodes : 述語ノードを格納したリスト
    - edges : 事前に定義されているエッジのリスト
    - original_sentences : 原文テキスト全体
    - doc_created_edge_indexes : 生成エッジのインデックスを登録するセット
    """

    # (1) GPTに与えるプロンプト
    system_prompt = (
        "[指示]\n"
        "あなたはナレッジグラフ(Knowledge Graph)上で表現されるノード間のエッジ（edge）とエッジラベル（edge label）を生成するアシスタントです。\n"
        "すでに他のタスクによって、原文テキストから複数のノードが抽出され、いくつかの事前定義エッジが付与されています。\n"
        "事前定義エッジとは、ユーザや他のモジュールがすでに定義・管理している関係です。\n"
        "事前定義エッジはユーザが指定したものであり、あなたが追加・変更を行うことはありません。\n"
        "あなたが担当する「自動生成エッジ」は、事前定義エッジに含まれない追加的な関係を付与するためのものです。\n"
        "この自動生成エッジは関係が乱立するのを防ぐため、「自動生成エッジ辞書」で一元管理されます。\n"
        "自動生成エッジ辞書にはエッジラベルと、そのラベルの意味にあたる説明が定義されています。\n"
        "あなたは原文テキストを参照し、提示されたノードの組み合わせを確認したうえで、以下を行ってください。\n"
        "1. すでに辞書に定義されている自動生成エッジが該当ノードに付与できる場合、それを生成して付与する\n"
        "2. 辞書にない新たな関係ラベルが必要だと判断される場合は、そのラベルと説明を自動生成エッジ辞書に追加し、そのエッジを該当ノードに付与する\n"
        "3. 新たに定義する自動生成エッジは、事前定義エッジや既存の自動生成エッジと重複しないようにする\n"
        "（ここで「重複しない」とは完全一致を指すだけではなく、意味的に同じ関係とみなせる場合も含めて排除すること）\n\n"
        "[注意点]\n"
        "まず、まだ一切の関係が付与されていないノードを優先的に検討し、付与できる関係があるならば積極的に生成してください。\n"
        "ただし、既に関係を持つノードについても、新たに妥当と思われる関係があれば合わせて提案してください。\n"
        "また、新たに生成しようとする関係が、既に存在する関係とほぼ同じ意味・機能を持つ場合は、重複を避けるために生成しないでください。\n\n"
        "[具体例]\n"
        "たとえば、次のような文があるとしましょう。\n"
        "「今日の朝におなかがすいたので、ごはんを食べるために牛丼屋に行ったが、みんな朝ご飯を食べたかったからかなり混んでいて、結局何も食べずにそのまま学校に行った。」\n"
        "ここから (1)「今日の朝」, (2)「おなかがすいた」\n"
        ", (3)「ごはんを食べる」, (4)「牛丼屋に行った」, (5)「みんな朝ご飯を食べたかった」, (6)「かなり混んでいて」, (7)「結局何も食べず」, (8)「そのまま学校に行った」の8つのノードが抽出されているとします。\n"
        "事前定義エッジとして、たとえば  \n"
        "(2) - [SpecificTime] → (1), (3) - [explain_reason] → (2), (4) - [explain_reason] → (3), (4) - [next_TimeStamp] → (6), (6) - [next_TimeStamp] → (7), (7) - [next_TimeStamp] → (8), (7) - [explain_reason] → (6) などが既に付与されているとします。\n"
        "一方、自動生成エッジ辞書には  \n"
        "(x) -[as_like]→ (y) : (y) は (x)の比喩表現である\n"
        "という1つの関係が定義されていると仮定しましょう。\n"
        "ここであなたのタスクは、まず原文テキストとノード情報を確認し、\n"
        "事前生成関係や既存の自動生成関係を把握したうえで、まだ付与されていない追加的な関係がないか検討することです。\n"
        "たとえば、あなたはノード (6) とノード (7) の間に’[assume_reason]’という関係を定義したいと考えました。\n"
        "この ‘(x) - [assume_reason] → (y)’ は「(y) は (x) の理由を推定したものである」という意味を持ち、今回の場合は ‘(7) - [assume_reason] → (6)’ の形で付与が可能だとします。\n"
        "そうすると ‘assume_reason’ という新しいエッジラベルとその説明（意味）が自動生成エッジ辞書に追加され、同時にそのエッジがノード (7) と (6) の間に付与されます。\n\n"
        "[入力形式]\n"
        "- 原文、ノード、エッジ、事前生成エッジ辞書、自動生成エッジ辞書\n"
        "原文 : テキスト\n"
        "ノード : (index) テキスト, (index) テキスト, (index) テキスト\n"
        "→ 例： (1) 今日の朝, (2) おなかがすいた, (3) ごはんを食べる\n"
        "エッジ : (index, index, edge label), (index, index, edge label), (index, index, edge label)\n"
        "→ 例： (2, 1, SpecificTime), (3, 2, explain_reason), (4, 3, explain_reason)\n"
        "事前生成エッジ辞書 : (x)-[edge label]→(y) : explanation\n"
        "自動生成エッジ辞書 : (x)-[edge label]→(y) : explanation\n"
        "[出力形式]\n"
        "- もし見落としが無い場合は「無し」とだけ出力してください。そうでない場合は必ず以下の形式を守ってください\n"
        "- 自動生成エッジ辞書に追加する関係があれば、以下のように(自動生成エッジ辞書追加)と明示したうえで、列挙すること。\n"
        "- 追加できる自動生成エッジがあれば、以下のように(自動生成エッジ)と明示したうえで、列挙すること。\n"
        "例えば、\n"
        "(自動生成エッジ辞書追加)\n"
        "(x)-[as_like]→(y) : (y) は (x)の比喩表現である\n"
        "(x)-[assume_reason]→(y) : (y) は (x) の理由を推定したものである\n"
        "(自動生成エッジ)\n"
        "(7, 6, assume_reason), (100, 101, as_like), …"
    )
    
    # (1-1) 事前生成エッジ辞書
    predefined_edges_text = """(x)-[sub]→(y) : (y) は(x) のの分類的階層構造において下位である
        (x)-[correspond_to]→(y) : (y)は(x)の意味的階層構造において下位である
        (x)-[SpecificTime]→(y) : (y)は(x)に詳細な時間情報を提供する
        (x)-[SpecificPlace]→(y) :  (y)は(x)に詳細な場所情報を提供する
        (x)-[next TimeStamp]→(y) : (y)のTimeStampは(x)のTimeStampの直後である
        (x)-[explain_details]→(y) :  (y)は(x)に詳細な情報を提供する
        (x)-[explain_reason]→(y) :  (y)は(x)に対する理由を説明する
        (x)-[explain_cause]→(y) : (y)は(x)に対する直接的な原因である
        (x)-[equivalent]→(y) :  (y)と(x)は類似した情報である
        """
    # (1-2) 自動生成エッジ辞書
    auto_edge_dict_items = get_auto_generated_edge_dictionary()

    auto_edges_text_list = []
    for item in auto_edge_dict_items:
        lbl = item["label"]
        expl = item["explanation"]
        auto_edges_text_list.append(f"(x)-[{lbl}]→(y) : {expl}")

    # (1-3) 原文
    user_prompt = ""
    user_prompt += f"原文 : {original_sentences.strip()}\n\n"

    # (1-4) ノードまとめ
    node_str_list = []
    for nd in entity_nodes:
        node_str_list.append(f"({nd['index']}) {nd.get('entity','')}")
    for nd in predicate_nodes:
        node_str_list.append(f"({nd['index']}) {nd.get('predicate','')}")
    user_prompt += "ノード : " + ", ".join(node_str_list) + "\n\n"

    # (1-5) エッジまとめ
    edge_str_list = []
    for e in edges:
        f_idx = e.get("from")
        t_idx = e.get("to")
        etype = e.get("type","")
        edge_str_list.append(f"({f_idx}, {t_idx}, {etype})")
    user_prompt += "エッジ : " + ", ".join(edge_str_list) + "\n\n"

    user_prompt += "事前生成エッジ辞書 :\n" + predefined_edges_text + "\n"
    user_prompt += "\n自動生成エッジ辞書 : "
    user_prompt += ", ".join(auto_edges_text_list)
    user_prompt += "\n\n"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    content = ""

    # (2) OpenAI APIを呼び出す
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
        if hasattr(response, "usage") and hasattr(response.usage, "total_tokens"):
            log_token_usage(response.usage.total_tokens)
    except Exception as e:
        print(f"[ERROR] OpenAI API call failed: {e}")
        return

    # (3)  GPTの応答を解析
    # (3-1) "無し" とだけ返された場合、新規に付与すべき関係は存在しないと判断
    if content.strip() == "無し":
        log_to_file("No new auto-generated edges found.")
        return

    dict_add_pattern = r'\(自動生成エッジ辞書追加\)([\s\S]*?)(?=\(自動生成エッジ\)|$)'
    edge_add_pattern = r'\(自動生成エッジ\)([\s\S]*)'

    dict_add_match = re.search(dict_add_pattern, content)
    edge_add_match = re.search(edge_add_pattern, content)

    # (3-2) 新しいエッジラベルを自動生成エッジ辞書へ追加
    if dict_add_match:
        dict_lines = dict_add_match.group(1).strip().splitlines()
        for line in dict_lines:
            line = line.strip()
            if not line:
                continue
            pattern = r'^\(x\)-\[(.+?)\]→\(y\)\s*:\s*(.*)$'
            m = re.match(pattern, line)
            if m:
                label = m.group(1).strip()
                explanation = m.group(2).strip()
                add_auto_edge_label(label, explanation)
                log_to_file(f"[New auto-generated relation] {label} : {explanation}")

    # (3-3) 自動生成エッジの付与
    if edge_add_match:
        edge_line = edge_add_match.group(1).strip()
        auto_edge_pattern = r'\(\s*(\d+)\s*,\s*(\d+)\s*,\s*([^\),]+)\s*\)'
        auto_edges = re.findall(auto_edge_pattern, edge_line)
        for (f_str, t_str, lbl_str) in auto_edges:
            from_idx = int(f_str)
            to_idx = int(t_str)
            relation = lbl_str.strip()
            append_edge_info(relation, from_idx, to_idx, doc_created_edge_indexes)
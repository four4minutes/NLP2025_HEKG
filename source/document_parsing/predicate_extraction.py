# pedicate_extraction.py
# 文から述語と述語項構造を抽出するモジュール

import re
from openai import OpenAI
from source.document_parsing.logger import log_token_usage
from source.document_parsing.text_utils import fix_predicate_structure_text

client = OpenAI()

def split_into_sentences(text: str) -> str:
    '''
    文を簡易的に区切り、ナンバリングして複数行にまとめて返す関数。
    句点やセミコロンなどを区切りとする。
    - text : 入力文
    '''
    # (1) 正規表現で分割
    sentences = re.split(r'[。！？.;,、]', text)
    # (2) 無意味な空白を除去し、番号を付与して連結
    valid_sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
    numbered_sentences = "\n".join(f"({i+1}) {sentence}" for i, sentence in enumerate(valid_sentences))
    return numbered_sentences

def extract_predicates(sentence: str) -> tuple:
    '''
    1つの文から事象述語と概念述語を抽出して返す関数。
    - sentence : 抽出対象となる文
    - return: (事象述語のリスト, 概念述語のリスト)
    '''
    # (1) 文を分割して前処理
    preprocessed_sentences = split_into_sentences(sentence)

    # (2) GPTに与えるプロンプト
    prompt = (
        "[タスク目的]\n\n"
        "入力文からすべての述語を特定し、その後、事象に関する記述をする述語と概念に関する記述をする述語を区別する。\n\n"
        "[背景知識・用語説明]\n\n"
        "1. 述語とは、文を構成する重要な文節の一つで、主語を受けてその動作・状態・存在を表す。\n"
        "   意味的には「どうする」「どんなだ」「何だ」「ある（ない）」を表し、品詞としては動詞・形容詞・形容動詞が含まれる。\n"
        "   （例1）「太郎は学校に行った。」→「行った」は述語\n"
        "   （例2）「彼は授業を受けた。」→「受けた」は述語\n\n"
        "2. 本タスクでは、事態性名詞（サ変名詞）も述語として扱う。\n"
        "   事態性名詞とは、動作・状態・現象を表し、「する」「した」を付けて動詞化できる名詞である。\n"
        "   （例）「統制(する)」「確認(した)」「インストール(する)」\n\n"
        "3. 本タスクでの述語分類：\n"
        "   - 事象に関する述語（事象述語）\n"
        "     現実世界で実際に発生した（あるいは明確な物理的・実体的変化・行為が存在する）動作・変化・現象を表す述語を事象述語とする。\n"
        "     例：「太郎は学校へ行った」の「行った」や「彼は授業を受けた」の「受けた」は、実際の行為・事象が起こっているため事象述語。\n"
        "     また、「～となった」のように状態変化が実際に起こったことを示す場合も事象述語。\n\n"
        "   - 概念に関する述語（概念述語）\n"
        "     抽象的な内容、実体の属性、可能性、必要性、考え方、方策など、\n"
        "     現実世界での物理的・具体的行為や変化を必ずしも伴わない抽象的・概念的な説明を行う述語を概念述語とする。\n"
        "     例：「問題がある」「私は学生である」「必要がある」は、具体的な行為ではなく、\n"
        "     状態・属性・可能性・改善策・理論的方向性などを述べるため概念述語。\n\n"
        "   ※文脈考慮の基準（追加）：\n"
        "     同じ動詞・表現でも文脈上、物理的行為や具体的変化ではなく、抽象的な方策・計画・構造的改善・理論的方向性を示す場合は概念述語とする。\n"
        "     一方、同じ表現でも現実に起きた具体的事象を表す場合は事象述語とする。\n\n"
        "[補足・留意点]\n\n"
        "1. 述語として機能する事態性名詞のみ対象、それ以外の具体的実体を指す名詞は対象外。\n"
        "   （例）「彼からの電話(i)によると、私は彼の家に電話(j)を忘れたらしい。」\n"
        "   電話(i)：「電話する」で動詞化可→述語該当、電話(j)実体名詞→対象外\n\n"
        "2. 複合名詞は分割せず一単位で扱う。\n"
        "   （例）「離党問題」は「離党問題」として扱う。\n"
        "   「文化庁の2005年の報告」も一塊として扱う。\n\n"
        "3. 意味を持つ最低限の格要素を含めて述語を抽出する。\n"
        "   （例）「けがをした」は「した」ではなく「けがをした」\n"
        "   （例）「においがする」も「する」ではなく「においがする」で抽出。\n\n"
        "[入力に関する説明]\n\n"
        "以下の文は複文であり、述語を正確に特定するために次のように前処理を行った。\n"
        "前処理を行う理由は、複雑な構造を持つ複文では、文を分割することで述語の特定が容易になるためである。\n\n"
        "- 原文: 元の文をそのまま提示する。\n"
        "- 分割した文: 文を句点(。)、読点(、)、セミコロン(;)を基準として分割し、それぞれ順番に番号を付けた。\n\n"
        "事象述語・概念述語の分類にあたっては、上記基準および文脈を参照し、\n"
        "具体的行為・物理的変化が明示的でない場合や単なる方策・可能性を表す場合は概念述語として扱ってよい。\n\n"
        "[出力形式]\n\n"
        "[事象述語] (1)<述語1> (2)<述語2> (3)<述語3> …\n"
        "[概念述語] (1)<述語1> (2)<述語2> (3)<述語3> …\n\n"
        "[指示]\n\n"
        "1. 原文および分割文を参照し、文中のすべての述語を抽出する。\n"
        "2. 述語を事象述語・概念述語に分類する（上記の基準および文脈考慮に従う）。\n"
        "3. 順序を維持しつつ重複を避ける。\n"
        "4. 結果を指定の形式で出力する。\n"
    )
    examples = [
        {
            "input": {
                "sentence": "東京ビッグサイトのエスカレーターにおいて、定員以上の乗客が乗り込んだため、ガクッという音とショックの後エスカレーターは停止し逆走した。",
                "preprocessed_sentences": "1. 東京ビッグサイトのエスカレーターにおいて\n2. 定員以上の乗客が乗り込んだ\n3. ガクッという音とショックの後エスカレーターは停止し\n4. 逆走した"
            },
            "output": "[事象述語] (1)<乗り込んだ> (2)<停止し> (3)<逆走した>\n[概念述語] 無し"
        },
        {
            "input": {
                "sentence": "客達は、エスカレーターの乗り口付近で仰向けに折り重なるようにして倒れ、10人がエスカレーターの段差に体をぶつけ足首を切ったり、軽い打撲のけがをした。",
                "preprocessed_sentences": "1. 客達はエスカレーターの乗り口付近で仰向けに折り重なるようにして倒れ\n2. 10人がエスカレーターの段差に体をぶつけ\n3. 足首を切ったり\n4. 軽い打撲のけがをした"
            },
            "output": "[事象述語] (1)<折り重なる> (2)<倒れ> (3)<ぶつけ> (4)<切ったり> (5)<けがをした>\n[概念述語] 無し"
        },
        {
            "input": {
                "sentence": "エスカレーターは、荷重オーバーで自動停止しさらにブレーキも効かず逆走・降下した。",
                "preprocessed_sentences": "1. エスカレーターは荷重オーバーで自動停止し\n2. さらにブレーキも効かず\n3. 逆走・降下した"
            },
            "output": "[事象述語] (1)<自動停止し> (2)<効かず> (3)<逆走・降下した>\n[概念述語] 無し"
        },
        {
            "input": {
                "sentence": "ただ、荷重オーバーによる停止を超えて、ブレーキ能力に限界があり逆走が発生したので、エスカレーターの機構にも問題がある可能性も考えられる。",
                "preprocessed_sentences": "1. 荷重オーバーによる停止を超えて\n2. ブレーキ能力に限界があり\n3. 逆走が発生した\n4. エスカレーターの機構にも問題がある可能性も考えられる"
            },
            "output": "[事象述語] (1)<停止> (2)<発生した>\n[概念述語] (1)<超えて> (2)<限界があり> (3)<問題がある> (4)<考えられる>"
        },
        {
            "input": {
                "sentence": "また、エスカレーターの逆走により、極めて高い密度で皆後ろ向きで乗り口付近で折り重なるように倒れたことから、「群集雪崩」が発生したとも考えられる。",
                "preprocessed_sentences": "1. エスカレーターの逆走により\n2. 極めて高い密度で皆後ろ向きで乗り口付近で折り重なるように倒れた\n3. 「群集雪崩」が発生したとも考えられる"
            },
            "output": "[事象述語] (1)<逆走> (2)<折り重なる> (3)<倒れた> (4)<発生した>\n[概念述語] (1)<考えられる>"
        },
        {
            "input": {
                "sentence": "東京ビッグサイト4階で開催されるアニメのフィギュアの展示・即売会場に直結するエスカレーターにおいて、開場にあたり警備員1人が先頭に立ち誘導し多くの客がエスカレーターに乗り始めた。",
                "preprocessed_sentences": "1. 東京ビッグサイト4階で開催されるアニメのフィギュアの展示・即売会場に直結するエスカレーターにおいて\n2. 開場にあたり警備員1人が先頭に立ち誘導し多くの客がエスカレーターに乗り始めた"
            },
            "output": "[事象述語] (1)<開催される> (2)<立ち> (3)<誘導し> (4)<乗り始めた>\n[概念述語] (1)<直結する>"
        },
        {
            "input": {
                "sentence": "客達は先を争うようにエスカレーターに乗り込んだが、先頭は警備員が規制していたため、エスカレーターの1段に3～4人が乗るほどのすし詰め状態となった。",
                "preprocessed_sentences": "1. 客達は先を争うようにエスカレーターに乗り込んだが\n2. 先頭は警備員が規制していたため\n3. エスカレーターの1段に3～4人が乗るほどのすし詰め状態となった"
            },
            "output": "[事象述語] (1)<争う> (2)<乗り込んだ> (3)<規制していた> (4)<乗る> (5)<すし詰め状態となった>\n[概念述語] 無し"
        },
        {
            "input": {
                "sentence": "先頭が全長35mの7～8割ほどまで上がったところで、ガクッという音とショックを受けエスカレーターは停止し、その後下りエスカレーターよりも速い速度で逆走・降下しはじめた。",
                "preprocessed_sentences": "1. 先頭が全長35mの7～8割ほどまで上がったところで\n2. ガクッという音とショックを受けエスカレーターは停止し\n3. その後下りエスカレーターよりも速い速度で逆走・降下しはじめた"
            },
            "output": "[事象述語] (1)<上がった> (2)<受け> (3)<停止し> (4)<逆走・降下しはじめた>\n[概念述語] 無し"
        },
            {
        "input": {
            "sentence": "周囲の人々が、倒れた人を引き起こしたり、移動させるなどの救助に協力した。",
            "preprocessed_sentences": "1. 周囲の人々が倒れた人を引き起こしたり\n2. 移動させるなどの救助に協力した"
        },
        "output": "[事象述語] (1)<倒れた> (2)<引き起こしたり> (3)<移動させる> (4)<協力した>\n[概念述語] 無し"
        },
        {
            "input": {
                "sentence": "関係者が異常に気付き緊急停止ボタンを押したり、逆走により乗員が減ったことからブレーキが効き始め、逆走は停止した。",
                "preprocessed_sentences": "1. 関係者が異常に気付き緊急停止ボタンを押したり\n2. 逆走により乗員が減ったことからブレーキが効き始め\n3. 逆走は停止した"
            },
            "output": "[事象述語] (1)<気付き> (2)<押したり> (3)<逆走> (4)<減った> (5)<効き始め> (6)<停止した>\n[概念述語] 無し"
        },
        {
            "input": {
                "sentence": "このエスカレーターは、荷重制限が約7.5t、逆送防止用ブレーキ能力の限界が約9.3tであったのに対し、事故当時は約120人が乗車したことから、逆送防止用ブレーキ能力の限界荷重をもオーバーし自動停止しさらにブレーキも効かず逆走・降下した。",
                "preprocessed_sentences": "1. このエスカレーターは荷重制限が約7.5t逆送防止用ブレーキ能力の限界が約9.3tであったのに対し\n2. 事故当時は約120人が乗車したことから\n3. 逆送防止用ブレーキ能力の限界荷重をもオーバーし自動停止しさらにブレーキも効かず逆走・降下した"
            },
            "output": "[事象述語] (1)<乗車した> (2)<オーバーし> (3)<自動停止し> (4)<効かず> (5)<逆走・降下した>\n[概念述語] (1)<約9.3tであった>"
        },
        {
            "input": {
                "sentence": "ただ、荷重制限とブレーキ能力の限界までには、(9.3-7.5=）1.8tの余裕があるはずなのに、停止してすぐ逆走したことから、エスカレーターの機構にも問題がある可能性もある。",
                "preprocessed_sentences": "1. ただ荷重制限とブレーキ能力の限界までには1.8tの余裕があるはずなのに\n2. 停止してすぐ逆走したことから\n3. エスカレーターの機構にも問題がある可能性もある"
            },
            "output": "[事象述語] (1)<停止して> (2)<逆走した>\n[概念述語] (1)<余裕がある> (2)<問題がある> (3)<可能性もある>"
        },
        {
            "input": {
                "sentence": "また、1段あたり3～4人乗車しており、「人口密度」は8.6人/平方メートルにも達している。",
                "preprocessed_sentences": "1. また1段あたり3～4人乗車しており\n2. 「人口密度」は8.6人/平方メートルにも達している"
            },
            "output": "[事象述語] (1)<乗車しており>\n[概念述語] (1)<達している>"
        },
        {
            "input": {
                "sentence": "さらに皆後ろ向きで乗り口付近で折り重なるように倒れ人口密度は増大し、「群集雪崩」が発生したことがけが人発生の原因である。",
                "preprocessed_sentences": "1. さらに皆後ろ向きで乗り口付近で折り重なるように倒れ人口密度は増大し\n2. 「群集雪崩」が発生したことがけが人発生の原因である"
            },
            "output": "[事象述語] (1)<折り重なる> (2)<倒れ> (3)<発生した>\n[概念述語] (1)<増大し> (2)<原因である>"
        },
        {
            "input": {
                "sentence": "周囲の人々の救助が功を奏したのと被害者は若者が殆どだったので、軽傷程度のけがですんだ。",
                "preprocessed_sentences": "1. 周囲の人々の救助が功を奏したのと被害者は若者が殆どだったので\n2. 軽傷程度のけがですんだ"
            },
            "output": "[事象述語] 無し\n[概念述語] (1)<奏した> (2)<殆どだった> (3)<すんだ>"
        },
        {
            "input": {
                "sentence": "事故を起こしたエスカレーターは閉鎖された。",
                "preprocessed_sentences": "1. 事故を起こしたエスカレーターは閉鎖された"
            },
            "output": "[事象述語] (1)<起こした> (2)<閉鎖された>\n[概念述語] 無し"
        },
        {
            "input": {
                "sentence": "警視庁は、モーターなどを押収し、電気系統のトラブルについても調べるとともに、事故当時エスカレーターに何人乗せていたのか関係者から聴取した。",
                "preprocessed_sentences": "1. 警視庁はモーターなどを押収し\n2. 電気系統のトラブルについても調べるとともに\n3. 事故当時エスカレーターに何人乗せていたのか関係者から聴取した"
            },
            "output": "[事象述語] (1)<押収し> (2)<調べる> (3)<乗せていた> (4)<聴取した>\n[概念述語] 無し"
        },
        {
            "input": {
                "sentence": "エスカレーターに定員があることすら知らない人が多いため、定員表示や過搭乗防止PRを徹底する必要がある。",
                "preprocessed_sentences": "1. エスカレーターに定員があることすら知らない人が多いため\n2. 定員表示や過搭乗防止PRを徹底する必要がある"
            },
            "output": "[事象述語] 無し\n[概念述語] (1)<定員がある> (2)<知らない> (3)<多い> (4)<徹底する> (5)<必要がある>"
        },
        {
            "input": {
                "sentence": "一方エスカレーターとしても、逆走防止のブレーキ能力を上げ、荷重オーバー時の停止から逆走に至る間の余裕を拡大させるなどのより安全サイドに立った構造にすることも必要である。",
                "preprocessed_sentences": "1. 一方エスカレーターとしても\n2. 逆走防止のブレーキ能力を上げ\n3. 荷重オーバー時の停止から逆走に至る間の余裕を拡大させるなどのより安全サイドに立った構造にすることも必要である"
            },
            "output": "[事象述語] 無し\n[概念述語] (1)<上げる> (2)<至る> (3)<拡大させる> (4)<立った> (5)<構造にする> (6)<必要である>"
        },
        {
            "input": {
                "sentence": "エスカレーターのかけ上がりによる事故防止ばかりに目を取られ、警備員が乗員の先頭に立ち、エスカレーターへの乗り込みは規制しなかったため、エスカレーターの定員オーバーを誘発したこと。",
                "preprocessed_sentences": "1. エスカレーターのかけ上がりによる事故防止ばかりに目を取られ\n2. 警備員が乗員の先頭に立ち\n3. エスカレーターへの乗り込みは規制しなかったため\n4. エスカレーターの定員オーバーを誘発したこと"
            },
            "output": "[事象述語] (1)<取られ> (2)<立ち> (3)<規制しなかった> (4)<誘発した>\n[概念述語] 無し"
        },
        {
            "input": {
                "sentence": "警備員にも、エスカレーターの定員に関する知識が欠如していたと考えられる。",
                "preprocessed_sentences": "1. 警備員にもエスカレーターの定員に関する知識が欠如していたと考えられる"
            },
            "output": "[事象述語] (1)<欠如していた>\n[概念述語] (1)<考えられる>"
        },
        {
            "input": {
                "sentence": "国土交通省は、都道府県と業界団体「日本エレベータ協会」に対し、 ",
                "preprocessed_sentences": "1. 国土交通省は都道府県と業界団体「日本エレベータ協会」に対し"
            },
            "output": "[事象述語] 無し\n[概念述語] 無し"
        },
        {
            "input": {
                "sentence": "運営実態を把握し、設計以上の積載荷重にならない",
                "preprocessed_sentences": "1. 運営実態を把握し\n2. 設計以上の積載荷重にならない"
            },
            "output": "[事象述語] (1)<把握し>\n[概念述語] (1)<ならない>"
        },
        {
            "input": {
                "sentence": "特にイベントなどで第三者に利用させる場合、適正な管理を確保させる 。",
                "preprocessed_sentences": "1. (2)特にイベントなどで第三者に利用させる場合\n2. 適正な管理を確保させる"
            },
            "output": "[事象述語] 無し\n[概念述語] (1)<利用させる> (2)<確保させる>"
        }
    ]

    # (3) APIを呼び出す
    response = client.chat.completions.create(
        model="gpt-4o",
        messages = [
            {"role": "system", "content": "You are an assistant that extracts predicates from a sentence."},
            {"role": "user", "content": prompt},
            *(
                item
                for example in examples
                for item in [
                    {"role": "user", "content": f"原文:\n{example['input']['sentence']}\n\n短文分割結果:\n{example['input']['preprocessed_sentences']}\n\n"},
                    {"role": "assistant", "content": f"結果:\n{example['output']}"}
                ]
            ),
            {"role": "user", "content": f"原文:\n{sentence}\n\n短文分割結果:\n{preprocessed_sentences}\n\n"}
        ],
        temperature=0.0
    )

    content = response.choices[0].message.content.strip()
    log_token_usage(response.usage.total_tokens)

    event_predicates = []
    entity_predicates = []

    # (4) 正規表現で抽出
    event_match = re.search(r"\[事象述語\](.*?)\[", content, re.DOTALL)
    if event_match:
        event_predicates = [pred.strip() for pred in re.findall(r"<(.*?)>", event_match.group(1))]

    entity_match = re.search(r"\[概念述語\](.*)", content, re.DOTALL)
    if entity_match:
        entity_predicates = [pred.strip() for pred in re.findall(r"<(.*?)>", entity_match.group(1))]

    return event_predicates, entity_predicates

def extract_entity_and_predicate_structures(sentence: str, event_predicates: list, entity_predicates: list, time_list: list, place_list: list) -> tuple:
    '''
    事象述語・概念述語を基に、述語項構造と追加エンティティを抽出する関数。
    - sentence : 処理対象の原文
    - event_predicates : 事象述語のリスト
    - entity_predicates : 概念述語のリスト
    - time_list : 時間表現のリスト
    - place_list : 場所表現のリスト
    - return : (述語項構造リスト, エンティティリスト)
    '''
    predicate_argument_structures = []
    entities = []

    try:
        # (1) 時間や場所情報を文字列化
        time_str = ", ".join(time_list) if time_list else ""
        place_str = ", ".join(place_list) if place_list else ""
        # (2) GPTに与えるプロンプト
        prompt = (
            "[タスク目的]\n\n"
            "入力文に対して、事象に関する述語を基に述語項構造を抽出し、概念に関する述語を基にエンティティ(名詞句化された概念)を抽出する。本タスクの最終目的は、文書全体をグラフ構造で表現する際のノードとなる情報を得ることである。\n\n"
            "ここで得られるノードには主に2種類存在する：\n\n"
            "1. 述語項構造ノード：事象(事故やイベントなど、時間的変化や行為を表す述語)を中心に格要素を付与した構造。\n"
            "2. エンティティノード：主に概念や状態、属性などを名詞句として抽出したノード。\n\n"
            "なお、事象述語を持たないが事件性があるような名詞表現(「ガクッという音」や「ショック」など)や、完全な行為ではないが将来的にエッジによって他の事象と関係付けられる名詞的要素もエンティティとして抽出することを想定する。\n\n"
            "また、概念的な属性や状態(「定員がある」「人が多い」など)も、そのまま述語として扱わず、可能な限り名詞句化してエンティティノードにまとめておく。\n\n"
            "最終的には、こうした述語項構造ノード同士やエンティティノードと述語項構造ノードをエッジで結び、事故の流れや原因・結果関係をグラフ構造で表現することが目的である。\n\n"
            "[背景知識・用語説明]\n\n"
            "1. 述語の分類\n"
            "    - 事象に関する述語\n"
            "      現実世界で発生した行為・変化・イベントを説明する述語。\n"
            "      例：「太郎は学校へ行った」の「行った」、「彼は授業を受けた」の「受けた」\n"
            "    - 概念に関する述語\n"
            "      抽象的な内容や属性、状態を説明する述語。\n"
            "      例：「問題がある」、「私は学生である」、「必要がある」\n"
            "      これらは事件性がなく、単なる状態や属性表現である。\n\n"
            "2. 述語項構造\n"
            "    述語と、それに関係する名詞格（格）を含む情報です。\n"
            "    例：「次郎は太郎にラーメンを食べるように勧めた」\n"
            "    - 食べる(述語), 太郎(ガ格), ラーメン(ヲ格)\n"
            "    - 勧めた(述語), 次郎(ガ格), 太郎(ニ格), ラーメン(ヲ格)\n\n"
            "    格助詞に対応する格:\n"
            "      ガ格, ヲ格, ニ格, ト格, カラ格, ヨリ格, へ格, マデ格, トシテ格, トイウ格, ニシテ格など\n\n"
            "3. 外の関係\n"
            "    内の関係(ガ格, ヲ格, ニ格など)で表せない関係は「外の関係」として扱います。\n"
            "    例:\n"
            "    - 「政治家が賄賂をもらった事実」\n"
            "        - もらった(述語), 政治家(ガ格), 賄賂(ヲ格), 事実(外の関係)\n"
            "    - 「長い相撲は足腰に負担がかかる」\n"
            "        - かかる(述語), 負担(ガ格), 足腰(ニ格), 長い相撲(外の関係)\n\n"
            "4. 事態性名詞\n"
            "    動作・状態・現象を表す名詞で、サ変動詞として扱えるもの。\n"
            "    例:「統制(する)」, 「確認(した)」, 「インストール(する)」\n\n"
            "5. 修飾語\n"
            "    他の文節にかかり意味を詳しくする語句。\n"
            "    - 連体修飾語: 名詞を修飾する語句。\n"
            "      例: 「美しい花が咲く」の「美しい」\n"
            "    - 連用修飾語: 動詞や形容詞を修飾する語句。\n"
            "      例: 「美しく花が咲く」の「美しく」\n\n"
            "[補足・留意点]\n\n"
            "1. 修飾語の扱い\n"
            "    - 連体修飾語: 格要素に含める。\n"
            "      例: 「美味しいラーメンを食べる」 → 「食べる(述語), 美味しいラーメン(ヲ格)」\n"
            "    - 連用修飾語: 述語の修飾語として扱う。\n"
            "      例: 「速く食べる」 → 「食べる(述語), 速く(修飾)」\n\n"
            "2. 複合名詞の扱い\n"
            "    - 分割せず一塊として扱う。\n"
            "      例: 「離党問題」は「離党問題」\n"
            "      例: 「文化庁の2005年の報告」\n\n"
            "3. 特定の述語の扱い\n"
            "    - 意味を持つ最低限の格要素を含めて扱う。\n"
            "      例: 「けがをした」 → 「けがをした(述語)」\n"
            "      例: 「においがする」 → 「においがする(述語)」\n\n"
            "4. 因果関係を表す格要素の扱い\n"
            "    述語項構造を抽出する際、格要素が因果関係（原因事象と結果事象）を示す場合は、原則としてその格要素を述語項構造の格要素に組み込まず、別途エンティティとして抽出する。例えば、例(1)では「睡眠不足」という原因事象を「睡眠不足(デ格)」のように格要素ではなく、エンティティの「睡眠不足」として抽出する。\n"
            "    ただし、述語項構造そのものが因果関係の原因事象または結果事象として成立する場合は、そのまま述語項構造を抽出する。例えば、「定員以上の乗客が乗り込んだため」の文では「乗り込んだ(述語), 定員以上の乗客(ガ格)」の述語項構造そのものが原因事象のため、述語項構造として抽出する。\n"
            "    つまり、格要素がの原因事象や結果事象を表すと判断できる場合のみエンティティとして抽出する。一方、例(2)のように格要素が外の関係(外の関係)である場合は、外の関係としてもエンティティとしても同時に抽出することを想定する。\n\n"
            "    例(1): あの学生は睡眠不足で今日も授業中に集中できずうとうとしている。\n"
            "    [述語項構造]\n"
            "    (1) 集中できず(述語), あの学生(ガ格), 授業中(ニ格)\n"
            "    (2) うとうとしている(述語), あの学生(ガ格)\n"
            "    [エンティティ]\n"
            "    (1) 睡眠不足\n\n"
            "    例(2): 突然手前で起きた交通事故のため、彼は病院に入院し、重要な会議に遅刻した。\n"
            "    [述語項構造]\n\n"
            "    (1) 起きた(述語), 突然(修飾), 手前(デ格), 交通事故(外の関係)\n"
            "    (2) 入院し(述語), 彼(ガ格), 病院(ニ格)\n"
            "    (3) 遅刻した(述語), 彼(ガ格), 重要な会議(ニ格)\n"
            "    [エンティティ]\n"
            "    (1) 交通事故\n\n"
            "5. 概念述語に関するエンティティ抽出\n"
            "    抽象的概念や状態、属性などは、直接事件性を持たないためエンティティとして名詞句化して表現する。\n\n"
            "6. 事件性(事象)判断基準と名詞表現の扱い\n"
            "    - 事象述語は、行為や発生・変化など、時間経過とともに起こる出来事を表す述語を指す。\n"
            "    - 単なる状態・属性・概念表現は事象述語ではないため、エンティティノードにする。\n"
            "    - ガクッという音やショックなど、事件性を明確に持たない名詞表現はエンティティとして扱い、後にエッジで他の事象と関連付けることを想定。\n"
            "    - 名詞で事件性を表そうとしている場合(「事故防止ばかりに目を取られ」など)は、エンティティとして抽出し、後で別の事象ノードと関係づけることを想定。\n\n"
            "7. 時間表現・場所表現の扱い\n"
            "    他タスクで既に抽出された時間表現・場所表現は新たなエンティティとして扱う必要はない。本タスクでは無視し、述語項構造やエンティティ抽出時には考慮しなくてよい。\n\n"
            "[入力に関する説明]\n"
            "以下の情報を基に文を分析します：\n"
            "時間表現・場所表現はすでに確定済みの情報であり、本タスクでは無視して他の情報抽出に専念する。\n"
            "- 文: 分析対象の文\n"
            "- 事象述語\n"
            "- 概念述語\n"
            "- 時間表現\n"
            "- 場所表現\n\n"
            "[出力形式]\n"
            "[述語項構造]\n"
            "(1) 述語(述語), 修飾語1(修飾), 修飾語2(修飾), 名詞1(格), 名詞2(格)\n"
            "(2) 述語(述語), 修飾語1(修飾), 修飾語2(修飾), 名詞1(格), 名詞2(格)…\n"
            "[エンティティ]\n"
            "(1) エンティティ\n"
            "(2) エンティティ\n\n"
            "[指示]\n"
            "1. 文と事象述語を参照し、述語項構造(事件性のある行為・変化)を抽出する。\n"
            "2. 文と概念述語を参照し、エンティティ(名詞句化した概念・状態・属性)を抽出する。\n"
            "   - 原則として事件性のない述語は名詞句化してエンティティとして扱う\n"
            "   - 状態・属性表現(「多い」「問題がある」)も可能な限り名詞化してエンティティ化\n"
            "   - 事件性が明確でない名詞表現もエンティティとして抽出\n"
            "3. 時間表現・場所表現は無視する(既知情報として扱い、ここで新たにエンティティ化しない)。\n"
            "4. 抽出結果を指定形式で出力する。\n"
        )
        examples = [
            {
                "input": {
                    "sentence": "東京ビッグサイトのエスカレーターにおいて、定員以上の乗客が乗り込んだため、ガクッという音とショックの後エスカレーターは停止し逆走した。",
                    "event_predicates": ["乗り込んだ", "停止し", "逆走した"],
                    "entity_predicates": [],
                    "time": [], 
                    "place": ["東京ビッグサイトのエスカレーター"]  
                },
                "output": "[述語項構造]\n"
                        "(1) 乗り込んだ(述語), 定員以上の乗客(ガ格)\n"
                        "(2) 停止し(述語), エスカレーター(ガ格)\n"
                        "(3) 逆走した(述語), エスカレーター(ガ格)\n"
                        "[エンティティ]\n"
                        "(1) ガクッという音\n"
                        "(2) ショック"
            },
            {
                "input": {
                    "sentence": "客達は、エスカレーターの乗り口付近で仰向けに折り重なるようにして倒れ、10人がエスカレーターの段差に体をぶつけ足首を切ったり、軽い打撲のけがをした。",
                    "event_predicates": ["折り重なる", "倒れ", "ぶつけ", "切ったり", "けがをした"],
                    "entity_predicates": [],
                    "time": [], 
                    "place": ["エスカレーターの乗り口付近"]  
                },
                "output": "[述語項構造]\n"
                        "(1) 折り重なる(述語), 客達(ガ格), 仰向け(ニ格)\n"
                        "(2) 倒れ(述語), 客達(ガ格)\n"
                        "(3) ぶつけ(述語), 10人(ガ格), エスカレーターの段差(ニ格), 体(ヲ格)\n"
                        "(4) 切ったり(述語), 10人(ガ格), 足首(ヲ格)\n"
                        "(5) けがをした(述語), 10人(ガ格), 軽い打撲(ノ格)\n"
                        "[エンティティ]\n"
                        "無し"
            },
            {
                "input": {
                    "sentence": "エスカレーターは、荷重オーバーで自動停止しさらにブレーキも効かず逆走・降下した。",
                    "event_predicates": ["自動停止し", "効かず", "逆走・降下した"],
                    "entity_predicates": [],
                    "time": [], 
                    "place": []
                },
                "output": "[述語項構造]\n"
                        "(1) 自動停止し(述語), エスカレーター(ガ格)\n"
                        "(2) 効かず(述語), ブレーキ(ガ格)\n"
                        "(3) 逆走・降下した(述語), エスカレーター(ガ格)\n"
                        "[エンティティ]\n"
                        "(1) 荷重オーバー\n"
            },
            {
                "input": {
                    "sentence": "ただ、荷重オーバーによる停止を超えて、ブレーキ能力に限界があり逆走が発生したので、エスカレーターの機構にも問題がある可能性も考えられる。",
                    "event_predicates": ["停止", "発生した"],
                    "entity_predicates": ["超えて", "限界があり", "問題がある", "考えられる"],
                    "time": [], 
                    "place": []
                },
                "output": "[述語項構造]\n"
                        "(1) 停止(述語)\n"
                        "(2) 発生した(述語), 逆走(ガ格)\n"
                        "[エンティティ]\n"
                        "(1) 荷重オーバー\n"
                        "(2) ブレーキ能力の限界\n"
                        "(3) エスカレーターの機構の問題"
            },
            {
                "input": {
                    "sentence": "また、エスカレーターの逆走により、極めて高い密度で皆後ろ向きで乗り口付近で折り重なるように倒れたことから、「群集雪崩」が発生したとも考えられる。",
                    "event_predicates": ["逆走", "折り重なる", "倒れた", "発生した"],
                    "entity_predicates": ["考えられる"],
                    "time": [], 
                    "place": ["乗り口付近"]  
                },
                "output": "[述語項構造]\n"
                        "(1) 逆走(述語), エスカレーター(ガ格)\n"
                        "(2) 折り重なる(述語), 皆(ガ格), 極めて高い密度(デ格), 後ろ向き(デ格)\n"
                        "(3) 倒れた(述語), 皆(ガ格)\n"
                        "(4) 発生した(述語), 群集雪崩(ガ格)\n"
                        "[エンティティ]\n"
                        "無し"
            },
            {
                "input": {
                    "sentence": "東京ビッグサイト4階で開催されるアニメのフィギュアの展示・即売会場に直結するエスカレーターにおいて、開場にあたり警備員1人が先頭に立ち誘導し多くの客がエスカレーターに乗り始めた。",
                    "event_predicates": ["開催される", "立ち", "誘導し", "乗り始めた"],
                    "entity_predicates": ["直結する"],
                    "time": [], 
                    "place": ["エスカレーター"] 
                },
                "output": "[述語項構造]\n"
                        "(1) 開催される(述語), 東京ビッグサイト4階(デ格), アニメのフィギュアの展示・即売会(外の関係)\n"
                        "(2) 直結する(述語), アニメのフィギュアの展示・即売会場(ニ格), エスカレーター(外の関係)\n"
                        "(3) 立ち(述語), 警備員1人(ガ格), 先頭に(ニ格)\n"
                        "(4) 誘導し(述語), 警備員1人(ガ格)\n"
                        "(5) 乗り始めた(述語), エスカレーター(ニ格), 多くの客(ガ格)\n"
                        "[エンティティ]\n"
                        "(1) 開場"
            },
            {
                "input": {
                    "sentence": "客達は先を争うようにエスカレーターに乗り込んだが、先頭は警備員が規制していたため、エスカレーターの1段に3～4人が乗るほどのすし詰め状態となった。",
                    "event_predicates": ["争う", "乗り込んだ", "規制していた", "乗る", "すし詰め状態となった"],
                    "entity_predicates": [],
                    "time": [], "place": []  
                },
                "output": "[述語項構造]\n"
                        "(1) 争う(述語), 先(ヲ格), 客達(ガ格)\n"
                        "(2) 乗り込んだ(述語), 客達(ガ格), エスカレーター(ニ格)\n"
                        "(3) 規制していた(述語), 先頭(ヲ格), 警備員(ガ格)\n"
                        "(4) 乗る(述語), エスカレーターの1段(ヲ格), 3～4人(数量格)\n"
                        "(5) すし詰め状態となった(述語)\n"
                        "[エンティティ]\n"
                        "無し"
            },
            {
                "input": {
                    "sentence": "先頭が全長35mの7～8割ほどまで上がったところで、ガクッという音とショックを受けエスカレーターは停止し、その後下りエスカレーターよりも速い速度で逆走・降下しはじめた。",
                    "event_predicates": ["上がった", "受け", "停止し", "逆走・降下しはじめた"],
                    "entity_predicates": [],
                    "time": [], "place": []
                },
                "output": "[述語項構造]\n"
                        "(1) 上がった(述語), 先頭(ガ格), 全長35mの7～8割ほど(マデ格)\n"
                        "(2) 受け(述語), ショック(ヲ格)\n"
                        "(3) 停止し(述語), エスカレーター(ガ格)\n"
                        "(4) 逆走・降下しはじめた(述語), エスカレーター(ガ格), 下りエスカレーター(ヨリ格), 速い速度(デ格)\n"
                        "[エンティティ]\n"
                        "(1) ガクッという音"
            },
            {
                "input": {
                    "sentence": "周囲の人々が、倒れた人を引き起こしたり、移動させるなどの救助に協力した。",
                    "event_predicates": ["倒れた", "引き起こしたり", "移動させる", "協力した"],
                    "entity_predicates": [],
                    "time": [], "place": []
                },
                "output": "[述語項構造]\n"
                        "(1) 倒れた(述語), 人(ガ格)\n"
                        "(2) 引き起こしたり(述語), 周囲の人々(ガ格), 人(ヲ格)\n"
                        "(3) 移動させる(述語), 周囲の人々(ガ格), 人(ヲ格)\n"
                        "(4) 協力した(述語), 周囲の人々(ガ格), 救助(ニ格)\n"
                        "[エンティティ]\n"
                        "無し"
            },
            {
                "input": {
                    "sentence": "関係者が異常に気付き緊急停止ボタンを押したり、逆走により乗員が減ったことからブレーキが効き始め、逆走は停止した。",
                    "event_predicates": ["気付き", "押したり", "逆走", "減った", "効き始め", "停止した"],
                    "entity_predicates": [],
                    "time": [], "place": []
                },
                "output": "[述語項構造]\n"
                        "(1) 気付き(述語), 関係者(ガ格), 異常(ニ格)\n"
                        "(2) 押したり(述語), 関係者(ガ格), 緊急停止ボタン(ヲ格)\n"
                        "(3) 逆走(述語)\n"
                        "(4) 減った(述語), 乗員(ガ格), 逆走(ニヨッテ格)\n"
                        "(5) 効き始め(述語), ブレーキ(ガ格)\n"
                        "(6) 停止した(述語), 逆走(ガ格)\n"
                        "[エンティティ]\n"
                        "無し"
            },
            {
                "input": {
                    "sentence": "このエスカレーターは、荷重制限が約7.5t、逆送防止用ブレーキ能力の限界が約9.3tであったのに対し、事故当時は約120人が乗車したことから、逆送防止用ブレーキ能力の限界荷重をもオーバーし自動停止しさらにブレーキも効かず逆走・降下した。",
                    "event_predicates": ["乗車した", "オーバーし", "自動停止し", "効かず", "逆走・降下した"],
                    "entity_predicates": ["約9.3tであった"],
                    "time": ["事故当時"], "place": []
                },
                "output": "[述語項構造]\n"
                        "(1) 乗車した(述語), 約120人(ガ格)\n"
                        "(2) 自動停止し(述語), エスカレーター(ガ格)\n"
                        "(3) 効かず(述語), ブレーキ(ガ格)\n"
                        "(4) 逆走・降下した(述語), エスカレーター(ガ格)\n"
                        "[エンティティ]\n"
                        "(1) 荷重制限が約7.5t\n"
                        "(2) 逆送防止用ブレーキ能力の限界が約9.3tであった\n"
                        "(3) 逆送防止用ブレーキ能力の限界荷重をもオーバー"
            },
            {
                "input": {
                    "sentence": "ただ、荷重制限とブレーキ能力の限界までには、(9.3-7.5=）1.8tの余裕があるはずなのに、停止してすぐ逆走したことから、エスカレーターの機構にも問題がある可能性もある。",
                    "event_predicates": ["停止して", "逆走した"],
                    "entity_predicates": ["余裕がある", "問題がある", "可能性もある"],
                    "time": [], "place": []
                },
                "output": "[述語項構造]\n"
                        "(1) 停止して(述語)\n"
                        "(2) 逆走した(述語)\n"
                        "[エンティティ]\n"
                        "(1) 荷重制限とブレーキ能力の限界までには、(9.3-7.5=）1.8tの余裕がある\n"
                        "(2) エスカレーターの機構にも問題がある"
            },
            {
                "input": {
                    "sentence": "また、1段あたり3～4人乗車しており、「人口密度」は8.6人/平方メートルにも達している。",
                    "event_predicates": ["乗車しており"],
                    "entity_predicates": ["達している"],
                    "time": [], "place": []
                },
                "output": "[述語項構造]\n"
                                    "(1) 乗車しており(述語), 3～4人(ガ格), 1段あたり(外の関係)\n"
                        "[エンティティ]\n"
                        "(1) 人口密度」は8.6人/平方メートルにも到達"
            },
            {
                "input": {
                    "sentence": "さらに皆後ろ向きで乗り口付近で折り重なるように倒れ人口密度は増大し、「群集雪崩」が発生したことがけが人発生の原因である。",
                    "event_predicates": ["折り重なる", "倒れ", "発生した"],
                    "entity_predicates": ["増大し", "原因である"],
                    "time": [], 
                    "place": ["乗り口付近"]
                },
                "output": "[述語項構造]\n"
                        "(1) 折り重なる(述語), 皆(ガ格), 後ろ向き(デ格)\n"
                        "(2) 倒れ(述語), 皆(ガ格)\n"
                        "(3) 発生した(述語), 群集雪崩(ガ格)\n"
                        "[エンティティ]\n"
                        "(1) 人口密度の増大\n"
                        "(2) けが人の発生"
            },
            {
                "input": {
                    "sentence": "周囲の人々の救助が功を奏したのと被害者は若者が殆どだったので、軽傷程度のけがですんだ。",
                    "event_predicates": [],
                    "entity_predicates": ["奏した", "殆どだった", "すんだ"],
                    "time": [], "place": []
                },
                "output": "[述語項構造]\n"
                        "無し\n"
                        "[エンティティ]\n"
                        "(1) 周囲の人々の救助が功を奏した結果\n"
                        "(2) 被害者は若者が大半\n"
                        "(3) 軽傷程度で収まった状態"
            },
            {
                "input": {
                    "sentence": "事故を起こしたエスカレーターは閉鎖された。",
                    "event_predicates": ["起こした", "閉鎖された"],
                    "entity_predicates": [],
                    "time": [], "place": []
                },
                "output": "[述語項構造]\n"
                        "(1) 起こした(述語), 事故(ヲ格), エスカレーター(外の関係)\n"
                        "(2) 閉鎖された(述語), エスカレーター(ガ格)\n"
                        "[エンティティ]\n"
                        "無し"
            },
            {
                "input": {
                    "sentence": "警視庁は、モーターなどを押収し、電気系統のトラブルについても調べるとともに、事故当時エスカレーターに何人乗せていたのか関係者から聴取した。",
                    "event_predicates": ["押収し", "調べる", "乗せていた", "聴取した"],
                    "entity_predicates": [],
                    "time": [], "place": []
                },
                "output": "[述語項構造]\n"
                        "(1) 押収し(述語), モーターなど(ヲ格), 警視庁(ガ格)\n"
                        "(2) 調べる(述語), 電気系統のトラブル(ニツイテ格), 警視庁(ガ格)\n"
                        "(3) 乗せていた(述語), エスカレーター(ニ格), 何人(ヲ格)\n"
                        "(4) 聴取した(述語), 関係者(カラ格), 警視庁(ガ格)\n"
                        "[エンティティ]\n"
                        "無し"
            },
            {
                "input": {
                    "sentence": "エスカレーターに定員があることすら知らない人が多いため、定員表示や過搭乗防止PRを徹底する必要がある。",
                    "event_predicates": [],
                    "entity_predicates": ["定員がある", "知らない", "多い", "徹底する", "必要がある"],
                    "time": [], "place": []
                },
                "output": "[述語項構造]\n"
                        "無し\n"
                        "[エンティティ]\n"
                        "(1) エスカレーターの定員\n"
                        "(2) 定員を知らない多数の人々\n"
                        "(3) 定員表示や過搭乗防止PRの徹底"
            },
            {
                "input": {
                    "sentence": "一方エスカレーターとしても、逆走防止のブレーキ能力を上げ、荷重オーバー時の停止から逆走に至る間の余裕を拡大させるなどのより安全サイドに立った構造にすることも必要である。",
                    "event_predicates": [],
                    "entity_predicates": ["上げる", "至る", "拡大させる", "立った", "構造にする", "必要である"],
                    "time": [], "place": []
                },
                "output": "[述語項構造]\n"
                        "無し\n"
                        "[エンティティ]\n"
                        "(1) 逆走防止のブレーキ能力向上\n"
                        "(2) 荷重オーバー時の停止から逆走に至る間の余裕の拡大\n"
                        "(3) より安全サイドに立った構造"
            },
            {
                "input": {
                    "sentence": "エスカレーターのかけ上がりによる事故防止ばかりに目を取られ、警備員が乗員の先頭に立ち、エスカレーターへの乗り込みは規制しなかったため、エスカレーターの定員オーバーを誘発したこと。",
                    "event_predicates": ["取られ", "立ち", "規制しなかった", "誘発した"],
                    "entity_predicates": [],
                    "time": [], "place": []
                },
                "output": "[述語項構造]\n"
                        "(1) 取られ(述語), 警備員(ガ格), 目(ヲ格), 事故防止ばかり(ニ格)\n"
                        "(2) 立ち(述語), 警備員(ガ格), 乗員の先頭(ニ格)\n"
                        "(3) 規制しなかった(述語), 警備員(ガ格), 乗り込み(ヲ格)\n"
                        "(4) 誘発した(述語), エスカレーターの定員オーバー(ヲ格)\n"
                        "[エンティティ]\n"
                        "(1) エスカレーターのかけ上がりによる事故"
            },
            {
                "input": {
                    "sentence": "警備員にも、エスカレーターの定員に関する知識が欠如していたと考えられる。",
                    "event_predicates": ["欠如していた"],
                    "entity_predicates": ["考えられる"],
                    "time": [], "place": []
                },
                "output": "[述語項構造]\n"
                        "無し\n"
                        "[エンティティ]\n"
                        "(1) エスカレーターの定員に関する知識\n"
                        "(2) 警備員の知識欠如"
            },
            {
                "input": {
                    "sentence": "国土交通省は、都道府県と業界団体「日本エレベータ協会」に対し、 ",
                    "event_predicates": [],
                    "entity_predicates": [],
                    "time": [], "place": []
                },
                "output": "[述語項構造]\n"
                        "無し\n"
                        "[エンティティ]\n"
                        "無し"
            },
            {
                "input": {
                    "sentence": "運営実態を把握し、設計以上の積載荷重にならない",
                    "event_predicates": ["把握し"],
                    "entity_predicates": ["ならない"],
                    "time": [], "place": []
                },
                "output": "[述語項構造]\n"
                        "無し\n"
                        "[エンティティ]\n"
                        "(1) 運営実態を把握\n"
                        "(2) 設計以上の積載荷重にならない状態"
            },
            {
                "input": {
                    "sentence": "特にイベントなどで第三者に利用させる場合、適正な管理を確保させる 。",
                    "event_predicates": [],
                    "entity_predicates": ["利用させる", "確保させる"],
                    "time": [], "place": []
                },
                "output": "[述語項構造]\n"
                        "無し\n"
                        "[エンティティ]\n"
                        "(1) イベント\n"
                        "(2) 第三者利用\n"
                        "(3) 適正な管理の確保"
            }
        ]
        messages = [
            {"role": "system", "content": "You are an assistant that extracts predicate-argument structures and entities from sentences."},
            {"role": "user", "content": prompt}
        ]
        for example in examples:
            example_input_str = (
                f"文:{example['input']['sentence']}\n"
                f"事象述語:{', '.join(example['input']['event_predicates'])}\n"
                f"概念述語:{', '.join(example['input']['entity_predicates'])}\n"
                f"時間表現:{example['input']['time']}\n"
                f"場所表現:{example['input']['time']}\n\n"
            )
            example_output_str = example['output']
            messages.append({"role": "user", "content": example_input_str})
            messages.append({"role": "assistant", "content": example_output_str})
        final_input = (
            f"文: {sentence}\n"
            f"事象述語: {', '.join(event_predicates)}\n"
            f"概念述語: {', '.join(entity_predicates)}\n"
            f"時間表現: {time_str}\n"
            f"場所表現: {place_str}\n\n"
        )
        messages.append({"role": "user", "content": final_input})

        # (3) 実際にAPIを呼び出す
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.0
        )

        content = response.choices[0].message.content.strip()
        log_token_usage(response.usage.total_tokens)

        # (4) 結果から述語項構造部分とエンティティ部分を抽出
        predicate_argument_section = re.search(r"\[述語項構造\](.*?)\[エンティティ\]", content, re.DOTALL)
        if predicate_argument_section:
            predicate_argument_lines = predicate_argument_section.group(1).strip().split("\n")
            for line in predicate_argument_lines:
                line = line.strip()
                if line.startswith("("):
                    structure = line.split(")", 1)[-1].strip()
                    fixed_structure = fix_predicate_structure_text(structure)
                    predicate_argument_structures.append(fixed_structure)

        entity_section = re.search(r"\[エンティティ\](.*)", content, re.DOTALL)
        if entity_section:
            entity_lines = entity_section.group(1).strip().split("\n")
            for line in entity_lines:
                line = line.strip()
                if line.startswith("("):
                    entity = line.split(")", 1)[-1].strip()
                    entities.append(entity)

    except Exception as e:
        print(f"Error extracting entity and predicate structures: {e}")
        return [], []

    return predicate_argument_structures, entities
import re
from openai import OpenAI
from source.document_parsing.logger import log_token_usage

client = OpenAI()

def split_into_sentences(text: str) -> str:
    """
    문장을 단문으로 나누고 번호를 부여한 후 합친 텍스트를 반환.
    """
    # 간단한 문장 분리 (句点, 쉼표, 세미콜론 등 기준)
    sentences = re.split(r'[。！？.;,、]', text)
    # 유효한 문장만 필터링
    valid_sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
    # 번호를 붙여서 단문을 합침
    numbered_sentences = "\n".join(f"({i+1}) {sentence}" for i, sentence in enumerate(valid_sentences))
    return numbered_sentences

def extract_predicates(sentence: str) -> tuple:
    """
    문장에서 술어를 추출하는 함수.
    """
    preprocessed_sentences = split_into_sentences(sentence)

    prompt = (
        "[タスク目的]\n"
        "入力文からすべての述語を特定し、その後、事象に関する記述をする述語と概念に関する記述をする述語を区別する。\n\n"
        "[背景知識・用語説明]\n\n"
        "1. 述語とは文を構成する重要な文節の一つで、主語を受けその動作・状態・存在を表す。\n"
        "意味的には「どうする」、「どんなだ」、「何だ」、「ある（ない）」を表し、品詞としては動詞・形容詞・形容動詞が含まれる。\n"
        "(述語の例1)「太郎は学校に行った。」という文の述語は「行った」\n"
        "(述語の例2)「彼は授業を受けた。」という文の述語は「受けた」\n\n"
        "2. また、本タスクでは事態性名詞も述語として扱う。\n"
        "事態性名詞とは動作・状態・現象を表す名詞であり、そのほとんどがサ変動詞に該当する。\n"
        "サ変動詞とは「する」、「した」を接続して動詞化できる名詞である。\n"
        "(サ変動詞の例)「統制(する)」、「確認(した)」、「インストール(する)」など\n\n"
        "3. 本タスクでは、述語を以下の2種類に分類する：\n"
        "- 事象に関する述語\n"
        "  事象(事故やイベントなど)に関する記述をする述語は、現実世界で発生した事象を説明する述語である。\n"
        "  例えば、「太郎は学校へ行った」の「行った」や「彼は授業を受けた」の「受けた」がこれに該当する。\n"
        "- 概念に関する述語\n"
        "  概念に関する記述をする述語は、抽象的な内容や現実世界の実体の属性を説明する述語である。\n"
        "  例えば、「問題がある」、「私は学生である」、「必要がある」などがこれに該当する。\n\n"
        "[補足・留意点]\n\n"
        "1. 述語として機能する事態性名詞のみを対象とし、それ以外の具体的な実体を指す名詞は対象外とする。\n"
        "(例)「彼からの電話(i)によると、私は彼の家に電話(j)を忘れたらしい。」\n"
        "電話(i)は「電話する」の意味を表し述語に該当するが、電話(j)は具体的な実体を指すため対象外とする。\n\n"
        "2. 複合名詞は分割せずに一つの単位として扱う。\n"
        "- (例) 「離党問題」は「離党問題」として分析する。\n"
        "- また、「の」で連結された名詞も分割せず、一つの塊として扱う。\n"
        "- (例)「文化庁の2005年の報告」は一つの塊として扱う。\n\n"
        "3. 意味を持つ最低限の格要素を含む形で述語を捉える。\n"
        "- (例) 「けがをした」は「けがをした」として述語を抽出する。\n"
        "- (例) 「においがする」も「においがする」として述語を抽出する。\n\n"
        "[入力に関する説明]\n"
        "以下の文は複文であり、述語を正確に特定するために次のように前処理を行いました。\n"
        "前処理を行う理由は、複雑な構造を持つ複文では、文を分割することで述語の特定が容易になるためです。\n\n"
        "- 原文: 元の文をそのまま提示します。\n"
        "- 分割した文: 文を句点 (。)、読点 (、)、およびセミコロン (;) を基準として分割し、それぞれ順番に番号を付けました。\n\n"
        "[出力形式]\n"
        "結果は以下の形式で出力してください：\n"
        "[事象述語] (1)<述語1> (2)<述語2> (3)<述語3> …\n"
        "[概念述語] (1)<述語1> (2)<述語2> (3)<述語3> …\n\n"
        "[指示]\n\n"
        "1. 原文を参照し、述語を抽出します。\n"
        "2. 短文分割された文を参照し、追加の述語を抽出します。\n"
        "3. 両者を統合し、原文の順序を守りつつ重複を避けて文中のすべての述語を網羅します。\n"
        "4. 網羅した述語を事象に関する述語と概念に関する述語に分類し、結果を出力します。\n"
    )

    examples = [
        {
            "input": {
                "sentence": "東京ビッグサイトのエスカレーターにおいて、定員以上の乗客が乗り込んだため、ガクッという音とショックの後エスカレーターは停止し逆走した。",
                "preprocessed_sentences": "1. 東京ビッグサイトのエスカレーターにおいて\n2. 定員以上の乗客が乗り込んだ\n3. ガクッという音とショックの後エスカレーターは停止し\n4. 逆走した"
            },
            "output": "[事象述語] (1)<乗り込んだ> (2)<音> (3)<ショック> (4)<停止し> (5)<逆走した>\n[概念述語] 無し"
        },
        {
            "input": {
                "sentence": "客達は、エスカレーターの乗り口付近で仰向けに折り重なるようにして倒れ、10人がエスカレーターの段差に体をぶつけ足首を切ったり、軽い打撲のけがをした。",
                "preprocessed_sentences": "1. 客達はエスカレーターの乗り口付近で仰向けに折り重なるようにして倒れ\n2. 10人がエスカレーターの段差に体をぶつけ\n3. 足首を切ったり\n4. 軽い打撲のけがをした"
            },
            "output": "[事象述語] (1)<倒れ> (2)<ぶつけ> (3)<切ったり> (4)<けがをした>\n[概念述語] 無し"
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
            "output": "[事象述語] (1)<停止> (2)<発生した> [概念述語] (1)<超えて> (2)<限界があり> (3)<問題がある> (4)<考えられる>"
        },
        {
            "input": {
                "sentence": "また、エスカレーターの逆走により、極めて高い密度で皆後ろ向きで乗り口付近で折り重なるように倒れたことから、「群集雪崩」が発生したとも考えられる。",
                "preprocessed_sentences": "1. エスカレーターの逆走により\n2. 極めて高い密度で皆後ろ向きで乗り口付近で折り重なるように倒れた\n3. 「群集雪崩」が発生したとも考えられる"
            },
            "output": "[事象述語] (1)<逆走> (2)<倒れた> (3)<発生した> [概念述語] (1)<考えられる>"
        }
    ]

    # 예시를 user→assistant 형식으로 제시
    messages = [
        {"role": "system", "content": "You are an assistant that extracts predicates from a sentence."},
        {"role": "user", "content": prompt}
    ]

    for example in examples:
        example_input = f"原文:\n{example['input']['sentence']}\n\n短文分割結果:\n{example['input']['preprocessed_sentences']}\n\n"
        example_output = example['output']
        # user 메세지로 예시의 입력을 주고
        messages.append({"role": "user", "content": example_input})
        # assistant 메세지로 예시의 출력을 제시
        messages.append({"role": "assistant", "content": example_output})

    # 실제 문장에 대한 요청
    final_input = f"原文:\n{sentence}\n\n短文分割結果:\n{preprocessed_sentences}\n\n"
    messages.append({"role": "user", "content": final_input})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.2
    )

    content = response.choices[0].message.content.strip()
    log_token_usage(response.usage.total_tokens)

    event_predicates = []
    entity_predicates = []

    event_match = re.search(r"\[事象述語\](.*?)\[", content, re.DOTALL)
    if event_match:
        event_predicates = [pred.strip() for pred in re.findall(r"<(.*?)>", event_match.group(1))]

    entity_match = re.search(r"\[概念述語\](.*)", content, re.DOTALL)
    if entity_match:
        entity_predicates = [pred.strip() for pred in re.findall(r"<(.*?)>", entity_match.group(1))]

    return event_predicates, entity_predicates

def extract_predicate_argument_structure(sentence: str, event_predicates: list, entity_predicates: list) -> tuple:
    """
    문장과 추출된 사상 술어(event predicates) 및 개념 술어(entity predicates)를 기반으로
    모든 述語項構造와 엔ティティ 리스트를 생성.
    """
    predicate_argument_structures = []
    entities = []

    try:
        prompt = (
            "[タスク目的]\n\n"
            "入力文に対して、事象に関する述語を基に述語項構造を抽出し、概念に関する述語を基にエンティティを抽出する。\n\n"
            "[背景知識・用語説明]\n\n"
            "1. **述語の分類**\n"
            "    - **事象に関する述語**\n"
            "      事象(事故やイベントなど)に関する記述をする述語は、現実世界で発生した事象を説明する役割を持ちます。\n"
            "      例:\n"
            "        - 「太郎は学校へ行った」の「行った」\n"
            "        - 「彼は授業を受けた」の「受けた」\n"
            "    - **概念に関する述語**\n"
            "      概念(抽象的な内容や実体の属性)を記述する述語です。\n"
            "      例:\n"
            "        - 「問題がある」\n"
            "        - 「私は学生である」\n"
            "        - 「必要がある」\n\n"
            "2. **述語項構造**\n"
            "    述語と、それに関係する名詞格（格）を含む情報です。\n"
            "    例:\n"
            "    - 「次郎は太郎にラーメンを食べるように勧めた」\n"
            "        - (1) 食べる(述語), 太郎(ガ格), ラーメン(ヲ格)\n"
            "        - (2) 勧めた(述語), 次郎(ガ格), 太郎(ニ格), ラーメン(ヲ格)\n"
            "    - 格助詞に対応する格:\n"
            "      ガ格, ヲ格, ニ格, ト格, カラ格, ヨリ格, へ格, マデ格, トシテ格, トイウ格, ニシテ格\n\n"
            "3. **外の関係**\n"
            "    内の関係(ガ格, ヲ格, ニ格など)で表せない関係は「外の関係」として扱います。\n"
            "    例:\n"
            "    - 「政治家が賄賂をもらった事実」\n"
            "        - もらった(述語), 政治家(ガ格), 賄賂(ヲ格), 事実(外の関係)\n"
            "    - 「長い相撲は足腰に負担がかかる」\n"
            "        - かかる(述語), 負担(ガ格), 足腰(ニ格), 長い相撲(外の関係)\n\n"
            "4. **事態性名詞**\n"
            "    動作・状態・現象を表す名詞で、サ変動詞として扱えるもの。\n"
            "    例:\n"
            "    - 「統制(する)」\n"
            "    - 「確認(した)」\n"
            "    - 「インストール(する)」\n\n"
            "5. **修飾語**\n"
            "    他の文節にかかり意味を詳しくする語句。\n"
            "    - **連体修飾語**: 名詞を修飾する語句。\n"
            "      例: 「美しい花が咲く」の「美しい」\n"
            "    - **連用修飾語**: 動詞や形容詞を修飾する語句。\n"
            "      例: 「美しく花が咲く」の「美しく」\n\n"
            "[補足・留意点]\n\n"
            "1. **修飾語の扱い**\n"
            "    - 連体修飾語: 格要素に含める。\n"
            "      例: 「美味しいラーメンを食べる」 → 「美味しいラーメン(ヲ格)」\n"
            "    - 連用修飾語: 述語の修飾語として扱う。\n"
            "      例: 「速く食べる」 → 「速く(修飾)」\n\n"
            "2. **複合名詞の扱い**\n"
            "    - 分割せず一塊として扱う。\n"
            "      例: 「離党問題」は「離党問題」\n"
            "      例: 「文化庁の2005年の報告」\n\n"
            "3. **特定の述語の扱い**\n"
            "    - 意味を持つ最低限の格要素を含めて扱う。\n"
            "      例: 「けがをした」 → 「けがをした(述語)」\n"
            "      例: 「においがする」 → 「においがする(述語)」\n\n"
            "4. **概念述語に関するエンティティ抽出**\n"
            "    - 抽象的概念や筆者の考え、実体の状態などを中心に抽出。\n\n"
            "[入力に関する説明]\n\n"
            "以下の情報を基に文を分析します：\n"
            "- 文\n"
            "- 事象述語\n"
            "- 概念述語\n\n"
            "[出力形式]\n\n"
            "[述語項構造]\n"
            "(1) 述語(述語), 修飾語1(修飾), 修飾語2(修飾), 名詞1(格), 名詞2(格)\n"
            "(2) 述語(述語), 修飾語1(修飾), 修飾語2(修飾), 名詞1(格), 名詞2(格)…\n\n"
            "[エンティティ]\n"
            "(1) エンティティ\n"
            "(2) エンティティ\n\n"
            "[指示]\n\n"
            "1. 文と事象述語を参照し、述語項構造を抽出します。\n"
            "2. 文と概念述語を参照し、エンティティを抽出します。\n"
            "3. 抽出結果を確認し、指定の形式で出力します。\n"
        )

        examples = [
            {
                "input": {
                    "sentence": "東京ビッグサイトのエスカレーターにおいて、定員以上の乗客が乗り込んだため、ガクッという音とショックの後エスカレーターは停止し逆走した。",
                    "event_predicates": ["乗り込んだ", "音", "ショック", "停止し", "逆走した"],
                    "entity_predicates": []
                },
                "output": (
                    "[述語項構造]\n"
                    "(1) 乗り込んだ(述語), 定員以上の乗客(ガ格)\n"
                    "(2) 音(述語), ガクッ(トイウ格)\n"
                    "(3) ショック(述語)\n"
                    "(4) 停止し(述語), エスカレーター(ガ格)\n"
                    "(5) 逆走した(述語), エスカレーター(ガ格)\n"
                    "[エンティティ]\n"
                    "無し"
                )
            },
            {
                "input": {
                    "sentence": "客達は、エスカレーターの乗り口付近で仰向けに折り重なるようにして倒れ、10人がエスカレーターの段差に体をぶつけ足首を切ったり、軽い打撲のけがをした。",
                    "event_predicates": ["倒れ", "ぶつけ", "切ったり", "けがをした"],
                    "entity_predicates": []
                },
                "output": (
                    "[述語項構造]\n"
                    "(1) 倒れ(述語), 客達(ガ格), 仰向け(ニ格), 折り重なるよう(ニシテ格)\n"
                    "(2) ぶつけ(述語), 10人(ガ格), エスカレーターの段差(ニ格), 体(ヲ格)\n"
                    "(3) 切ったり(述語), 10人(ガ格), 足首(ヲ格)\n"
                    "(4) けがをした(述語), 10人(ガ格), 軽い打撲(ノ格)\n"
                    "[エンティティ]\n"
                    "無し"
                )
            },
            {
                "input": {
                    "sentence": "エスカレーターは、荷重オーバーで自動停止しさらにブレーキも効かず逆走・降下した。",
                    "event_predicates": ["自動停止し", "効かず", "逆走・降下した"],
                    "entity_predicates": []
                },
                "output": (
                    "[述語項構造]\n"
                    "(1) 自動停止し(述語), エスカレーター(ガ格)\n"
                    "(2) 効かず(述語), ブレーキ(ガ格)\n"
                    "(3) 逆走・降下した(述語), エスカレーター(ガ格)\n"
                    "[エンティティ]\n"
                    "(1) 荷重オーバー"
                )
            },
            {
                "input": {
                    "sentence": "ただ、荷重オーバーによる停止を超えて、ブレーキ能力に限界があり逆走が発生したので、エスカレーターの機構にも問題がある可能性も考えられる。",
                    "event_predicates": ["停止", "発生した"],
                    "entity_predicates": ["超えて", "限界があり", "問題がある", "考えられる"]
                },
                "output": (
                    "[述語項構造]\n"
                    "(1) 停止(述語)\n"
                    "(2) 発生した(述語), 逆走(ガ格)\n"
                    "[エンティティ]\n"
                    "(1) 荷重オーバー\n"
                    "(2) ブレーキ能力に限界があり\n"
                    "(3) エスカレーターの機構にも問題がある"
                )
            },
            {
                "input": {
                    "sentence": "また、エスカレーターの逆走により、極めて高い密度で皆後ろ向きで乗り口付近で折り重なるように倒れたことから、「群集雪崩」が発生したとも考えられる。",
                    "event_predicates": ["逆走", "倒れた", "発生した"],
                    "entity_predicates": ["考えられる"]
                },
                "output": (
                    "[述語項構造]\n"
                    "(1) 逆走(述語), エスカレーター(ガ格)\n"
                    "(2) 倒れた(述語), 皆(ガ格), 極めて高い密度(デ格), 後ろ向き(デ格)\n"
                    "(3) 発生した(述語), 群集雪崩(ガ格)\n"
                    "[エンティティ]\n"
                    "無し"
                )
            }
        ]

        # 여기서 예시를 user→assistant 쌍으로 제시
        messages = [
            {"role": "system", "content": "You are an assistant that extracts predicate-argument structures and entities from sentences."},
            {"role": "user", "content": prompt}
        ]

        for example in examples:
            example_input_str = (
                f"文:\n{example['input']['sentence']}\n\n"
                f"事象述語:\n{', '.join(example['input']['event_predicates'])}\n\n"
                f"概念述語:\n{', '.join(example['input']['entity_predicates'])}\n\n"
            )
            example_output_str = example['output']
            # user가 예시를 입력
            messages.append({"role": "user", "content": example_input_str})
            # assistant가 예시에 대한 출력 제시
            messages.append({"role": "assistant", "content": example_output_str})

        # 실제 요청 부분
        final_input = (
            f"文: {sentence}\n\n"
            f"事象述語: {', '.join(event_predicates)}\n\n"
            f"概念述語: {', '.join(entity_predicates)}\n\n"
        )
        messages.append({"role": "user", "content": final_input})

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.2
        )

        content = response.choices[0].message.content.strip()
        log_token_usage(response.usage.total_tokens)

        # 述語項構造 파싱
        predicate_argument_section = re.search(r"\[述語項構造\](.*?)\[エンティティ\]", content, re.DOTALL)
        if predicate_argument_section:
            predicate_argument_lines = predicate_argument_section.group(1).strip().split("\n")
            for line in predicate_argument_lines:
                line = line.strip()
                if line.startswith("("):  # "(1) ..." 형식 검사
                    structure = line.split(")", 1)[-1].strip()
                    predicate_argument_structures.append(structure)

        # エンティティ 파싱
        entity_section = re.search(r"\[エンティティ\](.*)", content, re.DOTALL)
        if entity_section:
            entity_lines = entity_section.group(1).strip().split("\n")
            for line in entity_lines:
                line = line.strip()
                if line.startswith("("):  # "(1) ..." 형식 검사
                    entity = line.split(")", 1)[-1].strip()
                    entities.append(entity)

    except Exception as e:
        print(f"Error extracting predicate-argument structure: {e}")

    return predicate_argument_structures, entities
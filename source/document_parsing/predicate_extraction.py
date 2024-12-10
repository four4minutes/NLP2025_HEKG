import re
from openai import OpenAI
from source.document_parsing.token_logger import log_token_usage

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

def extract_predicates(sentence: str) -> list:
    """
    문장에서 술어를 추출하는 함수.
    """

    # 문장을 단문으로 나눔
    preprocessed_sentences = split_into_sentences(sentence)
        
    try:
        prompt = (
            "以下の文は複文であり、述語を正確に特定するために次のように前処理を行いました。\n"
            "前処理を行う理由は、複雑な構造を持つ複文では、文を分割することで述語の特定が容易になるためです。\n"
            "- 原文: 元の文をそのまま提示します。\n"
            "- 分割した文: 文を句点、カンマ、セミコロンなどを基準に文を分割し、それぞれ番号を付けました。\n"
            "述語は文法的に動詞や形容詞として機能する単語です。\n"
            "すべての動詞は述語として扱います。\n"
            "以下の手順で述語を抽出してください：\n"
            "1. 原文を参照し、述語を抽出します。\n"
            "2. 短文分割された文を参照し、追加の述語を抽出します。\n"
            "3. 両者を統合し、文中のすべての述語を網羅します。\n"
            "補足1. 以下のような「形容詞+する」も述語として扱います。\n"
            "(対象文) : 気分を悪くして病院へ搬送された。\n"
            "(結果) : (1)<悪くし> (2)<搬送された>"
            "補足2. 以下のような「名詞+する」も述語として扱います。\n"
            "(対象文) : 事故を目撃した入場客ら13名\n"
            "(結果) : (1)<目撃した>"
            "原文:\n"
            f"{sentence}\n\n"
            "短文分割結果:\n"
            f"{preprocessed_sentences}\n\n"
            "結果は以下の形式で出力してください：\n"
            "(1)<述語1> (2)<述語2> (3)<述語3> ..."
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that extracts predicates from a sentence."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        content = response.choices[0].message.content.strip()
        log_token_usage(response.usage.total_tokens)

        predicates = []
        for item in content.split(" "):
            if item.startswith("(") and ")" in item:
                predicate = item.split(")")[1].strip("<>").strip()
                if predicate:
                    predicates.append(predicate)

        return predicates

    except Exception as e:
        print(f"Error extracting predicates: {e}")
        return []

def extract_predicate_argument_structure(sentence: str, predicates: list) -> list:
    """
    문장과 추출된 술어 리스트를 기반으로 모든 述語項構造를 생성.
    """
    predicate_argument_structures = []

    try:
        explanation = (
            "述語項構造は述語と、その述語と関係を持つ名詞格（格）に関する情報を含んでいます。\n"
            "以下はその例です：\n"
            "(対象文) 次郎は太郎にタンゴを踊るように勧めた\n"
            "(1) 踊る(述語), 太郎(ガ格), タンゴ(ヲ格)\n"
            "(2) 勧めた(述語), 次郎(ガ格), 太郎(ニ格), 踊り(ヲ格)\n"
            "また、各名詞格について文中で「の」によって修飾される場合、その修飾情報も含めて出力してください。\n"
            "以下はその例です：\n"
            "(対象文) 搭乗者1名が車両と左側の鉄柵に頭を挟まれて\n"
            "(3) 挟まれて(述語), 搭乗者1名(ガ格), 車両(ト格), 左側の鉄柵(ニ格), 頭(ヲ格)\n"
            "次に、文中に修飾語が含まれる場合、それも述語項構造に含めてください。\n"
            "以下はその例です：\n"
            "(対象文) ジェットコースターの車輪が突然レールから脱輪し\n"
            "ここで「突然」は「脱輪し」という述語を修飾する修飾語であるため、これも述語項構造に含めてください。その結果、以下のようになります：\n"
            "(4) 脱輪し(述語), 突然(修飾), ジェットコースターの車輪(ガ格), レール(カラ格)\n"
            "また、文中で因果関係を表す名詞格が存在する場合、それを述語項構造に含めないでください。\n"
            "以下はその例です：\n"
            "(対象文) 車輪を支える軸のねじ部が疲労破壊で、切断したため、車輪がレールから脱輪した（図2）\n"
            "ここで「疲労破壊で」は「切断した」という結果事象に対する原因事象に該当する名詞格であるため、これを除外します。その結果、以下のようになります：\n"
            "(5) 切断した(述語), 車輪を支える軸のねじ部(ガ格)\n"
            "(6) 脱輪した(述語), 車輪(ガ格), レール(カラ格)\n"
        )
        predicates_str = ", ".join(predicates)
        instruction = (
            f"{explanation}\n"
            f"文: {sentence}\n"
            f"述語: {predicates_str}\n"
            "結果を以下の形式で出力してください：\n"
            "(1) 述語(述語), 修飾語1(修飾), 修飾語2(修飾), 名詞1(格), 名詞2(格)\n"
            "(2) 述語(述語), 修飾語1(修飾), 修飾語2(修飾), 名詞1(格), 名詞2(格)"
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that extracts predicate-argument structures with expanded noun phrases."},
                {"role": "user", "content": instruction}
            ],
            temperature=0.2
        )

        # 응답 파싱
        content = response.choices[0].message.content.strip()
        log_token_usage(response.usage.total_tokens)

        # 각 술어항 구조를 리스트에 추가
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("("):  # "(1) ..." 형식 검사
                structure = line.split(")", 1)[-1].strip()
                predicate_argument_structures.append(structure)

    except Exception as e:
        print(f"Error extracting predicate-argument structure: {e}")

    return predicate_argument_structures
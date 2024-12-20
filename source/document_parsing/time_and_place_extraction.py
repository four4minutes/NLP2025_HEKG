from openai import OpenAI
import unicodedata
import re

client = OpenAI()

def extract_time_and_place(sentence: str) -> dict:
    """
    문장에서 시간 표현과 장소 표현을 추출하는 함수.
    """
    try:
        prompt = (
            "以下の文から時間表現と場所表現を抽出してください。\n"
            "条件:\n"
            "- 時間表現は年月日、曜日、午前午後、または季節を含む『名詞句』のみ抽出してください。\n"
            "- 場所表現は地名、施設名、または特定の場所を表す『名詞句』のみ抽出してください。\n"
            "- 「の」で連結された名詞句は可能な限り一つの塊として扱ってください。\n"
            "  ただし、名詞以外の修飾表現（形容動詞的な表現、動詞句など）が介入し、\n"
            "  対象名詞を複雑に修飾する場合は、その修飾部分を除外し、\n"
            "  最終的なコア名詞だけを場所表現として抽出してください。\n"
            "- 時間表現・場所表現は複数存在する場合、以下の形式で全て出力してください：\n"
            "  <time : 時間表現1>, <time : 時間表現2>, ...\n"
            "  <place : 場所表現1>, <place : 場所表現2>, ...\n"
            "- 存在しない場合は必ず「無し」を明示してください。\n"
            "  例: 時間表現が無い場合：<time : 無し>\n"
            "      場所表現が2つある場合：<place : 場所1>, <place : 場所2>\n"
        )
        examples = [
            {
                "input": "東京ビッグサイトのエスカレーターにおいて、定員以上の乗客が乗り込んだため、ガクッという音とショックの後エスカレーターは停止し逆走した。",
                "output": "<time : 無し>, <place : 東京ビッグサイトのエスカレーター>"
            },
            {
                "input": "客達は、エスカレーターの乗り口付近で仰向けに折り重なるようにして倒れ、10人がエスカレーターの段差に体をぶつけ足首を切ったり、軽い打撲のけがをした。",
                "output": "<time : 無し>, <place : エスカレーターの乗り口付近>"
            },
            {
                "input": "また、エスカレーターの逆走により、極めて高い密度で皆後ろ向きで乗り口付近で折り重なるように倒れたことから、「群集雪崩」が発生したとも考えられる。",
                "output": "<time : 無し>, <place : 乗り口付近>"
            },
            {
                "input": "東京ビッグサイト4階で開催されるアニメのフィギュアの展示・即売会場に直結するエスカレーターにおいて、開場にあたり警備員1人が先頭に立ち誘導し多くの客がエスカレーターに乗り始めた。",
                "output": "<time : 無し>, <place : エスカレーター>"
            },
            {
                "input": "さらに皆後ろ向きで乗り口付近で折り重なるように倒れ人口密度は増大し、「群集雪崩」が発生したことがけが人発生の原因である。",
                "output": "<time : 無し>, <place : 乗り口付近>"
            },
            {
                "input": "このエスカレーターは、荷重制限が約7.5t、逆送防止用ブレーキ能力の限界が約9.3tであったのに対し、事故当時は約120人が乗車したことから、逆送防止用ブレーキ能力の限界荷重をもオーバーし自動停止しさらにブレーキも効かず逆走・降下した。",
                "output": "<time : 事故当時>, <place : 無し>"
            },
            {
                "input": "特に時間や場所が明示されていない文です。",
                "output": "<time : 無し>, <place : 無し>"
            }
        ]
        # few-shot을 위한 messages 구성
        messages = [
            {"role": "system", "content": "You are an assistant that extracts time and place expressions from a sentence."},
            {"role": "user", "content": prompt},
        ]

        # 예시 제공
        for example in examples:
            messages.append({"role": "user", "content": f"文: {example['input']}"})
            messages.append({"role": "assistant", "content": example['output']})

        # 최종적으로 실제 문장에 대한 요청
        messages.append({"role": "user", "content": f"文: {sentence}"})

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.2
        )

        content = response.choices[0].message.content.strip()

        time_and_place = {
            "time": [],
            "place": []
        }

        time_pattern = re.findall(r"<time\s*:\s*(.*?)>", content)
        place_pattern = re.findall(r"<place\s*:\s*(.*?)>", content)
        
        # 시간 처리
        if time_pattern:
            has_none_time = any(t.strip() == "無し" for t in time_pattern)
            if has_none_time:
                time_and_place["time"] = []
            else:
                for t in time_pattern:
                    parts = [x.strip() for x in t.split(",")]
                    for p in parts:
                        if p and p not in time_and_place["time"]:
                            time_and_place["time"].append(p)
        else:
            time_and_place["time"] = []

        # 장소 처리
        if place_pattern:
            has_none_place = any(p.strip() == "無し" for p in place_pattern)
            if has_none_place:
                time_and_place["place"] = []
            else:
                for pl in place_pattern:
                    parts = [x.strip() for x in pl.split(",")]
                    for p in parts:
                        if p and p not in time_and_place["place"]:
                            expanded = expand_place_expression(sentence, p)
                            time_and_place["place"].append(expanded)
        else:
            time_and_place["place"] = []

        return time_and_place

    except Exception as e:
        print(f"Error extracting time and place: {e}")
        return {"time": [], "place": []}

def expand_place_expression(sentence: str, place: str) -> str:
    """
    장소 표현을 기준으로 문장에서 「の」로 연결된 명사구를 확장.
    """
    if place in sentence:
        pattern = re.compile(rf"(?:[^。、]+の)*{re.escape(place)}(?:の[^。、]+)*")
        match = pattern.search(sentence)
        if match:
            return match.group(0).strip()
    return place

def normalize_text(text: str) -> str:
    """
    문자열을 정규화하여 전각/반각 문자와 공백을 통일.
    """
    return unicodedata.normalize('NFKC', text).replace(" ", "").strip()

def remove_expressions(sentence: str, expressions: list) -> str:
    """
    문장에서 주어진 표현들과 뒤에 오는 접속사 또는 콤마를 포함하여 제거.
    """
    normalized_sentence = normalize_text(sentence)
    normalized_expressions = [normalize_text(expr) for expr in expressions]

    for expression in normalized_expressions:
        pattern = re.compile(rf"{re.escape(expression)}(?:[、,]?\s*[でに]*)?")
        normalized_sentence = pattern.sub("", normalized_sentence)
    return normalized_sentence.strip()
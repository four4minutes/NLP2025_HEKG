from openai import OpenAI
import unicodedata
import re

client = OpenAI()

def extract_time_and_place(sentence: str) -> dict:
    """
    문장에서 시간 표현과 장소 표현을 추출하는 함수.
    """
    try:
        # OpenAI API 호출
        prompt = (
            "以下の文から時間表現と場所表現を抽出してください。\n"
            "条件:\n"
            "- 時間表現は年月日、曜日、午前午後、または季節を含む『名詞句』のみ抽出してください。\n"
            "- 場所表現は地名、施設名、または特定の場所を表す『名詞句』のみ抽出してください。\n"
            "- 結果は以下の形式で出力してください：\n"
            "<time : 時間表現>, <place : 場所表現>\n"
            "文: " + sentence
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that extracts time and place expressions from a sentence."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        # 응답에서 시간 및 장소 표현 추출
        content = response.choices[0].message.content.strip()

        # 시간 및 장소 표현 기본 구조
        time_and_place = {
            "time": [],
            "place": []
        }
        
        if "<time :" in content:
            time_section = content.split("<time :")[1].split(">")[0].strip()
            if time_section:
                time_and_place["time"] = [time_section]
        if "<place :" in content:
            place_section = content.split("<place :")[1].split(">")[0].strip()
            if place_section:
                expanded_place = expand_place_expression(sentence, place_section)
                time_and_place["place"] = [expanded_place]
        
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
    
    Args:
        sentence (str): 원본 문장.
        expressions (list): 제거할 표현 리스트.
    
    Returns:
        str: 표현이 제거된 문장.
    """

    # 문장 정규화
    normalized_sentence = normalize_text(sentence)
    normalized_expressions = [normalize_text(expr) for expr in expressions]

    for expression in normalized_expressions:
        # 정규식: 표현 + 뒤따르는 조사 또는 구두점까지 매칭
        pattern = re.compile(rf"{re.escape(expression)}(?:[、,]?\s*[でに]*)?")
        # 표현 제거
        normalized_sentence = pattern.sub("", normalized_sentence)
    return normalized_sentence.strip()
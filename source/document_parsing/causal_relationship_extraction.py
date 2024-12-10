from openai import OpenAI

# OpenAI 클라이언트 초기화
client = OpenAI()

# 디버깅 모드 플래그
DEBUG_MODE = True

# 手がかり表現 리스트
CAUSAL_CUES = [
    "を背景に", "を受け", "を受けて", "を受けております", "ため", "ためで", "ため」", "ためであります。",
    "に伴う", "に伴い", "に伴いで", "から", "により", "によって", "により", "による。", "によります。",
    "によっております。", "によっています。", "が響き", "が響いた。", "が影響した。", "が響く",
    "が響いている", "が響いている。", "を反映して", "を反映し", "このため", "そのため",
    "その結果", "この結果", "をきっかけに", "に支えられて", "で"
]

# "から"와 "で"는 보수적으로 처리
SENSITIVE_CUES = ["から", "で"]

def find_causal_cues(sentence: str) -> list:
    """
    문장에서 手がかり表現을 찾아 리스트로 반환하는 함수.
    """
    return [cue for cue in CAUSAL_CUES if cue in sentence]

def extract_causal_expressions(sentence: str, detected_cues: list) -> list:
    """
    문장에서 원인사상과 결과사상을 추출하며, 手がかり表現과 직접적으로 연결된 경우만 반환.
    """
    try:
        prompt = (
            "以下の文から因果関係を抽出してください。\n"
            "条件:\n"
            "- 原因事象と結果事象を分けて抽出してください。\n"
            "- 手がかり表現と直接結びついた原因事象と結果事象のみ抽出してください。\n"
            "- 'から' や 'で' に基づく因果関係は慎重に扱ってください。\n"
            "- 複数の因果関係がある場合、それぞれ個別に抽出してください。\n"
            "文: " + sentence
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that extracts causal relationships from a sentence."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        if DEBUG_MODE:
            print("DEBUG: OpenAI API 원본 응답")
            print(response.choices[0].message.content.strip())

        content = response.choices[0].message.content.strip()
        causal_relationships = []

        # 인과관계 개별 추출
        for line in content.split("\n"):
            if "<原因:" in line and "<結果:" in line:
                cause = line.split("<原因:")[1].split(">")[0].strip()
                effect = line.split("<結果:")[1].split(">")[0].strip()

                # 手がかり表現과 연결 여부 확인
                for cue in detected_cues:
                    if cue in SENSITIVE_CUES:  # 보수적 검토
                        if cue + cause in sentence or cause + cue in sentence:
                            causal_relationships.append({"cue": cue, "cause": cause, "effect": effect})
                    elif cue + cause in sentence or cause + cue in sentence or cue + effect in sentence or effect + cue in sentence:
                        causal_relationships.append({"cue": cue, "cause": cause, "effect": effect})

        return causal_relationships

    except Exception as e:
        print(f"Error extracting causal expressions: {e}")
        return []

def process_sentence(sentence: str) -> dict:
    """
    문장을 처리하여 인과관계를 추출.
    """
    detected_cues = find_causal_cues(sentence)
    causal_relationships = extract_causal_expressions(sentence, detected_cues)

    return {
        "causal_cue_present": bool(detected_cues),
        "detected_causal_cues": detected_cues,
        "causal_relationships": causal_relationships
    }

#실행확인
#f __name__ == "__main__":
#    example_sentence = "この結果、彼の行動が影響したため、プロジェクトが遅延しました。"
#    result = process_sentence(example_sentence)
#    print(result)
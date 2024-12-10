import re

# 격 조사 매핑
CASE_MARKERS = {
    "ヲ格": "を",
    "ガ格": "が",
    "ニ格": "に",
    "デ格": "で",
    "カラ格": "から",
    "ト格": "と",
    "ヨリ格": "より",
    "ヘ格": "へ",
    "マデ格": "まで"
}

def normalize_text(text: str) -> str:
    """
    텍스트를 정규화하여 공백 제거 및 괄호 통일.
    """
    text = text.strip()
    text = text.replace("（", "(").replace("）", ")")
    text = text.replace("「", '"').replace("」", '"')
    return text

def extract_expressions_from_structure(sentence: str, predicate_argument_structures: list) -> tuple:
    expressions_with_case = []
    expressions_without_case = []

    splitted_structures = []
    for structure in predicate_argument_structures:
        structure = normalize_text(structure)
        splitted_structures.extend([s.strip() for s in structure.split(",") if s.strip()])

    for structure in splitted_structures:
        structure = normalize_text(structure)
        matches = re.findall(r"^(.*)\((述語|修飾|[^()]+格)\)$", structure)

        for noun_or_modifier, case in matches:
            normalized_expression = normalize_text(noun_or_modifier)
            # CASE_MARKERS 대응 가능할 때만 조사 변환
            if case in CASE_MARKERS:
                expression_with_case = f"{normalized_expression}{CASE_MARKERS[case]}"
                expressions_with_case.append(expression_with_case)

            expressions_without_case.append(normalized_expression)

    return expressions_with_case, expressions_without_case

def remove_expressions(sentence: str, expressions: list) -> str:
    """
    문장에서 제거할 표현 리스트를 사용해 텍스트를 정제.
    """
    modified_sentence = normalize_text(sentence)
    for expression in expressions:
        normalized_expression = normalize_text(expression)
        pattern = re.compile(rf"{re.escape(normalized_expression)}")
        modified_sentence = pattern.sub("", modified_sentence)

    return modified_sentence.strip()

def process_sentence_with_residue_removal(sentence: str, predicate_argument_structures: list) -> str:
    """
    문장에서 조사 변환 리스트와 명사 리스트를 순차적으로 사용하여 문장을 정제.
    """
    normalized_sentence = normalize_text(sentence)

    # 두 종류의 표현 리스트 생성
    expressions_with_case, expressions_without_case = extract_expressions_from_structure(normalized_sentence, predicate_argument_structures)

    # 조사 변환 리스트로 제거
    sentence_after_case_removal = remove_expressions(normalized_sentence, expressions_with_case)

    # 명사구 리스트로 제거
    final_sentence = remove_expressions(sentence_after_case_removal, expressions_without_case)

    return final_sentence
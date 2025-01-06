import re

# 격 조사 매핑 (정의된 것만)
CASE_MARKERS = {
    "ガ格": "が",
    "ヲ格": "を",
    "ニ格": "に",
    "デ格": "で",
    "カラ格": "から",
    "ト格": "と",
    "ヨリ格": "より",
    "ヘ格": "へ",
    "マデ格": "まで",
    "トシテ格": "として",
    "ニヨル格": "による",
    "ニオケル格": "における"
}

def normalize_text(text: str) -> str:
    text = text.strip()
    text = text.replace("（", "(").replace("）", ")")
    text = text.replace("「", '"').replace("」", '"')
    return text

def extract_expressions_from_structure(
    sentence: str, 
    predicate_argument_structures: list
) -> tuple:
    """
    (수정판)
    1) 항상 격요소를 다음 순서로 정렬:
       - ガ格(=0) -> 기타格(=1) -> 修飾(=2) -> 述語(=3) -> 그 외(=4)
    2) CASE_MARKERS에 없는 격요소는 콘솔 메시지 출력 후,
       '格'을 제거한 문자열(카타카나 등)으로 붙인다.
    3) expressions_with_case / expressions_without_case 반환
    """

    expressions_with_case = []
    expressions_without_case = []

    splitted_structures = []
    for structure in predicate_argument_structures:
        structure = normalize_text(structure)
        # 콤마(,) 기준으로 분할
        splitted_structures.extend([s.strip() for s in structure.split(",") if s.strip()])

    # 임시 저장: (expr_with_case, expr_no_case, case_type)
    tmp_list = []

    for structure in splitted_structures:
        structure = normalize_text(structure)
        # 예: "車両(ガ格)" → noun_or_modifier="車両", case="ガ格"
        matches = re.findall(r"^(.*)\((述語|修飾|[^()]+格)\)$", structure)
        for noun_or_modifier, case_type in matches:
            normalized_expression = normalize_text(noun_or_modifier)

            if case_type.endswith("格"):
                if case_type in CASE_MARKERS:
                    # 정의된 격 조사
                    expression_with_case = f"{normalized_expression}{CASE_MARKERS[case_type]}"
                    tmp_list.append((expression_with_case, normalized_expression, case_type))
                else:
                    # 정의되지 않은 격 조사
                    # 콘솔 출력
                    print(f"정의되지 않은 격요소 출현: {case_type}")
                    # "カラ格" → "カラ"
                    unknown_marker = re.sub(r'格$', '', case_type)
                    expression_with_case = f"{normalized_expression}{unknown_marker}"
                    tmp_list.append((expression_with_case, normalized_expression, case_type))

            elif case_type in ["述語", "修飾"]:
                # 격 조사 아닌 경우 (述語, 修飾)
                tmp_list.append((normalized_expression, normalized_expression, case_type))
            else:
                # 혹시 모르는 케이스
                print(f"정의되지 않은 요소 출현: {case_type}") 
                tmp_list.append((normalized_expression, normalized_expression, case_type))

    # 이제 정렬 기준 지정
    def sort_key(item):
        # item: (expr_with_case, expr_no_case, case_type)
        case_type = item[2]
        if case_type == "ガ格":
            return 0
        elif case_type.endswith("格") and case_type != "ガ格":
            return 1
        elif case_type == "修飾":
            return 2
        elif case_type == "述語":
            return 3
        else:
            return 4

    tmp_sorted = sorted(tmp_list, key=sort_key)

    # sorted된 tmp_list를 expressions_with_case / without_case 에 추가
    for expr_with_case, expr_no_case, case_type in tmp_sorted:
        expressions_with_case.append(expr_with_case)
        expressions_without_case.append(expr_no_case)

    return expressions_with_case, expressions_without_case

def remove_expressions(sentence: str, expressions: list) -> str:
    modified_sentence = normalize_text(sentence)
    for expression in expressions:
        normalized_expression = normalize_text(expression)
        pattern = re.compile(rf"{re.escape(normalized_expression)}")
        modified_sentence = pattern.sub("", modified_sentence)
    return modified_sentence.strip()

def process_sentence_with_residue_removal(sentence: str, predicate_argument_structures: list) -> str:
    normalized_sentence = normalize_text(sentence)

    # 수정된 extract_expressions_from_structure
    expressions_with_case, expressions_without_case = extract_expressions_from_structure(
        normalized_sentence, predicate_argument_structures
    )

    sentence_after_case_removal = remove_expressions(normalized_sentence, expressions_with_case)
    final_sentence = remove_expressions(sentence_after_case_removal, expressions_without_case)

    return final_sentence

def convert_predicate_to_text(predicate_node: dict) -> str:
    """
    Predicate Structure 노드를 받아, 
    (agent_argument, argument[], modifier, predicate) 순서로 우선 문자열로 합친 뒤,
    extract_expressions_from_structure를 통해
    'ガ格 -> 그 외格 -> 修飾 -> 述語' 순서로 정렬·조사 변환한 최종 문자열을 만든다.

    예) node:
      {
        "index": 18,
        "agent_argument": "車輪を支える軸のねじ部(ガ格)",
        "predicate": "切断した(述語)",
        "argument": ["疲労破壊(デ格)"],
        "modifier": ""
      }
    -> "車輪を支える軸のねじ部(ガ格), 疲労破壊(デ格), 切断した(述語)"
    -> extract_expressions_from_structure -> "車輪を支える軸のねじ部が 疲労破壊で 切断した"
    """
    parts = []

    # (A) agent_argument
    if predicate_node.get("agent_argument"):
        parts.append(predicate_node["agent_argument"])

    # (B) argument[]
    if predicate_node.get("argument"):
        for arg in predicate_node["argument"]:
            parts.append(arg)

    # (C) modifier
    if predicate_node.get("modifier"):
        parts.append(predicate_node["modifier"])

    # (D) predicate
    if predicate_node.get("predicate"):
        parts.append(predicate_node["predicate"])

    # 콤마로 합침
    joined_text = ", ".join(p for p in parts if p)

    # extract_expressions_from_structure를 호출
    with_case, _ = extract_expressions_from_structure(joined_text, [joined_text])
    final_str = "".join(with_case)
    return final_str

def is_heading_start(text: str) -> bool:
    """
    '１．' '1.' '2.' 등등, 혹은 '注' 등으로 시작하거나,
    [・（）注]+ 등이 전부인 경우를 판단하는 함수.
    """
    text = normalize_text(text)
    text = re.sub(r'[０-９]', lambda x: chr(ord(x.group(0)) - 0xFEE0), text)

    # 기존 json_processor.py의 패턴
    # ^(\d+\.|[・（）注]+)   # 시작 부분
    pattern = r'^(\d+\.|[・（）注]+)$'
    # 간단 판별
    return bool(re.match(pattern, text.strip()))

def split_heading_and_rest(value: str):
    """
    value가 heading에 해당하면, heading prefix와 나머지(rest)를 분리해서 반환.
    """
    item_normalized = re.sub(r'[０-９]', lambda x: chr(ord(x.group(0)) - 0xFEE0), value)
    pattern = r'^(\d+\.|[・（）注]+)\s?(.*)$'
    match = re.match(pattern, item_normalized)
    if match:
        heading_prefix = match.group(1).strip()
        rest = match.group(2).strip()
        return heading_prefix, rest
    else:
        return None, None

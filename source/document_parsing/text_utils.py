#text_utils.py

import re

# 格
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
    "ニヨリ格": "により",
    "ニヨッテ格": "によって",
    "ニオケル格": "における",
    "ニタイスル格": "に対する",
    "ノ格":"の"
}

# 不用語
STOP_WORDS = {"が", "で", "した", "に", "する", "を", "から", "の", "へ", "て", "と", "など", "による", "、", "し", "な", '"'}

def normalize_text(text: str) -> str:
    '''
    テキストを正規化して全角/半角や記号を整える関数。
    '''
    text = text.strip()
    text = text.replace("（", "(").replace("）", ")")
    text = text.replace("「", '"').replace("」", '"')
    return text

def extract_expressions_from_structure(sentence: str, predicate_argument_structures: list) -> tuple:
    '''
    述語項構造（カンマ区切り）から格要素や修飾などを抽出して、
    “格付き”リストと“格なし”リストに分解して返す。
    '''
    expressions_with_case = []
    expressions_without_case = []

    splitted_structures = []
    for structure in predicate_argument_structures:
        structure = normalize_text(structure)
        splitted_structures.extend([s.strip() for s in structure.split(",") if s.strip()])

    tmp_list = []
    for structure in splitted_structures:
        structure = normalize_text(structure)
        matches = re.findall(r"^(.*)\((.*?)\)$", structure)
        for noun_or_modifier, case_type in matches:
            normalized_expression = normalize_text(noun_or_modifier)
            case_type = case_type.strip()

            if case_type == "外の関係":
                tmp_list.append((normalized_expression, normalized_expression, case_type))
            elif case_type.endswith("格"):
                if case_type in CASE_MARKERS:
                    expression_with_case = f"{normalized_expression}{CASE_MARKERS[case_type]}"
                else:
                    print(f"Undefined case marker found: {case_type}")
                    unknown_marker = re.sub(r'格$', '', case_type)
                    expression_with_case = f"{normalized_expression}{unknown_marker}"
                tmp_list.append((expression_with_case, normalized_expression, case_type))
            elif case_type in ["述語", "修飾"]:
                tmp_list.append((normalized_expression, normalized_expression, case_type))
            else:
                print(f"Undefined element found: {case_type}")
                tmp_list.append((normalized_expression, normalized_expression, case_type))

    def sort_key(item):
        # item: (expr_with_case, expr_no_case, case_type)
        case_type = item[2]
        if case_type == "ガ格":
            return 0
        elif case_type.endswith("格") and case_type != "ガ格" and case_type != "外の関係":
            return 1
        elif case_type == "修飾":
            return 2
        elif case_type == "述語":
            return 3
        else:  
            return 4

    tmp_sorted = sorted(tmp_list, key=sort_key)

    for expr_with_case, expr_no_case, case_type in tmp_sorted:
        expressions_with_case.append(expr_with_case)
        expressions_without_case.append(expr_no_case)

    return expressions_with_case, expressions_without_case

def remove_expressions(sentence: str, expressions: list) -> str:
    '''
    渡された表現（expressions）を文から順次除去する。
    - sentence : 元の文
    - expressions : 除去対象文字列のリスト
    '''
    modified_sentence = normalize_text(sentence)
    for expression in expressions:
        normalized_expression = normalize_text(expression)
        pattern = re.compile(rf"{re.escape(normalized_expression)}")
        modified_sentence = pattern.sub("", modified_sentence)
    return modified_sentence.strip()

def process_sentence_with_residue_removal(sentence: str, predicate_argument_structures: list) -> str:
    '''
    述語項構造から抽出した表現を文から取り除き、残差を確認する処理。
    '''
    normalized_sentence = normalize_text(sentence)

    expressions_with_case, expressions_without_case = extract_expressions_from_structure(normalized_sentence, predicate_argument_structures)

    sentence_after_case_removal = remove_expressions(normalized_sentence, expressions_with_case)
    final_sentence = remove_expressions(sentence_after_case_removal, expressions_without_case)

    return final_sentence

def convert_predicate_to_text(predicate_node: dict) -> str:
    '''
    述語ノードの情報からガ格・その他格・修飾・述語を一つにつなげた文字列を生成し、
    格要素を正規の形に再フォーマットした結果を返す。
    '''
    parts = []

    if predicate_node.get("agent_argument"):
        parts.append(predicate_node["agent_argument"])

    if predicate_node.get("argument"):
        for arg in predicate_node["argument"]:
            parts.append(arg)

    if predicate_node.get("modifier"):
        parts.append(predicate_node["modifier"])

    if predicate_node.get("predicate"):
        parts.append(predicate_node["predicate"])

    joined_text = ", ".join(p for p in parts if p)

    with_case, _ = extract_expressions_from_structure(joined_text, [joined_text])
    final_str = "".join(with_case)
    return final_str

def is_heading_start(text: str) -> bool:
    '''
    見出しのような短いパターンかどうかを判定する。
    例えば "1." "2." "注" "・" のみ などをチェック。
    '''
    text = normalize_text(text)
    text = re.sub(r'[０-９]', lambda x: chr(ord(x.group(0)) - 0xFEE0), text)
    pattern = r'^(\d+\.|[・（）注]+)$'
    return bool(re.match(pattern, text.strip()))

def split_heading_and_rest(value: str):
    '''
    見出し部分と残りの部分に分割する関数。該当しなければ (None, None) を返す。
    '''
    item_normalized = re.sub(r'[０-９]', lambda x: chr(ord(x.group(0)) - 0xFEE0), value)
    pattern = r'^(\d+\.|[・（）注]+)\s?(.*)$'
    match = re.match(pattern, item_normalized)
    if match:
        heading_prefix = match.group(1).strip()
        rest = match.group(2).strip()
        return heading_prefix, rest
    else:
        return None, None
    
def fix_predicate_structure_text(structure: str) -> str:
    '''
    述語項構造内の末尾の調整などを行い、表記ゆれを修正する補助的な関数。
    '''
    segments = [seg.strip() for seg in structure.split(",")]
    fixed_segments = []
    for seg in segments:
        m = re.match(r"^(.*?)(\S*)\(([^)]+)\)$", seg)
        if m:
            base_text = m.group(1)
            trailing = m.group(2)
            case_type = m.group(3).strip()

            if case_type in CASE_MARKERS:
                if trailing == CASE_MARKERS[case_type]:
                    fixed_seg = f"{base_text}({case_type})"
                else:
                    fixed_seg = seg
            else:
                fixed_seg = seg
            fixed_segments.append(fixed_seg)
        else:
            fixed_segments.append(seg)

    return ", ".join(fixed_segments)
# text_utils.py

# 격조사 매핑
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
    "ニタイスル": "に対する"
}

def parse_case_element(elem: str) -> str:
    """
    예) "車両(ト格)" -> "車両と"
        "レール(カラ格)" -> "レールから"
        "レール(ホニャ格)" (매핑 없는 경우) -> "レールホニャ"
    - 괄호 안에 있는 'XX格' 부분을 추출하여, CASE_MARKERS 에 있으면 치환
      없으면 '格'만 제거한 채로 사용.
    """
    # 혹시라도 괄호가 없으면 그대로 리턴
    if '(' not in elem or ')' not in elem:
        return elem

    # "車両(ト格)" -> 앞부분 "車両", 뒷부분 "ト格"
    head, tail = elem.split('(')
    tail = tail.replace(')', '')  # tail = "ト格"
    head = head.strip()
    tail = tail.strip()

    # "ト格"에서 "格"을 떼고 -> "ト"
    # CASE_MARKERS 에 "ト格" 키가 있으면 매핑값 사용. 없으면 tail에서 "格"만 제거
    if tail in CASE_MARKERS:
        marker = CASE_MARKERS[tail]
    else:
        # tail = "ト格" -> "ト"
        # tail = "ホニャ格" -> "ホニャ"
        marker = tail.replace('格', '')

    # 변환 결과는 head + marker
    return head + marker


def predicate_to_text(predicate_node: dict) -> str:
    """
    predicate_node 예시:
    {
      'index': '15',
      'level': 0,
      'agent': 'ジェットコースターの車輪(ガ格)',
      'predicate': '脱輪し(述語)',
      'argument': ['レール(カラ格)'],
      'modifier': ''
    }
    변환 순서:
      1) agent(ガ格) -> "ジェットコースターの車輪が"
      2) argument들 (가급적 입력 순서대로) -> "レールから"
      3) predicate -> "脱輪し"
    => "ジェットコースターの車輪がレールから脱輪し"
    """
    agent_str = ""
    if predicate_node['agent']:
        # agent 부분 변환 (ex. "ジェットコースターの車輪(ガ格)" -> "ジェットコースターの車輪が")
        agent_str = parse_case_element(predicate_node['agent'])

    # argument 리스트 처리
    # (가장 기본적으로, agent의 'ガ格' 이외 격요소가 argument 쪽에 있을 수도 있으니 순서대로)
    arg_str_list = []
    for arg in predicate_node['argument']:
        arg_str_list.append(parse_case_element(arg))

    # predicate 처리
    # "脱輪し(述語)" -> "脱輪し" 로 (괄호 속 '述語' 제거)
    pred = predicate_node['predicate']
    if '(' in pred and ')' in pred:
        # "脱輪し(述語)" -> "脱輪し"
        pred_head, _ = pred.split('(')
        pred = pred_head.strip()

    # 합치기
    # 순서: agent_str -> arg_str_list -> pred
    # 예) "ジェットコースターの車輪が" + "レールから" + "脱輪し"
    # 중간에 임의로 띄어쓰기를 넣을지 여부는 원하는 출력 형식에 따라 결정
    # 예시처럼 붙여 쓰도록 하겠습니다.
    final_str = agent_str
    for a in arg_str_list:
        final_str += a
    final_str += pred

    return final_str

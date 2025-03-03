# causal_relationship_extraction.py
# 因果関係を抽出し、エッジへ追加するモジュール

import re
from openai import OpenAI
from source.document_parsing.logger import log_token_usage
from source.document_parsing.edge_maker import append_edge_info

client = OpenAI()

def extract_causal_relationship(sentence, node_list,doc_created_indexes):
    '''
    文とノード情報をもとに、因果関係があれば抽出して "explain_cause" や "explain_reason" エッジを生成する。
    - sentence : 原文
    - node_list : [{"index":..., "text":...}, ...]
    - doc_created_indexes : 生成したエッジのインデックスを追跡するセット
    '''
    
    try:
        # (1) GPTに与えるプロンプト
        prompt = (
            '[タスク目的]\n'
            '入力文に対して、文から抽出されたノード間に存在する因果関係を抽出する。\n'
            '[背景説明]\n'
            '(1) 因果関係\n'
            '事象が発生したとき、原因となる事象を「原因事象」、結果として生じる事象を「結果事象」と呼ぶ。これらの関係を「因果関係」という。たとえば「電車の遅延により、遅刻してしまった」という文では、原因事象は「電車の遅延」、結果事象は「遅刻」であり、両者は因果関係にある。\n'
            '(2) 手がかり表現\n'
            '因果関係が含まれているかを判断する際の目印となる表現を指す。原因事象と結果事象をつなぐ表現例として、「～を理由に」「～ため」などがある。ただし、手がかり表現が出現しても必ず因果関係を示すわけではない点に注意する。同じ表現でも文脈によっては単に時間を示すなど、別の意味になる場合もある。\n'
            '(3) ノード\n'
            '他のタスクで文を区切り、ノードとしてまとめた要素を指す。本タスクでは、与えられたノード同士の間に因果関係があるかどうかを抽出することが目的である。\n'
            '(4) cause と reason\n'
            '文に現れる事象の因果関係には、大きく分けて2種類があるとする。結果事象に対する直接的な原因事象を「cause」と呼び、結果事象を引き起こした原因の原因や説明表現を「reason」と呼ぶ。\n'
            '- 例1：「電車の遅延による遅刻」という文では、結果事象「遅刻」に対する直接的な原因事象「電車の遅延」が「cause」にあたる。\n'
            '- 例2：「電車の遅延の原因は人身事故である」という文では、結果事象「電車の遅延」に対する原因事象「人身事故」が「reason」となる。\n'
            'ただし「cause」と「reason」は類似の意味を持ち、はっきり区別しにくい場合もある。そのため、どちらに分類するか判断が難しいときは適宜割り振って構わない。\n'
            '[手がかり表現一覧]\n'
            '因果関係抽出時に役立つ表現の例を以下に示す。抽出の際に参考とすること。\n'
            '"を背景に", "を受け", "を受けて", "を受けております", "ため", "ためで", "ため」", "ためであります。", '
            '"に伴う", "に伴い", "に伴いで", "から", "により", "によって", "により", "による。", "によります。", '
            '"によっております。", "によっています。", "が響き", "が響いた。", "が影響した。", "が響く", '
            '"が響いている", "が響いている。", "を反映して", "を反映し", "このため", "そのため", '
            '"その結果", "この結果", "をきっかけに", "に支えられて", "で", "原因", "ので"\n'
            '[入力に関する説明]\n'
            '- 入力文: 分析対象となる文\n'
            '- ノード: {"index": ノードのインデックス番号, "text": ノードのテキスト情報}\n'
            '[出力形式]\n'
            '以下の形式で因果関係を出力する。\n'
            '- LABEL は「cause」または「reason」を出力する。\n'
            '- 手がかり表現には、判断根拠となった表現を入力する(該当しない場合は "" のように空文字列)。\n'
            '- 複数ある場合は番号を振って列挙すること。\n'
            '[CAUSAL_RELATION]\n'
            '(1) (原因事象ノードID, 結果事象ノードID, \'LABEL\', \'手がかり表現\')\n'
            '(2) (原因事象ノードID, 結果事象ノードID, \'LABEL\', \'手がかり表現\')\n'
            '...\n'
            '因果関係が無い場合は「無し」と記載する。\n'
            '[CAUSAL_RELATION]\n'
            '無し\n'
            '[指示]\n'
            '入力文およびノード情報を参照し、因果関係があれば抽出する。その際、上記の手がかり表現一覧を参考とするが、文脈も十分に考慮したうえで関係の有無を正確に判断すること。\n'
        )
        examples = [
            {
            "input": {
                "sentence": "東京ビッグサイトのエスカレーターにおいて、定員以上の乗客が乗り込んだため、ガクッという音とショックの後エスカレーターは停止し逆走した。",
                "nodes": [
                { "index": 1, "text": "定員以上の乗客が乗り込んだ" },
                { "index": 2, "text": "エスカレーターが停止し" },
                { "index": 3, "text": "エスカレーターが逆走した" },
                { "index": 4, "text": "ガクッという音" },
                { "index": 5, "text": "ショック" }
                ]
            },
            "output": "[CAUSAL_RELATION]\n(1) (1, 2, 'cause', 'ため')\n(2) (1, 3, 'cause', 'ため')"
            },
            {
            "input": {
                "sentence": "エスカレーターは、荷重オーバーで自動停止しさらにブレーキも効かず逆走・降下した。",
                "nodes": [
                { "index": 6, "text": "エスカレーターが自動停止し" },
                { "index": 7, "text": "ブレーキが効かず" },
                { "index": 8, "text": "エスカレーターが逆走・降下した" },
                { "index": 9, "text": "荷重オーバー" }
                ]
            },
            "output": "[CAUSAL_RELATION]\n(1) (9, 6, 'cause', 'で')"
            },
            {
            "input": {
                "sentence": "ただ、荷重オーバーによる停止を超えて、ブレーキ能力に限界があり逆走が発生したので、エスカレーターの機構にも問題がある可能性も考えられる。",
                "nodes": [
                { "index": 10, "text": "停止" },
                { "index": 11, "text": "逆走が発生した" },
                { "index": 12, "text": "荷重オーバー" },
                { "index": 13, "text": "ブレーキ能力の限界" },
                { "index": 14, "text": "エスカレーターの機構の問題" }
                ]
            },
            "output": "[CAUSAL_RELATION]\n(1) (12, 10, 'cause', 'による')\n(2) (13, 11, 'reason', '')\n(3) (14, 11, 'reason', 'ので')"
            },
            {
            "input": {
                "sentence": "また、エスカレーターの逆走により、極めて高い密度で皆後ろ向きで乗り口付近で折り重なるように倒れたことから、「群集雪崩」が発生したとも考えられる。",
                "nodes": [
                { "index": 15, "text": "エスカレーターが逆走" },
                { "index": 16, "text": "皆が極めて高い密度で後ろ向きで折り重なる" },
                { "index": 17, "text": "皆が倒れた" },
                { "index": 18, "text": "群集雪崩が発生した" }
                ]
            },
            "output": "[CAUSAL_RELATION]\n(1) (15, 17, 'cause', 'により')\n(2) (17, 18, 'cause', 'から')"
            },
            {
            "input": {
                "sentence": "客達は先を争うようにエスカレーターに乗り込んだが、先頭は警備員が規制していたため、エスカレーターの1段に3～4人が乗るほどのすし詰め状態となった。",
                "nodes": [
                { "index": 19, "text": "客達が先を争う" },
                { "index": 20, "text": "客達がエスカレーターに乗り込んだ" },
                { "index": 21, "text": "警備員が先頭を規制していた" },
                { "index": 22, "text": "3～4人がエスカレーターの1段を乗る" },
                { "index": 23, "text": "すし詰め状態となった" }
                ]
            },
            "output": "[CAUSAL_RELATION]\n(1) (21, 23, 'cause', 'ため')"
            },
            {
            "input": {
                "sentence": "このエスカレーターは、荷重制限が約7.5t、逆送防止用ブレーキ能力の限界が約9.3tであったのに対し、事故当時は約120人が乗車したことから、逆送防止用ブレーキ能力の限界荷重をもオーバーし自動停止しさらにブレーキも効かず逆走・降下した。",
                "nodes": [
                { "index": 24, "text": "約120人が乗車した" },
                { "index": 25, "text": "エスカレーターが自動停止し" },
                { "index": 26, "text": "ブレーキが効かず" },
                { "index": 27, "text": "エスカレーターが逆走・降下した" },
                { "index": 28, "text": "荷重制限が約7.5t" },
                { "index": 29, "text": "逆送防止用ブレーキ能力の限界が約9.3tであった" },
                { "index": 30, "text": "逆送防止用ブレーキ能力の限界荷重をもオーバー" }
                ]
            },
            "output": "[CAUSAL_RELATION]\n(1) (24, 30, 'reason', 'から')"
            },
            {
            "input": {
                "sentence": "ただ、荷重制限とブレーキ能力の限界までには、(9.3-7.5=）1.8tの余裕があるはずなのに、停止してすぐ逆走したことから、エスカレーターの機構にも問題がある可能性もある。",
                "nodes": [
                { "index": 31, "text": "停止して" },
                { "index": 32, "text": "逆走した" },
                { "index": 33, "text": "荷重制限とブレーキ能力の限界までには、(9.3-7.5=）1.8tの余裕がある" },
                { "index": 34, "text": "エスカレーターの機構にも問題がある" }
                ]
            },
            "output": "[CAUSAL_RELATION]\n(1) (34, 32, 'reason', 'から')"
            },
            {
            "input": {
                "sentence": "さらに皆後ろ向きで乗り口付近で折り重なるように倒れ人口密度は増大し、「群集雪崩」が発生したことがけが人発生の原因である。",
                "nodes": [
                { "index": 35, "text": "皆が後ろ向きで折り重なる" },
                { "index": 36, "text": "皆が倒れ" },
                { "index": 37, "text": "群集雪崩が発生した" },
                { "index": 38, "text": "人口密度の増大" },
                { "index": 39, "text": "けが人の発生" }
                ]
            },
            "output": "[CAUSAL_RELATION]\n(1) (37, 39, 'reason', '原因')"
            },
            {
            "input": {
                "sentence": "周囲の人々の救助が功を奏したのと被害者は若者が殆どだったので、軽傷程度のけがですんだ。",
                "nodes": [
                { "index": 40, "text": "周囲の人々の救助が功を奏した結果" },
                { "index": 41, "text": "被害者は若者が大半" },
                { "index": 42, "text": "軽傷程度で収まった状態" }
                ]
            },
            "output": "[CAUSAL_RELATION]\n(1) (41, 42, 'reason', 'ので')"
            },
            {
            "input": {
                "sentence": "エスカレーターに定員があることすら知らない人が多いため、定員表示や過搭乗防止PRを徹底する必要がある。",
                "nodes": [
                { "index": 43, "text": "エスカレーターの定員" },
                { "index": 44, "text": "定員を知らない多数の人々" },
                { "index": 45, "text": "定員表示や過搭乗防止PRの徹底" }
                ]
            },
            "output": "[CAUSAL_RELATION]\n(1) (44, 45, 'reason', 'ため')"
            }
        ]

        messages = [
            {"role": "system", "content": "You are an assistant that extracts causal relationships between nodes."},
            {"role": "user", "content": prompt}
        ]
        for example in examples:
            example_sentence = example["input"]["sentence"]
            example_nodes = example["input"]["nodes"]
            example_node_str = "\n".join(
                f"{{index:{n['index']}, text:{n['text']}}}"
                for n in example_nodes
            )
            example_input_str = ( f"文:{example_sentence}\n" f"ノード:{example_node_str}\n")
            example_output_str = example["output"]
            messages.append({"role": "user", "content": example_input_str})
            messages.append({"role": "assistant", "content": example_output_str})
        node_str = "\n".join(
            f"{{index:{n['index']}, text:{n['text']}}}"
            for n in node_list
        )
        final_input_str = (
            f"文: {sentence}\n"
            f"ノード:\n{node_str}\n\n"
        )
        messages.append({"role": "user", "content": final_input_str})

        # (2) 実際にAPIを呼び出す
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.0
        )

        content = response.choices[0].message.content.strip()
        if hasattr(response, "usage") and hasattr(response.usage, "total_tokens"):
            log_token_usage(response.usage.total_tokens)

        # (3) 結果からを抽出
        lines = content.splitlines()
        in_section = False
        for line in lines:
            line = line.strip()
            if "[CAUSAL_RELATION]" in line:
                in_section = True
                continue
            if not in_section:
                continue
            if line == "無し":
                break

            # (4) 正規表現による分析
            match = re.match(r'^\(\d+\)\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*\'(cause|reason)\'\s*,\s*\'(.*?)\'\)$', line)
            if match:
                cause_idx = int(match.group(1))
                effect_idx = int(match.group(2))
                label_str = match.group(3)  
                cue_str = match.group(4)

                # (結果) --(explain_cause)--> (原因) 関係の付与
                if label_str == "cause":
                    append_edge_info("explain_cause", effect_idx, cause_idx, doc_created_indexes)
                # (結果) --(explain_reason)--> (原因) 関係の付与
                if label_str == "reason":
                    append_edge_info("explain_reason", effect_idx, cause_idx, doc_created_indexes)

    except Exception as e:
        print(f"Error extracting causal relation: {e}")
        return {content}
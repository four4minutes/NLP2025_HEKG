# similarity_calculation.py

from sentence_transformers import SentenceTransformer, util
from source.document_parsing.edge_maker import append_edge_info
from source.document_parsing.text_utils import convert_predicate_to_text, is_heading_start

model = SentenceTransformer('stsb-xlm-r-multilingual')
SIMILARITY_THRESHOLD_EQUIVALENT = 0.8  # equivalent 기준
SIMILARITY_THRESHOLD_LOG = 0.5        # 로그 참고자료표에 표시할 기준

# (A) 모든 노드 쌍의 유사도 및 유사도등록 로그를 저장
similarity_score_cache = {} 
similarity_registration_logs = []

# 부모-자식 묶음을 저장(중복 방지)
similarity_info = []

def reset_similarity_info():
    similarity_info.clear()
    similarity_score_cache.clear()
    similarity_registration_logs.clear()

def gather_all_nodes(entity_nodes, predicate_nodes):
    all_nodes = []

    for ent in entity_nodes:
        idx = ent["index"]
        text = ent["entity"].strip()
        if is_heading_start(text) and len(text) <= 2:
            continue
        all_nodes.append({"index": idx, "text": text})

    for pnode in predicate_nodes:
        idx = pnode["index"]
        text = convert_predicate_to_text(pnode).strip()
        if is_heading_start(text) and len(text) <= 2:
            continue
        all_nodes.append({"index": idx, "text": text})

    return all_nodes

def compute_all_similarities(all_nodes):
    texts = [n["text"] for n in all_nodes]
    embeddings = model.encode(texts, convert_to_tensor=True)

    n = len(all_nodes)
    for i in range(n):
        cache_list = []
        emb_i = embeddings[i]
        idx_i = all_nodes[i]["index"]
        text_i = all_nodes[i]["text"]

        for j in range(n):
            if i == j:
                continue
            emb_j = embeddings[j]
            idx_j = all_nodes[j]["index"]
            text_j = all_nodes[j]["text"]
            score_val = util.pytorch_cos_sim(emb_i, emb_j).item()

            cache_list.append((score_val, idx_j, text_j))

        # 내림차순 정렬
        cache_list.sort(key=lambda x: x[0], reverse=True)
        # cache에 저장
        similarity_score_cache[idx_i] = cache_list

def run_similarity_check(entity_nodes, predicate_nodes):
    reset_similarity_info()
    all_nodes = gather_all_nodes(entity_nodes, predicate_nodes)
    compute_all_similarities(all_nodes)

    for node_i in all_nodes:
        idx_i = node_i["index"]
        text_i = node_i["text"]

        parent_entry = None
        for pe in similarity_info:
            if pe["parent_index"] == idx_i:
                parent_entry = pe
                break
        if not parent_entry:
            parent_entry = {
                "parent_text": text_i,
                "parent_index": idx_i,
                "children": []
            }
            similarity_info.append(parent_entry)

        for (score_val, idx_j, text_j) in similarity_score_cache[idx_i]:
            if score_val < SIMILARITY_THRESHOLD_EQUIVALENT:
                break  
            already_child = any(c["index"] == idx_j for c in parent_entry["children"])
            if not already_child:
                parent_entry["children"].append({"text": text_j, "index": idx_j})
                similarity_registration_logs.append(
                    f"[유사도등록] {text_i} --(equivalent)--> {text_j} (score={score_val:.2f})"
                )

def create_equivalent_edges():
    for parent_entry in similarity_info:
        p_idx = parent_entry["parent_index"]
        for child in parent_entry["children"]:
            c_idx = child["index"]
            append_edge_info("equivalent", p_idx, c_idx)
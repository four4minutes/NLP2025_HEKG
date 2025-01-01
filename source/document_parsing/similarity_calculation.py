# similarity_calculation.py (간단 예시)

from sentence_transformers import SentenceTransformer, util
from source.document_parsing.logger import log_to_file
from source.document_parsing.edge_maker import append_edge_info
from source.document_parsing.residue_extraction import convert_predicate_to_text

model = SentenceTransformer('stsb-xlm-r-multilingual')
SIMILARITY_THRESHOLD = 0.8

# 부모-자식 묶음을 저장할 리스트/사전
similarity_info = []

def reset_similarity_info():
    similarity_info.clear()

def gather_all_nodes(entity_nodes, predicate_nodes):
    """
    entity_nodes 예: [{"index":1,"entity":"大阪府吹田市"},...]
    predicate_nodes 예: [{"index":10,"agent_argument":"車体(ガ格)",...},...]
    """
    all_nodes = []
    # Entity
    for ent in entity_nodes:
        idx = ent["index"]
        text = ent["entity"]
        all_nodes.append({"index": idx, "text": text})

    # Predicate (convert_predicate_to_text로 문자열화)
    for pnode in predicate_nodes:
        idx = pnode["index"]
        text = convert_predicate_to_text(pnode)
        all_nodes.append({"index": idx, "text": text})

    return all_nodes

def register_node(node_text: str, node_index: int):
    new_embedding = model.encode(node_text, convert_to_tensor=True)

    matched_parent = None
    best_score = -1

    for parent_entry in similarity_info:
        parent_text = parent_entry["parent_text"]
        parent_embedding = model.encode(parent_text, convert_to_tensor=True)
        score = util.pytorch_cos_sim(new_embedding, parent_embedding).item()

        if score >= SIMILARITY_THRESHOLD and score > best_score:
            best_score = score
            matched_parent = parent_entry

    if matched_parent:
        matched_parent["children"].append({
            "text": node_text,
            "index": node_index
        })
        log_to_file(f"[유사도등록] {matched_parent['parent_text']} --(equivalent)--> {node_text} (score={best_score:.2f})")
    else:
        similarity_info.append({
            "parent_text": node_text,
            "parent_index": node_index,
            "children": []
        })

def run_similarity_check(entity_nodes, predicate_nodes):
    reset_similarity_info()
    all_nodes = gather_all_nodes(entity_nodes, predicate_nodes)

    for node in all_nodes:
        register_node(node["text"], node["index"])

def create_equivalent_edges():
    for parent_entry in similarity_info:
        p_idx = parent_entry["parent_index"]
        for child in parent_entry["children"]:
            c_idx = child["index"]
            append_edge_info("equivalent", p_idx, c_idx)
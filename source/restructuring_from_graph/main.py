# main.py

import os
from result_file_parser import (
    category_structure,
    entity_structure,
    predicate_structure,
    edges,
    load_category_structure,
    load_entity_structure,
    load_predicate_structure,
    load_edges
)
from text_utils import predicate_to_text
from timeline_parser import build_timeline_groups

def main():
    base_dir = "results/archive"
    global category_structure, entity_structure, predicate_structure, edges

    # (1) CSV 로드
    category_structure   = load_category_structure(os.path.join(base_dir, "category_structure_node.csv"))
    entity_structure     = load_entity_structure(os.path.join(base_dir, "entity_structure_node.csv"))
    predicate_structure  = load_predicate_structure(os.path.join(base_dir, "predicate_structure_node.csv"))
    edges                = load_edges(os.path.join(base_dir, "edge.csv"))

    # (1) hierarchical level=0 필터
    predicate_0 = {k:v for k,v in predicate_structure.items() if v['level'] == 0}
    entity_0    = {k:v for k,v in entity_structure.items() if v['level'] == 0}

    # (2) timeline 그룹 생성
    timelines = build_timeline_groups(predicate_0, entity_0, edges)

    # (출력) 예시
    t_num = 0
    for timeline in timelines:
        t_num += 1
        print(f"[Timeline {t_num}]")
        eg_num = 0
        for eg in timeline['event_groups']:
            eg_num += 1
            print(f" (Event Group {eg_num})")
            # predicates
            preds_sorted = sorted(eg['predicates'], key=lambda x: int(x))
            for pid in preds_sorted:
                pnode = predicate_0[pid]
                ptext = predicate_to_text(pnode)
                print("   ", ptext)
            # entities
            ents_sorted = sorted(eg['entities'], key=lambda x: int(x))
            for eid in ents_sorted:
                print("   ", entity_0[eid]['entity'])
        print()

    print("[Done]")

if __name__ == "__main__":
    main()

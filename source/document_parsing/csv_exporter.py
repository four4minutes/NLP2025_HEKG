# csv_exporter.py
import csv
import os

def export_to_csv(category_list, entity_list, predicate_list, edge_list, output_dir="."):
    """
    4개의 CSV 파일을 생성한다:
      1) category_structure_node.csv
      2) entity_structure_node.csv
      3) predicate_structure_node.csv
      4) edge.csv

    output_dir 파라미터를 통해 결과 파일을 저장할 경로 지정 가능 (기본은 현재 디렉토리).
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 1) category_structure_node.csv
    # 헤더: index, hierarchical level, category type, category title
    category_csv_path = os.path.join(output_dir, "category_structure_node.csv")
    with open(category_csv_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "hierarchical level", "category type", "category title"])
        for cat in category_list:
            writer.writerow([
                cat.get("index", ""),
                cat.get("hierarchical_level", ""),
                cat.get("category_type", ""),
                cat.get("category_title", "")
            ])

    # 2) entity_structure_node.csv
    # 헤더: index, hierarchical level, entity
    entity_csv_path = os.path.join(output_dir, "entity_structure_node.csv")
    with open(entity_csv_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "hierarchical level", "entity"])
        for ent in entity_list:
            writer.writerow([
                ent.get("index", ""),
                ent.get("hierarchical_level", ""),
                ent.get("entity", "")
            ])

    # 3) predicate_structure_node.csv
    # 헤더: index, hierarchical level, agent argument, predicate, argument, modifier
    predicate_csv_path = os.path.join(output_dir, "predicate_structure_node.csv")
    with open(predicate_csv_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "hierarchical level", "agent argument", "predicate", "argument", "modifier"])
        for pred in predicate_list:
            # pred["argument"]가 배열이므로, 이를 콤마로 합친 문자열로 변환
            arg_list = pred.get("argument", [])
            argument_str = ", ".join(arg_list) if arg_list else ""

            writer.writerow([
                pred.get("index", ""),
                pred.get("hierarchical_level", ""),
                pred.get("agent_argument", ""),
                pred.get("predicate", ""),
                argument_str,
                pred.get("modifier", "")
            ])

    # 4) edge.csv
    # 헤더: index, type, from, to
    edge_csv_path = os.path.join(output_dir, "edge.csv")
    with open(edge_csv_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "type", "from", "to"])
        for e in edge_list:
            writer.writerow([
                e.get("index", ""),
                e.get("type", ""),
                e.get("from", ""),
                e.get("to", "")
            ])

    print(f"CSV files have been created in: {output_dir}")
# result_file_parser.py
import csv
from collections import defaultdict

# 전역 리스트(혹은 딕셔너리)
category_structure = []
entity_structure   = {}
predicate_structure= {}
edges             = []

# Union-Find(Disjoint Set) 보조 함수들
def find(parent, x):
    """Find with path compression."""
    if parent[x] != x:
        parent[x] = find(parent, parent[x])
    return parent[x]

def union(parent, rank, a, b):
    """Union by rank."""
    rootA = find(parent, a)
    rootB = find(parent, b)
    if rootA != rootB:
        if rank[rootA] < rank[rootB]:
            rootA, rootB = rootB, rootA
        parent[rootB] = rootA
        if rank[rootA] == rank[rootB]:
            rank[rootA] += 1

# CSV 로더 함수들
def load_category_structure(filepath):
    """ category_structure_node.csv 파일 읽기 """
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'index': row['index'],
                'hierarchical level': row['hierarchical level'],
                'category type': row['category type'],
                'category title': row['category title']
            })
    return data


def load_entity_structure(filepath):
    """ entity_structure_node.csv 파일 읽기 """
    data = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = row['index']
            level = int(row['hierarchical level'])
            entity = row['entity']
            data[idx] = {
                'index': idx,
                'level': level,
                'entity': entity
            }
    return data


def load_predicate_structure(filepath):
    """ predicate_structure_node.csv 파일 읽기 """
    data = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = row['index']
            level = int(row['hierarchical level'])
            agent = row['agent argument'].strip()   # ガ格
            predicate = row['predicate'].strip()    # 술어
            # argument 는 콤마(,)로 구분 -> 리스트
            arg_list = [a.strip() for a in row['argument'].split(',') if a.strip()]
            modifier = row['modifier'].strip()      # 연용수식어
            data[idx] = {
                'index': idx,
                'level': level,
                'agent': agent,
                'predicate': predicate,
                'argument': arg_list,
                'modifier': modifier
            }
    return data


def load_edges(filepath):
    """ edge.csv 파일 읽기 """
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            e_index = row['index']
            e_type = row['type']
            e_from = row['from']
            e_to   = row['to']
            data.append({
                'index': e_index,
                'type': e_type,
                'from': e_from,
                'to': e_to
            })
    return data

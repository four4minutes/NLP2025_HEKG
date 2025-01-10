# timeline_builder.py

from collections import defaultdict

def build_maps(predicate_0, entity_0, edges):
    """
    predicate 간의 equivalent, next_TimeStamp 맵
    predicate->entity 관계 맵을 구성
    """
    eq_map = defaultdict(set)    # eq_map[p] = set(equivalent_predicates)
    nxt_map = defaultdict(set)   # nxt_map[p] = set(next_predicates)
    used_entity_labels = {"explain_details", "info_SpecificTime", "info_SpecificPlace"}
    entity_map = defaultdict(set)  # entity_map[p] = set(entity_nodes connected)
    
    for e in edges:
        etype = e['type']
        f = e['from']
        t = e['to']

        # equivalent
        if etype == 'equivalent':
            if f in predicate_0 and t in predicate_0:
                eq_map[f].add(t)
                eq_map[t].add(f)

        # next_TimeStamp
        elif etype == 'next_TimeStamp':
            if f in predicate_0 and t in predicate_0:
                nxt_map[f].add(t)

        # entity 관계
        elif etype in used_entity_labels:
            if f in predicate_0 and t in entity_0:
                entity_map[f].add(t)

    return eq_map, nxt_map, entity_map


def assign_equivalent(pred_id, eq_map, event_group, 
                      assigned_predicates, event_group_id):
    """
    (2-1-2) 처리:
      pred_id(미할당)를 현재 event_group에 넣고,
      그 pred_id와 equivalent인 노드를 재귀적으로 event_group에 추가.
    """
    stack = [pred_id]
    while stack:
        curr = stack.pop()
        # 이미 event_group에 들어 있으면 skip
        if curr in event_group['predicates']:
            continue

        # 만약 이미 다른 event 그룹에 속해 있으면 -> 에러 출력 후 skip
        if curr in assigned_predicates:
            # 다만, 만약 같은 group_id라면 문제없지만
            old_grp = assigned_predicates[curr]
            if old_grp != event_group_id:
                print(f"[ERROR] Predicate {curr} is already in event_group {old_grp}, "
                      f"but found via equivalent search in event_group {event_group_id}. Skipping.")
            continue

        # event group에 추가
        event_group['predicates'].add(curr)
        # 할당표 기록
        assigned_predicates[curr] = event_group_id

        # 다시 curr의 equivalent에 대해 탐색
        for eqp in eq_map[curr]:
            if eqp not in event_group['predicates']:
                stack.append(eqp)


def assign_entities(event_group, entity_map):
    """
    (2-1-3) 처리:
      event_group에 속한 모든 predicate가
      (explain_details, info_SpecificTime, info_SpecificPlace)
      관계를 맺는 entity 노드를 event_group에 추가
    """
    for p in event_group['predicates']:
        if p in entity_map:
            for e in entity_map[p]:
                event_group['entities'].add(e)


def build_event_group(start_pred, eq_map, entity_map, 
                      assigned_predicates, event_group_id):
    """
    (2-1-1), (2-1-2), (2-1-3) 순으로 
    하나의 event_group 객체를 생성 (빈 상태) 후 노드 할당
    """
    event_group = {
        'predicates': set(),
        'entities': set()
    }
    # (2-1-1) start_pred를 이 event group에 넣는다
    # (2-1-2) equivalent인 노드들도 재귀적으로 넣는다
    assign_equivalent(start_pred, eq_map, event_group, 
                      assigned_predicates, event_group_id)
    # (2-1-3) entity 할당
    assign_entities(event_group, entity_map)

    return event_group


def explore_event_groups(current_event_group, eq_map, nxt_map, entity_map, 
                         assigned_predicates, predicate_list, timeline, 
                         timeline_id):
    """
    (2-1-4) 처리: 
      current_event_group에 속한 predicate 노드들에서 next_TimeStamp로 이어지는 노드들을 찾아 
      각각 새로운 event group을 DFS로 생성한다.
    """
    # 이 event group에 속한 predicate들을 모아두고,
    # 각 predicate p 에 대해 nxt_map[p]를 확인
    next_candidates = set()
    for p in current_event_group['predicates']:
        if p in nxt_map:
            for nxtp in nxt_map[p]:
                # 이미 할당되었으면 skip
                if nxtp in assigned_predicates:
                    continue
                next_candidates.add(nxtp)
    
    # now, DFS: 각 next_candidate에 대해 새 event group을 만들고
    #           그 event group이 완성되면 다시 explore_event_groups(…)
    for nxtp in sorted(next_candidates, key=lambda x: int(x)):
        event_group_id = f"{timeline_id}-{nxtp}"  # 임의의 식별자
        new_event_group = build_event_group(
            nxtp, eq_map, entity_map, 
            assigned_predicates, event_group_id
        )
        # event group이 만들어졌는데, predicates가 비어있을 수도 있음 
        # (이미 다른 group에 할당된 경우 전부 skip될 수 있으므로)
        if len(new_event_group['predicates']) == 0:
            continue

        # timeline에 추가
        timeline['event_groups'].append(new_event_group)

        # DFS 재귀
        explore_event_groups(new_event_group, eq_map, nxt_map, entity_map,
                             assigned_predicates, predicate_list, timeline,
                             timeline_id)


def build_timeline_groups(predicate_0, entity_0, edges):
    """
    주된 함수:
    - predicate( level=0 )를 오름차순 정렬하여 순회
    - 아직 할당 안된 노드가 있으면 새 timeline 생성
    - timeline 안에서 event group 1개 만든 뒤, 그 group의 next_TimeStamp -> DFS로 추가 group 탐색
    - 전부 끝나면 timelines 반환
    """
    eq_map, nxt_map, entity_map = build_maps(predicate_0, entity_0, edges)

    # predicate 리스트
    pred_list_sorted = sorted(predicate_0.keys(), key=lambda x: int(x))

    assigned_predicates = {}  # p -> "event_group_id"
    timelines = []
    timeline_count = 0

    idx = 0
    while idx < len(pred_list_sorted):
        p = pred_list_sorted[idx]
        idx += 1
        if p in assigned_predicates:
            continue  # 이미 어딘가에 포함됨 -> skip

        # 새로운 timeline 생성
        timeline_count += 1
        timeline = {
            'event_groups': []
        }
        timelines.append(timeline)

        # 첫 event group in this timeline
        event_group_id = f"T{timeline_count}-firstEG"
        event_group = build_event_group(
            p, eq_map, entity_map, 
            assigned_predicates, event_group_id
        )
        # 혹시 전부 skip돼서 empty면 pass
        if len(event_group['predicates']) == 0:
            continue
        timeline['event_groups'].append(event_group)

        # DFS로 next_TimeStamp 확장
        explore_event_groups(event_group, eq_map, nxt_map, entity_map, 
                             assigned_predicates, pred_list_sorted,
                             timeline, f"T{timeline_count}")

    return timelines

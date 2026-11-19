import heapq
import time
from collections import deque

import osmnx as ox


class SearchAlgorithm:
    def __init__(self, graph, objective="distance", v_max=None):
        """
        graph: گراف خروجی از build_scenario_graph (دارای weight_distance و weight_time)
        objective: 'distance' یا 'time'
        v_max: بیشترین سرعت موجود در گراف (km/h) برای هیوریستیک زمان A* و Greedy
        """
        if objective not in ("distance", "time"):
            raise ValueError("Objective must be 'distance' or 'time'")

        self.graph = graph
        self.objective = objective
        self.weight_key = "weight_distance" if objective == "distance" else "weight_time"

        if objective == "time":
            if v_max is None or v_max <= 0:
                raise ValueError("A positive v_max is required for the 'time' objective.")
            self.v_max = float(v_max)
        else:
            self.v_max = v_max

    # ---------------- Helper Methods ----------------

    def _select_edge(self, u, v, ignore_weights=False):
        """
        انتخاب یک یال مشخص (key, data) بین u و v با حفظ هویت یال‌های موازی
        و شکستن تساوی قطعی (Deterministic tie-breaking).
        """
        edges_dict = self.graph.get_edge_data(u, v)
        if ignore_weights:
            # برای BFS و DFS: بدون توجه به وزن، کوچک‌ترین کلید را قطعی انتخاب کن
            best_key = min(edges_dict.keys())
            return best_key, edges_dict[best_key]

        # برای Greedy و A*: کم‌هزینه‌ترین یال موازی (در تساوی، کوچک‌ترین کلید)
        best_key, best_data = min(
            edges_dict.items(),
            key=lambda item: (item[1][self.weight_key], item[0]),
        )
        return best_key, best_data

    def heuristic(self, node, goal):
        """
        هدف distance: فاصله مستقیم (متر)
        هدف time: 3.6 * d(n, G) / V_max (ثانیه)
        """
        y1, x1 = self.graph.nodes[node]["y"], self.graph.nodes[node]["x"]
        y2, x2 = self.graph.nodes[goal]["y"], self.graph.nodes[goal]["x"]
        d = ox.distance.great_circle(y1, x1, y2, x2)

        if self.objective == "distance":
            return d
        return (3.6 * d) / self.v_max

    def _reconstruct_result(self, parent, goal, expansions, max_frontier, runtime_s):
        """بازسازی مسیر گره‌ها، یال‌های دقیق (u, v, key) و محاسبه مسافت و زمان کل."""
        if goal not in parent:
            return {
                "found": False,
                "nodes": [],
                "edges": [],
                "total_distance_m": None,
                "total_time_s": None,
                "node_expansions": expansions,
                "max_frontier_size": max_frontier,
                "runtime_s": runtime_s,
            }

        nodes = []
        edges = []
        curr = goal
        while curr is not None:
            nodes.append(curr)
            prev_info = parent[curr]
            if prev_info is not None:
                prev_node, edge_key = prev_info
                edges.append((prev_node, curr, edge_key))
                curr = prev_node
            else:
                curr = None

        nodes.reverse()
        edges.reverse()

        total_dist = sum(self.graph.edges[u, v, k]["weight_distance"] for u, v, k in edges)
        total_time = sum(self.graph.edges[u, v, k]["weight_time"] for u, v, k in edges)

        return {
            "found": True,
            "nodes": nodes,
            "edges": edges,
            "total_distance_m": total_dist,
            "total_time_s": total_time,
            "node_expansions": expansions,
            "max_frontier_size": max_frontier,
            "runtime_s": runtime_s,
        }

    # ---------------- 1. BFS ----------------

    def bfs(self, start, goal):
        t0 = time.perf_counter()
        frontier = deque([start])
        visited = {start}
        parent: dict = {start: None}
        expansions = 0
        max_frontier = 1

        while frontier:
            max_frontier = max(max_frontier, len(frontier))
            u = frontier.popleft()
            expansions += 1

            if u == goal:
                return self._reconstruct_result(
                    parent, goal, expansions, max_frontier, time.perf_counter() - t0
                )

            # مرتب‌سازی همسایه‌ها برای شکستن تساوی قطعی
            for v in sorted(self.graph.successors(u)):
                if v not in visited:
                    visited.add(v)
                    key, _ = self._select_edge(u, v, ignore_weights=True)
                    parent[v] = (u, key)
                    frontier.append(v)

        return self._reconstruct_result({}, goal, expansions, max_frontier, time.perf_counter() - t0)

    # ---------------- 2. DFS ----------------

    def dfs(self, start, goal):
        t0 = time.perf_counter()
        frontier = [start]
        explored = set()
        parent: dict = {start: None}
        expansions = 0
        max_frontier = 1

        while frontier:
            max_frontier = max(max_frontier, len(frontier))
            u = frontier.pop()

            if u in explored:
                continue
            explored.add(u)
            expansions += 1

            if u == goal:
                return self._reconstruct_result(
                    parent, goal, expansions, max_frontier, time.perf_counter() - t0
                )

            # مرتب‌سازی معکوس تا کوچک‌ترین شناسه گره بالاتر در پشته قرار گیرد و اول باز شود
            for v in sorted(self.graph.successors(u), reverse=True):
                if v not in explored:
                    key, _ = self._select_edge(u, v, ignore_weights=True)
                    parent[v] = (u, key)
                    frontier.append(v)

        return self._reconstruct_result({}, goal, expansions, max_frontier, time.perf_counter() - t0)

    # ---------------- 3. Greedy Best-First Search ----------------

    def greedy(self, start, goal):
        t0 = time.perf_counter()
        frontier = [(self.heuristic(start, goal), start)]
        explored = set()
        parent: dict = {start: None}
        expansions = 0
        max_frontier = 1

        while frontier:
            max_frontier = max(max_frontier, len(frontier))
            _, u = heapq.heappop(frontier)

            if u in explored:
                continue
            explored.add(u)
            expansions += 1

            if u == goal:
                return self._reconstruct_result(
                    parent, goal, expansions, max_frontier, time.perf_counter() - t0
                )

            for v in sorted(self.graph.successors(u)):
                if v not in explored and v not in parent:
                    key, _ = self._select_edge(u, v, ignore_weights=False)
                    parent[v] = (u, key)
                    heapq.heappush(frontier, (self.heuristic(v, goal), v))

        return self._reconstruct_result({}, goal, expansions, max_frontier, time.perf_counter() - t0)

    # ---------------- 4. A* Search ----------------

    def a_star(self, start, goal):
        t0 = time.perf_counter()
        frontier = [(self.heuristic(start, goal), start)]
        g_cost = {start: 0.0}
        parent: dict = {start: None}
        explored = set()
        expansions = 0
        max_frontier = 1

        while frontier:
            max_frontier = max(max_frontier, len(frontier))
            _, u = heapq.heappop(frontier)

            if u in explored:
                continue
            explored.add(u)
            expansions += 1

            if u == goal:
                return self._reconstruct_result(
                    parent, goal, expansions, max_frontier, time.perf_counter() - t0
                )

            for v in sorted(self.graph.successors(u)):
                key, data = self._select_edge(u, v, ignore_weights=False)
                new_g = g_cost[u] + data[self.weight_key]

                if new_g < g_cost.get(v, float("inf")):
                    g_cost[v] = new_g
                    parent[v] = (u, key)
                    f_cost = new_g + self.heuristic(v, goal)
                    heapq.heappush(frontier, (f_cost, v))

        return self._reconstruct_result({}, goal, expansions, max_frontier, time.perf_counter() - t0)


if __name__ == "__main__":
    from graph_weights import build_scenario_graph
    from load_graph import load_graph
    from traffic_api import load_matches
    from traffic_matching import apply_traffic_matches

    # بارگذاری گراف و اسنپ‌شات واقعی ترافیک
    G_base = load_graph()
    matches = load_matches("./data/traffic_snapshot.json")
    G_traffic = apply_traffic_matches(G_base.copy(), matches)
    G_scen, vmax = build_scenario_graph(G_traffic, scenario="traffic")

    # انتخاب دو گره واقعی برای تست سریع
    nodes_list = list(G_scen.nodes)
    start_node, goal_node = nodes_list[0], nodes_list[-1]

    print(f"\nTesting all 4 algorithms (Objective: TIME, V_max={vmax:.2f} km/h)")
    print(f"Start: {start_node} -> Goal: {goal_node}\n")

    solver = SearchAlgorithm(G_scen, objective="time", v_max=vmax)
    for name, func in [
        ("BFS", solver.bfs),
        ("DFS", solver.dfs),
        ("Greedy", solver.greedy),
        ("A*", solver.a_star),
    ]:
        res = func(start_node, goal_node)
        if res["found"]:
            print(
                f"{name:6} | Dist: {res['total_distance_m']:7.1f} m | "
                f"Time: {res['total_time_s']:6.1f} s | "
                f"Expansions: {res['node_expansions']:3d} | "
                f"MaxFrontier: {res['max_frontier_size']:3d} | "
                f"Runtime: {res['runtime_s']*1000:.2f} ms"
            )
        else:
            print(f"{name:6} | No path found.")

import heapq
import osmnx as ox


class SearchAlgorithm:

    def __init__(self, london_graph, objective="distance"):
        self.graph = london_graph
        self.vertices = list(self.graph.nodes)
        self.mark = {v: 0 for v in self.vertices} #??
        self.count = 0

        self.objective = objective

        if objective not in ["distance", "time"]:
            raise ValueError("Objective must be distance or time")

        if objective == "time":
            self.Vmax = max(
                data["speed_kph"]
                for u, v, data in self.graph.edges(data=True)
            )

    def reset(self):
        self.count = 0
        for v in self.vertices:
            self.mark[v] = 0

    # ---------------- Edge Cost ----------------

    def edge_cost(self, u, v):
        edges = self.graph.get_edge_data(u, v)

        if self.objective == "distance":
            return min(data["length"] for data in edges.values())

        return min(data["travel_time"] for data in edges.values())

    # ---------------- Heuristic ----------------

    def heuristic(self, node, goal):
        x1 = self.graph.nodes[node]["x"]
        y1 = self.graph.nodes[node]["y"]

        x2 = self.graph.nodes[goal]["x"]
        y2 = self.graph.nodes[goal]["y"]

        d = ox.distance.great_circle(y1, x1, y2, x2)

        if self.objective == "distance":
            return d

        return 3.6 * d / self.Vmax

    # ---------------- DFS ----------------

    def dfs(self, start):
        self.reset()

        def dfsexplore(vertex):
            self.count += 1
            self.mark[vertex] = self.count

            for n in self.graph.neighbors(vertex):
                if self.mark[n] == 0:
                    dfsexplore(n)

        dfsexplore(start)
        return self.mark

    # ---------------- BFS ----------------

    def bfs(self, start):
        self.reset()

        queue = [start]
        self.count = 1
        self.mark[start] = self.count

        while queue:
            u = queue.pop(0)

            for w in self.graph.neighbors(u):
                if self.mark[w] == 0:
                    self.count += 1
                    self.mark[w] = self.count
                    queue.append(w)

        return self.mark

    # ---------------- Greedy ----------------

    def greedy(self, start, goal):
        frontier = [(self.heuristic(start, goal), start)]
        explored = set()
        parent = {start: None}

        while frontier:
            _, u = heapq.heappop(frontier)

            if u in explored:
                continue

            explored.add(u)

            if u == goal:
                return self.get_path(parent, goal)

            for v in self.graph.neighbors(u):
                if v not in explored and v not in parent:
                    parent[v] = u
                    heapq.heappush(
                        frontier,
                        (self.heuristic(v, goal), v)
                    )

        return None

    # ---------------- A* ----------------

    def A_star(self, start, goal):
        frontier = [(self.heuristic(start, goal), start)]

        g = {start: 0}
        parent = {start: None}
        explored = set()

        while frontier:
            _, u = heapq.heappop(frontier)

            if u in explored:
                continue

            if u == goal:
                return self.get_path(parent, goal)

            explored.add(u)

            for v in self.graph.neighbors(u):

                new_g = g[u] + self.edge_cost(u, v)

                if new_g < g.get(v, float("inf")):
                    g[v] = new_g
                    parent[v] = u

                    explored.discard(v)

                    f = new_g + self.heuristic(v, goal)

                    heapq.heappush(frontier, (f, v))

        return None

    # ---------------- Path ----------------

    def get_path(self, parent, goal):
        path = []

        while goal is not None:
            path.append(goal)
            goal = parent[goal]

        return path[::-1]

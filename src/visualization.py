import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import osmnx as ox

from graph_weights import build_scenario_graph
from load_graph import load_graph
from search_algorithm import SearchAlgorithm
from traffic_api import load_matches
from traffic_matching import apply_traffic_matches

HOST = "127.0.0.1"
PORT = 8000
SNAPSHOT_PATH = "./data/traffic_snapshot.json"
STATIC_DIR = Path(__file__).parent / "static"


print("Initializing map data and scenarios...")
G_base = load_graph()
matches = load_matches(SNAPSHOT_PATH)
G_traffic = apply_traffic_matches(G_base.copy(), matches)

all_nodes = list(G_traffic.nodes)
DEFAULT_START_NODE = all_nodes[0]
FIXED_GOAL_NODE = all_nodes[-1]

G_free, vmax_free = build_scenario_graph(G_traffic, scenario="free_flow")
G_meas, vmax_meas = build_scenario_graph(G_traffic, scenario="traffic")

_init_solver = SearchAlgorithm(G_meas, objective="time", v_max=vmax_meas)
_init_res = _init_solver.a_star(DEFAULT_START_NODE, FIXED_GOAL_NODE)
if _init_res["found"] and _init_res["edges"]:
    MANUAL_CLOSED_EDGE = _init_res["edges"][len(_init_res["edges"]) // 2]
else:
    MANUAL_CLOSED_EDGE = next(iter(G_meas.edges(keys=True)))

G_clos, vmax_clos = build_scenario_graph(
    G_traffic, scenario="closure", closed_edge=MANUAL_CLOSED_EDGE
)

SCENARIOS = {
    "free_flow": (G_free, vmax_free),
    "traffic": (G_meas, vmax_meas),
    "closure": (G_clos, vmax_clos),
}

def get_edge_coords(G, u, v, key):
    """استخراج مختصات دقیق یک یال موازی به فرمت [lat, lon] برای Leaflet."""
    data = G.edges[u, v, key]
    geom = data.get("geometry")
    if geom is not None:

        return [[float(y), float(x)] for x, y in geom.coords]
    return [
        [float(G.nodes[u]["y"]), float(G.nodes[u]["x"])],
        [float(G.nodes[v]["y"]), float(G.nodes[v]["x"])],
    ]


def find_nearest_node(G, lat, lon):
    return min(
        G.nodes,
        key=lambda n: ox.distance.great_circle(lat, lon, G.nodes[n]["y"], G.nodes[n]["x"]),
    )


def build_traffic_payload():
    layers = {"red": [], "yellow": [], "closed": [], "missing": [], "manual_closed": [], "normal": []}

    for u, v, key, data in G_traffic.edges(keys=True, data=True):
        coords = get_edge_coords(G_traffic, u, v, key)
        info = {
            "coords": coords,
            "current_speed": data.get("current_speed_kmh"),
            "free_flow_speed": data.get("free_flow_speed_kmh"),
            "status": data.get("traffic_status"),
        }

        if (u, v, key) == MANUAL_CLOSED_EDGE:
            layers["manual_closed"].append(info)

        if data.get("is_closed", False):
            layers["closed"].append(info)

        else:
            color = data.get("traffic_color", "missing")
            if color == "red":
                layers["red"].append(info)
            elif color == "yellow":
                layers["yellow"].append(info)
            elif color == "missing":
                layers["missing"].append(info)
            elif color == "none":
                layers["normal"].append(info)
            

    start_lat = float(G_traffic.nodes[DEFAULT_START_NODE]["y"])
    start_lon = float(G_traffic.nodes[DEFAULT_START_NODE]["x"])
    goal_lat = float(G_traffic.nodes[FIXED_GOAL_NODE]["y"])
    goal_lon = float(G_traffic.nodes[FIXED_GOAL_NODE]["x"])

    return {
        "center": [51.5215, -0.1300],
        "default_start": {"node": DEFAULT_START_NODE, "lat": start_lat, "lon": start_lon},
        "goal": {"node": FIXED_GOAL_NODE, "lat": goal_lat, "lon": goal_lon},
        "layers": layers,
    }


def compute_routes_payload(lat, lon, scenario, objective):
    if scenario not in SCENARIOS:
        scenario = "traffic"
    if objective not in ("time", "distance"):
        objective = "time"

    G_scen, v_max = SCENARIOS[scenario]
    start_node = find_nearest_node(G_scen, lat, lon)
    goal_node = FIXED_GOAL_NODE

    solver = SearchAlgorithm(G_scen, objective=objective, v_max=v_max)
    algorithms = {
        "A*": solver.a_star,
        "Greedy": solver.greedy,
        "BFS": solver.bfs,
        "DFS": solver.dfs,
    }

    routes_out = {}
    for name, func in algorithms.items():
        res = func(start_node, goal_node)
        segments = []
        if res["found"]:
            segments = [get_edge_coords(G_scen, u, v, k) for u, v, k in res["edges"]]

        routes_out[name] = {
            "found": res["found"],
            "segments": segments,
            "total_distance_m": round(res["total_distance_m"], 1) if res["found"] else None,
            "total_time_s": round(res["total_time_s"], 1) if res["found"] else None,
            "node_expansions": res["node_expansions"],
            "max_frontier_size": res["max_frontier_size"],
            "runtime_ms": round(res["runtime_s"] * 1000, 3),
        }

    return {
        "scenario": scenario,
        "objective": objective,
        "v_max": round(v_max, 2),
        "start": {
            "node": start_node,
            "lat": float(G_scen.nodes[start_node]["y"]),
            "lon": float(G_scen.nodes[start_node]["x"]),
        },
        "goal": {
            "node": goal_node,
            "lat": float(G_scen.nodes[goal_node]["y"]),
            "lon": float(G_scen.nodes[goal_node]["x"]),
        },
        "routes": routes_out,
    }


# HTTP PART

class MapRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filepath, content_type):
        if not filepath.exists():
            self.send_error(404, "File not found")
            return
        body = filepath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")

        elif path == "/static/app.js":
            self._send_file(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")

        elif path == "/api/traffic":
            self._send_json(build_traffic_payload())

        elif path == "/api/route":
            try:
                lat = float(params["lat"][0])
                lon = float(params["lon"][0])
                scenario = params.get("scenario", ["traffic"])[0]
                objective = params.get("objective", ["time"])[0]
                payload = compute_routes_payload(lat, lon, scenario, objective)
                self._send_json(payload)
            except (KeyError, ValueError) as e:
                self._send_json({"error": f"Invalid parameters: {e}"}, status=400)

        else:
            self.send_error(404, "Endpoint not found")


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), MapRequestHandler)
    print(f"Interactive map running at: http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
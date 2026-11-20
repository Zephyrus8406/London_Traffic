# London_Traffic

## Authors

- Saba Najafian
- Saba Gorji
- Parmis Solgi

Course: Artificial Intelligence, Fall 2026, KNTU
Instructor: Dr. Maryam Abdolali

## The Problem

The shortest road is not always the fastest one. A short route through a jammed junction can take longer than a longer route where traffic keeps moving.

In this project we test that idea on a real map of central London. We take the road network from OpenStreetMap, add **real TomTom traffic data**, and compare four search algorithms that we wrote ourselves: **BFS, DFS, greedy best-first search and A\***.

## What We Did

**1. Built the map.** We download a small drivable part of London with OSMnx and keep it as a directed graph, so one-way streets are respected. Road lengths are in meters, and parallel edges between the same two nodes keep their own identity (`(u, v, key)`) in the search.

**2. Added live traffic.** We ask the TomTom Flow Segment Data API for speeds near road midpoints, match each answer to OSM edges, and store a current speed and a free-flow speed on the edge. Travel time is

```
t = 3.6 * length / speed      (length in meters, speed in km/h)
```

**3. Compared the algorithms.** Each search runs with two goals (shortest distance or shortest time) in three situations: **free flow**, **measured traffic**, and **measured traffic plus one closed directed edge**. For every run we record route distance, travel time, runtime, node expansions and maximum frontier size.

## How It Works

```
downloading_graph.py  ->  data/graph/london.graphml
collect_traffic.py    ->  data/traffic_snapshot.json   (TomTom + matching)
```

Behind these scripts:

- `load_graph.py` loads the saved graph.
- `traffic_api.py` calls TomTom and cleans the answer.
- `traffic_matching.py` matches TomTom segments to OSM edges.
- `graph_weights.py` builds the three scenario graphs.
- `search_algorithm.py` holds the four algorithms.

## The Map

`downloading_graph.py` downloads the drivable roads within **750 m** of `(51.5215, -0.1300)` with `simplify=True` and saves them to `data/graph/london.graphml`:

```python
G = ox.graph_from_point(
    (51.5215, -0.1300), dist=750, network_type="drive", simplify=True
)
ox.save_graphml(G, filepath="./data/graph/london.graphml")
```

The saved graph has 439 nodes and 880 edges.

## Traffic Data

### Getting it

`collect_traffic.py` walks over the graph edges, queries TomTom at each edge midpoint (zoom 18, speeds in km/h), and saves the matches:

- at most **200 queries** per run (`MAX_QUERIES`), with a short pause between requests
- edges that were already matched by an earlier query are skipped
- the snapshot is saved as `data/traffic_snapshot.json` with a UTC `collected_at` time
- the collection interval and the traffic coverage are printed at the end

All algorithms and scenarios use this one saved snapshot.

### Matching TomTom to OSM

For every TomTom segment we look at OSM edges within 25 m and give each a score:

```
score = 0.7 * overlap + 0.3 * direction_similarity
```

`overlap` is the share of the OSM edge that lies within 10 m of the TomTom line, and `direction_similarity` compares the headings of the two lines. Edges with a score of at least **0.55** get that segment's speeds. Matching is done in a projected CRS so distances are in meters.

### Cleaning it

Every answer gets one status (`classify_traffic` in `traffic_api.py`):

| Status | When | What we do |
|--------|------|------------|
| `closed` | TomTom reports a road closure | edge is removed from the graph |
| `missing` | speed, free-flow speed or confidence is absent | not used as a measurement |
| `unreliable` | confidence < 0.5 | not used as a measurement |
| `invalid_speed` | current or free-flow speed is zero or negative | not used as a measurement |
| `valid` | everything above passes | used |
| `unmatched` | no TomTom segment matched this edge | not used as a measurement |

Edges that are not `valid` still need a cost so the graph does not fall apart. For those we use the OSM speed limit (`maxspeed`, with mph converted to km/h, or 30 km/h if there is none). They are labeled as missing data, separately from real measurements.
This keeps the graph connected, but it means these edges are assumed to move at the speed limit, so real jams on roads without data are not seen by the search. In our snapshot, 356 of 880 edges (about 40%) had no traffic data and used the speed limit.

### Colors

With r = current speed / free-flow speed:

- **red**: r < 0.5
- **yellow**: 0.5 <= r < 0.8
- no overlay: r >= 0.8
- "missing" label: every edge that is not `valid`

### Snapshot details

- **Collected at:** 2026-11-20, about 10:48 to 10:51 UTC
- **Collection interval:** 204.8 seconds
- **Edges in graph / valid edges / coverage:** 880 / 520 / 59.1%

## Scenarios

`build_scenario_graph(G, scenario)` in `graph_weights.py` returns a graph and its V_max:

| Scenario | Speeds used | Extra |
|----------|-------------|-------|
| `free_flow` | free-flow speed on valid edges | closed edges removed |
| `traffic` | current speed on valid edges | closed edges removed |
| `closure` | same as `traffic` | one more directed edge removed |

Every edge gets both `weight_distance` (meters) and `weight_time` (seconds), and V_max is the highest speed used anywhere in that scenario graph.

## The Algorithms

All four are in `search_algorithm.py` and return the same kind of result:

```python
from search_algorithm import SearchAlgorithm

solver = SearchAlgorithm(G_scenario, objective="time", v_max=vmax)   # or "distance"
res = solver.a_star(start_node, goal_node)    # also: bfs, dfs, greedy

res["nodes"]               # route as nodes
res["edges"]               # route as (u, v, key), parallel edges kept
res["total_distance_m"], res["total_time_s"]
res["node_expansions"], res["max_frontier_size"], res["runtime_s"]
```

| Goal | Edge cost | Heuristic |
|------|-----------|-----------|
| `distance` | road length | straight-line distance to the goal |
| `time` | travel time | 3.6 * distance / V_max |

```python
def heuristic(self, node, goal):
    d = ox.distance.great_circle(y1, x1, y2, x2)      # meters
    if self.objective == "distance":
        return d
    return (3.6 * d) / self.v_max                      # seconds
```

**Why the time heuristic is admissible.** A straight line is never longer than a road path, and no edge can be driven faster than V_max. So the real remaining time is at least 3.6 * d / V_max. It is also consistent, because every edge costs at least 3.6 * (straight distance between its ends) / V_max.

How each one behaves:

- **BFS** explores level by level and ignores weights, so it finds the route with the fewest road segments, not the shortest or fastest one.
- **DFS** (iterative, with an explored set to handle cycles) ignores weights too. Its route depends on the order neighbors are visited, so we visit them in sorted node order to keep it deterministic.
- **Greedy** always expands the node that looks closest to the goal (lowest h). It is fast but can return a worse route.
- **A\*** expands the node with the lowest g + h and finds the best route for the chosen goal.

Ties are always broken by node id, and among parallel edges by the cheapest one (smallest key on ties), so results are repeatable.

`max_frontier_size` is the largest size of the queue, stack or heap. For A\* and DFS it can include duplicate entries for a node.

## Project Structure

```
.
├── src/
│   ├── downloading_graph.py    # download and save the OSM graph (run once)
│   ├── load_graph.py           # load the saved graph
│   ├── traffic_api.py          # TomTom requests, cleaning, save/load snapshot
│   ├── traffic_matching.py     # match TomTom segments to OSM edges
│   ├── collect_traffic.py      # collect and save one traffic snapshot
│   ├── graph_weights.py        # free-flow / traffic / closure graphs
│   ├── search_algorithm.py     # BFS, DFS, greedy, A*
│   └── experiments/            # practice scripts for shapely, geopandas, OSMnx
├── data/                       # graph and snapshot (not committed, see .gitignore)
├── cache/                      # OSMnx cache (not committed)
├── notebook.ipynb
├── requirements.txt
└── README.md
```

## Setup

```bash
git clone https://github.com/Zephyrus8406/London_Traffic.git
cd London_Traffic
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The code needs OSMnx 2.x, NetworkX, GeoPandas, Shapely, requests and python-dotenv (matplotlib is only used in the practice scripts).

### TomTom API key

Get a key from the TomTom developer portal and put it in a file named `.env` in the project root:

```
TOMTOM_API_KEY_2=your_key_here
```

`.env` is in `.gitignore`, so the key is never committed. Follow TomTom's rules for storing and sharing traffic data, and stay within the free allowance.

## How to Run

Run everything from the project root, because the scripts use paths like `./data/...`.

```bash
python src/downloading_graph.py    # 1. download the map (once)
python src/collect_traffic.py      # 2. collect one traffic snapshot
```

`data/` is not committed, so anyone who clones the repo has to run these two steps first.

Most modules also have a small test in their `__main__` block, for example `python src/graph_weights.py`.

## Results

_Add your comparison tables here: three origins, one destination, three scenarios, two goals. For each run give distance, time, median runtime over 5 runs, node expansions and maximum frontier size. Then explain why BFS ignores costs, how DFS depends on neighbor order, and when greedy returns a worse route than A\*._

## Resources

- [OSMnx](https://osmnx.readthedocs.io/)
- [TomTom Flow Segment Data API](https://developer.tomtom.com/traffic-api/documentation/traffic-flow/flow-segment-data)
- TomTom free allowance and terms (see the TomTom developer portal)

let trafficData = null;
let routeData = null;
let currentStart = null;

let bounds = { minLat: 51.51, maxLat: 51.53, minLon: -0.14, maxLon: -0.12 };
const PADDING = 30;

const scenarioSelect = document.getElementById("scenario-select");
const objectiveSelect = document.getElementById("objective-select");
const statsBody = document.getElementById("stats-body");

function setup() {
  const container = document.getElementById("canvas-container");
  const cnv = createCanvas(container.clientWidth, container.clientHeight);
  cnv.parent("canvas-container");

  scenarioSelect.addEventListener("change", () => {
    if (currentStart) fetchRoutes(currentStart.lat, currentStart.lon);
  });
  objectiveSelect.addEventListener("change", () => {
    if (currentStart) fetchRoutes(currentStart.lat, currentStart.lon);
  });

  initMapData();
}

function windowResized() {
  const container = document.getElementById("canvas-container");
  resizeCanvas(container.clientWidth, container.clientHeight);
}

function computeBounds(layers) {
  let minLat = Infinity, maxLat = -Infinity;
  let minLon = Infinity, maxLon = -Infinity;

  for (const list of Object.values(layers)) {
    for (const item of list) {
      for (const [lat, lon] of item.coords) {
        if (lat < minLat) minLat = lat;
        if (lat > maxLat) maxLat = lat;
        if (lon < minLon) minLon = lon;
        if (lon > maxLon) maxLon = lon;
      }
    }
  }
  bounds = { minLat, maxLat, minLon, maxLon };
}

function getProjectionParams() {
  const midLatRad = ((bounds.minLat + bounds.maxLat) / 2) * (Math.PI / 180);
  const cosLat = Math.cos(midLatRad);

  const geoW = (bounds.maxLon - bounds.minLon) * cosLat;
  const geoH = bounds.maxLat - bounds.minLat;

  const availW = width - 2 * PADDING;
  const availH = height - 2 * PADDING;
  const scale = Math.min(availW / geoW, availH / geoH);

  const offsetX = (width - geoW * scale) / 2;
  const offsetY = (height - geoH * scale) / 2;

  return { cosLat, scale, offsetX, offsetY };
}

function latLonToXY(lat, lon) {
  const { cosLat, scale, offsetX, offsetY } = getProjectionParams();
  const x = offsetX + (lon - bounds.minLon) * cosLat * scale;
  const y = offsetY + (bounds.maxLat - lat) * scale;
  return { x, y };
}

function xyToLatLon(x, y) {
  const { cosLat, scale, offsetX, offsetY } = getProjectionParams();
  const lon = bounds.minLon + (x - offsetX) / (cosLat * scale);
  const lat = bounds.maxLat - (y - offsetY) / scale;
  return { lat, lon };
}

async function initMapData() {
  const res = await fetch("/api/traffic");
  trafficData = await res.json();
  computeBounds(trafficData.layers);

  currentStart = {
    lat: trafficData.default_start.lat,
    lon: trafficData.default_start.lon,
  };
  await fetchRoutes(currentStart.lat, currentStart.lon);
}

async function fetchRoutes(lat, lon) {
  const scenario = scenarioSelect.value;
  const objective = objectiveSelect.value;
  const url = `/api/route?lat=${lat}&lon=${lon}&scenario=${scenario}&objective=${objective}`;

  const res = await fetch(url);
  routeData = await res.json();
  currentStart = { lat: routeData.start.lat, lon: routeData.start.lon };
  renderStatsTable(routeData.routes);
}

function renderStatsTable(routes) {
  statsBody.innerHTML = "";
  for (const [algoName, info] of Object.entries(routes)) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><strong>${algoName}</strong></td>
      <td>${info.found ? "Found" : "No Path"}</td>
      <td>${info.total_distance_m ?? "-"}</td>
      <td>${info.total_time_s ?? "-"}</td>
      <td>${info.node_expansions}</td>
      <td>${info.max_frontier_size}</td>
      <td>${info.runtime_ms}</td>
    `;
    statsBody.appendChild(row);
  }
}

function drawPolyline(coords) {
  noFill();
  beginShape();
  for (const [lat, lon] of coords) {
    const pt = latLonToXY(lat, lon);
    vertex(pt.x, pt.y);
  }
  endShape();
}

function draw() {
  background(15, 23, 42);

  if (!trafficData) {
    fill(200);
    noStroke();
    textAlign(CENTER, CENTER);
    text("Loading London graph...", width / 2, height / 2);
    return;
  }

  const layers = trafficData.layers;

  if (layers.normal) {
    stroke(51, 65, 85);
    strokeWeight(1.5);
    layers.normal.forEach((item) => drawPolyline(item.coords));
  }

  if (document.getElementById("chk-missing").checked) {
    stroke(100, 116, 139);
    strokeWeight(1.5);
    layers.missing.forEach((item) => drawPolyline(item.coords));
  }
  if (document.getElementById("chk-yellow").checked) {
    stroke(234, 179, 8);
    strokeWeight(2.5);
    layers.yellow.forEach((item) => drawPolyline(item.coords));
  }
  if (document.getElementById("chk-red").checked) {
    stroke(220, 38, 38);
    strokeWeight(3);
    layers.red.forEach((item) => drawPolyline(item.coords));
  }
  if (document.getElementById("chk-closed").checked) {
    stroke(0);
    strokeWeight(4);
    layers.closed.forEach((item) => drawPolyline(item.coords));
  }
  if (document.getElementById("chk-manual").checked) {
    stroke(244, 63, 94);
    strokeWeight(5);
    layers.manual_closed.forEach((item) => drawPolyline(item.coords));
  }

  
  if (routeData) {
    const drawRoute = (algoName, checkboxId, r, g, b, weight) => {
      const info = routeData.routes[algoName];
      if (!info || !info.found || !document.getElementById(checkboxId).checked) return;
      stroke(r, g, b);
      strokeWeight(weight);
      info.segments.forEach((seg) => drawPolyline(seg));
    };

    drawRoute("DFS", "chk-dfs", 106, 13, 173, 2.5);
    drawRoute("BFS", "chk-bfs", 192, 132, 252, 3.5);
    drawRoute("Greedy", "chk-greedy", 74, 222, 128, 4.5);
    drawRoute("A*", "chk-astar", 59, 130, 246, 5.5);

    const startPt = latLonToXY(routeData.start.lat, routeData.start.lon);
    const goalPt = latLonToXY(routeData.goal.lat, routeData.goal.lon);

    stroke(255);
    strokeWeight(2);
    fill(34, 197, 94);
    circle(startPt.x, startPt.y, 14);

    fill(239, 68, 68);
    circle(goalPt.x, goalPt.y, 14);

    noStroke();
    fill(255);
    textSize(12);
    textAlign(LEFT, CENTER);
    text("START", startPt.x + 10, startPt.y);
    text("GOAL", goalPt.x + 10, goalPt.y);
  }
}

function doubleClicked() {
  if (mouseX >= 0 && mouseX <= width && mouseY >= 0 && mouseY <= height) {
    const { lat, lon } = xyToLatLon(mouseX, mouseY);
    fetchRoutes(lat, lon);
  }
}
# def build_scenario_graph(G,scenario):
#     if scenario not in ("free_flow", "traffic"):
#         raise ValueError("Unknown scenario")
#     H = G.copy()
#     for u, v, key, data in list(H.edges(keys=True, data=True)):
#         status = data.get("traffic_status")
#         # Keep only valid measurements.
#         if status != "valid":
#             H.remove_edge(u, v, key)
#             continue
#         if data.get("is_closed", False):
#             H.remove_edge(u, v, key)
#             continue
#         if scenario == "free_flow":
#             cost = data.get("free_flow_time_s")
#         else:
#             cost = data.get("traffic_time_s")
#         if cost is None or cost <= 0:
#             H.remove_edge(u, v, key)
#             continue
#         # defining the cost for the data
#         data["weight"] = float(cost)
#     return H

from traffic_api import calculate_travel_time


def parse_osm_speed_kmh(maxspeed_attr, default_speed_kmh=30.0):

    if not maxspeed_attr:
        return default_speed_kmh

    if isinstance(maxspeed_attr, list):
        maxspeed_attr = maxspeed_attr[0]

    text = str(maxspeed_attr).strip().lower()
    parts = text.split()
    try:
        value = float(parts[0])
        if "mph" in text:
            return value * 1.60934
        return value if value > 0 else default_speed_kmh
    except (ValueError, IndexError):
        return default_speed_kmh


def build_scenario_graph(G, scenario="traffic", closed_edge=None, default_speed_kmh=30.0):
    """
    آماده‌سازی و وزن‌دهی گراف برای یکی از ۳ سناریوی تمرین: 'free_flow'، 'traffic' یا 'closure'.
    خروجی: (گراف آماده‌شده H, بیشترین سرعت موجود در گراف V_max)
    """
    if scenario not in ("free_flow", "traffic", "closure"):
        raise ValueError("Scenario must be 'free_flow', 'traffic', or 'closure'")

    H = G.copy()
    max_speed_found = 1.0

    # حذف یال جهت‌دار انتخابی در سناریوی انسداد دستی (closure)
    if scenario == "closure" and closed_edge is not None:
        u_c, v_c, k_c = closed_edge
        if H.has_edge(u_c, v_c, k_c):
            H.remove_edge(u_c, v_c, k_c)

    for u, v, key, data in list(H.edges(keys=True, data=True)):
        # ۱. حذف قطعی خیابان‌های مسدود تاییدشده
        if data.get("is_closed", False):
            H.remove_edge(u, v, key)
            continue

        status = data.get("traffic_status")
        length_m = float(data.get("length", 1.0))

        # ۲. تعیین سرعت و زمان سفر بر اساس سناریو
        if status == "valid":
            if scenario == "free_flow":
                speed = float(data["free_flow_speed_kmh"])
                cost_time = float(data["free_flow_time_s"])
            else:  # برای traffic و closure
                speed = float(data["current_speed_kmh"])
                cost_time = float(data["traffic_time_s"])
        else:
            # سرعت جایگزین برای یال‌های بدون داده (جلوگیری از تکه‌تکه شدن گراف)
            speed = parse_osm_speed_kmh(data.get("maxspeed"), default_speed_kmh)
            cost_time = float(calculate_travel_time(length_m, speed))

        # ۳. ذخیره هم‌زمان هر دو وزن (زمان و مسافت) روی یال
        data["weight_time"] = cost_time
        data["weight_distance"] = length_m

        if speed > max_speed_found:
            max_speed_found = speed

    return H, max_speed_found

if __name__ == "__main__":
    from load_graph import load_graph
    from traffic_matching import apply_traffic_matches

    # ۱. تست تبدیل سرعت‌های OSM (به خصوص mph در لندن)
    print("--- Testing parse_osm_speed_kmh ---")
    print("20 mph ->", round(parse_osm_speed_kmh("20 mph"), 2), "km/h")
    print("['30 mph', '20 mph'] ->", round(parse_osm_speed_kmh(["30 mph", "20 mph"]), 2), "km/h")
    print("None (default) ->", parse_osm_speed_kmh(None), "km/h")

    # ۲. بارگذاری گراف و انتخاب ۳ یال واقعی برای تست
    G_base = load_graph()
    sample_edges = list(G_base.edges(keys=True))[:3]
    e_valid, e_closed_api, e_manual_close = sample_edges

    # ساخت داده ترافیکی فرضی: یال اول پرترافیک، یال دوم مسدود در API، بقیه بدون داده
    dummy_matches = {
        e_valid: {
            "current_speed": 15.0,
            "free_flow_speed": 45.0,
            "confidence": 0.9,
            "road_closure": False,
        },
        e_closed_api: {
            "current_speed": 0.0,
            "free_flow_speed": 40.0,
            "confidence": 0.95,
            "road_closure": True,
        },
    }

    G_traffic = apply_traffic_matches(G_base.copy(), dummy_matches)

    # ۳. تست هر ۳ سناریو
    G_free, vmax_free = build_scenario_graph(G_traffic, scenario="free_flow")
    G_meas, vmax_meas = build_scenario_graph(G_traffic, scenario="traffic")
    G_clos, vmax_clos = build_scenario_graph(
        G_traffic, scenario="closure", closed_edge=e_manual_close
    )

    print("\n--- Testing Scenarios ---")
    print(f"Original edges : {G_base.number_of_edges()}")
    print(f"Free-flow edges: {G_free.number_of_edges()} | V_max: {vmax_free:.2f} km/h")
    print(f"Traffic edges  : {G_meas.number_of_edges()} | V_max: {vmax_meas:.2f} km/h")
    print(f"Closure edges  : {G_clos.number_of_edges()} | V_max: {vmax_clos:.2f} km/h")

    # ۴. بررسی دقیق مقادیر وزن روی یال معتبر (باید زمان ترافیک ۳ برابر جریان آزاد باشد)
    u, v, k = e_valid
    t_free = G_free.edges[u, v, k]["weight_time"]
    t_meas = G_meas.edges[u, v, k]["weight_time"]
    dist = G_meas.edges[u, v, k]["weight_distance"]

    print(f"\n--- Checking Valid Edge {e_valid} ---")
    print(f"Distance: {dist:.2f} m | Free-flow time: {t_free:.2f} s | Traffic time: {t_meas:.2f} s")
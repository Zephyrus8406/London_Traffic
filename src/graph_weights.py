## graph_weights ###
def assign_weights(G, scenario="traffic"):
    
    max_speed_found = 1.0

    for u, v, k, data in G.edges(keys=True, data=True):
        length = float(data.get('length', 1.0))
        
        if scenario == "free_flow":
            speed = data.get('v_free', 30.0)
        else:
            speed = data.get('v_current', 30.0)

        if data.get('is_closed', False) or (scenario == "closure" and data.get('manual_closure', False)):
            cost_time = float('inf')
            cost_distance = float('inf')
        else:
            cost_time = (3.6 * length) / speed  
            cost_distance = length

        data['weight_time'] = cost_time
        data['weight_distance'] = cost_distance

        if speed > max_speed_found and speed != float('inf'):
            max_speed_found = speed

    return G, max_speed_found

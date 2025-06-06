# --------------------------------------
# How to run this application: (Version with CO2 calculation - Challenge)
# --------------------------------------
# 1. Activate the virtual environment:
#    .\env\Scripts\activate
# 2. Run the Python script:
#    python app_challenge.py
# 3. Send a POST request with a JSON payload (example with payload1.json):
#    curl -X POST -H "Content-Type: application/json" -d @example_payloads/payload1.json http://localhost:8888/productionplan
# --------------------------------------

from flask import Flask, request, jsonify
import json
from datetime import datetime
import os

# Get CO2 emission factor from environment variable, default to 0.3 if not set
CO2_EMISSION_FACTOR = float(os.getenv('CO2_EMISSION_FACTOR', '0.3'))

# Create the Flask application.
app = Flask(__name__)

# Only accepts POST requests.
@app.route('/productionplan', methods=['POST'])
def production_plan():
    try:
        # Get JSON data from the request.
        payload = request.get_json()
        app.logger.info("Received JSON payload.")
        if not payload:
            return jsonify({"error": "Invalid JSON payload"}), 400

        # Extract key data from the payload.
        load = payload.get('load')
        fuels = payload.get('fuels')
        powerplants = payload.get('powerplants')

        # Validate that required fields are present and have correct types.
        if not isinstance(load, (int, float)):
            return jsonify({"error": "Field 'load' must be a number"}), 400
        if not isinstance(fuels, dict):
            return jsonify({"error": "Field 'fuels' must be an object"}), 400
        if not isinstance(powerplants, list):
            return jsonify({"error": "Field 'powerplants' must be a list"}), 400
        
        app.logger.info("Input payload validated successfully.")
        app.logger.info(f"Processing {len(powerplants)} powerplants for load {load}.")

        # Validate fuels data
        required_fuels = ['gas(euro/MWh)', 'kerosine(euro/MWh)', 'co2(euro/ton)', 'wind(%)']
        for fuel_key in required_fuels:
            if fuel_key not in fuels or not isinstance(fuels[fuel_key], (int, float)):
                return jsonify({"error": f"Fuel '{fuel_key}' is missing or not a number"}), 400

        # Validate powerplants data
        for i, pp in enumerate(powerplants):
            if not isinstance(pp, dict):
                return jsonify({"error": f"Powerplant at index {i} must be an object"}), 400
            
            required_pp_fields = ['name', 'type', 'efficiency', 'pmax']
            for field in required_pp_fields:
                if field not in pp:
                    return jsonify({"error": f"Powerplant at index {i} is missing field '{field}'"}), 400
            
            if not isinstance(pp['name'], str):
                return jsonify({"error": f"Powerplant at index {i}, field 'name' must be a string"}), 400
            if not isinstance(pp['type'], str):
                return jsonify({"error": f"Powerplant at index {i}, field 'type' must be a string"}), 400
            if not isinstance(pp['efficiency'], (int, float)):
                return jsonify({"error": f"Powerplant at index {i}, field 'efficiency' must be a number"}), 400
            if not isinstance(pp['pmax'], (int, float)):
                return jsonify({"error": f"Powerplant at index {i}, field 'pmax' must be a number"}), 400
            
            if 'pmin' in pp and not isinstance(pp['pmin'], (int, float)):
                return jsonify({"error": f"Powerplant at index {i}, field 'pmin' must be a number"}), 400

        # --- Logic to calculate the production plan ---

        # Calculate the effective cost per MWh for each powerplant.
        for pp in powerplants:
            if pp['type'] == 'gasfired':
                # Gas cost per MWh of electricity.
                co2_cost_per_mwh = CO2_EMISSION_FACTOR * fuels['co2(euro/ton)']
                pp['cost_per_mwh'] = (fuels['gas(euro/MWh)'] / pp['efficiency']) + co2_cost_per_mwh
            elif pp['type'] == 'turbojet':
                # Kerosene cost per MWh of electricity.
                pp['cost_per_mwh'] = fuels['kerosine(euro/MWh)'] / pp['efficiency']
            elif pp['type'] == 'windturbine':
                # Wind turbines have zero cost.
                pp['cost_per_mwh'] = 0.0

        # Sort powerplants from cheapest to most expensive.
        powerplants.sort(key=lambda x: x['cost_per_mwh'])

        # Save the original list of powerplants to maintain order in the final response.
        original_powerplants = payload.get('powerplants')

        # Initialize the result with all powerplants and production at 0.0.
        production_plan_result = []
        powerplant_index_map = {} # To quickly update production by name.
        for i, pp in enumerate(original_powerplants):
            production_plan_result.append({"name": pp["name"], "p": 0.0})
            powerplant_index_map[pp["name"]] = i

        # Remaining load to cover.
        remaining_load = load

        # Assign production to wind powerplants first.
        for pp in powerplants:
            if pp['type'] == 'windturbine':
                # Calculate the actual wind production based on wind percentage.
                wind_production = pp['pmax'] * (fuels['wind(%)'] / 100)
                actual_production = min(wind_production, remaining_load)
                
                # Update production in the result.
                index = powerplant_index_map[pp["name"]]
                production_plan_result[index]["p"] = round(actual_production, 1)

                remaining_load -= actual_production
                if remaining_load <= 0:
                    break
        
        # Assign production to gas and turbojet powerplants.
        i = 0
        while i < len(powerplants) and remaining_load > 0:
            pp = powerplants[i]
            
            # Skip wind powerplants as they were already processed.
            if pp['type'] == 'windturbine':
                i += 1
                continue

            next_pp = None
            if i + 1 < len(powerplants):
                next_pp = powerplants[i+1]
            
            # Logic for "split" case when two powerplants have the same cost
            # and the first cannot cover the entire load, but the second can contribute its pmin.
            if (next_pp and
                pp['cost_per_mwh'] == next_pp['cost_per_mwh'] and
                remaining_load > pp['pmax'] and
                'pmin' in next_pp and next_pp['pmin'] > 0 and
                remaining_load <= (pp['pmax'] + next_pp['pmin'])):
                
                # Calculate production for the current powerplant: remaining load minus the next powerplant's Pmin.
                production_for_current = remaining_load - next_pp['pmin']
                
                # Ensure that the current powerplant's production does not exceed its Pmax.
                actual_production_current = min(production_for_current, pp['pmax'])
                
                # The next powerplant takes its Pmin.
                actual_production_next = next_pp['pmin']
                
                # Update production in the result for the current powerplant.
                index_current = powerplant_index_map[pp["name"]]
                production_plan_result[index_current]["p"] = round(actual_production_current, 1)
                remaining_load -= actual_production_current
                
                # Update production in the result for the next powerplant.
                index_next = powerplant_index_map[next_pp["name"]]
                production_plan_result[index_next]["p"] = round(actual_production_next, 1)
                remaining_load -= actual_production_next
                
                # Move the index two positions forward, as both powerplants have been processed.
                i += 2
                continue # Continue with the next iteration of the while loop
            
            # Normal assignment logic:
            # Calculate how much this powerplant can produce without exceeding its Pmax or the remaining load.
            production_to_assign = min(pp['pmax'], remaining_load)
            
            # Adjustment to ensure the next powerplant's pmin can be covered
            # if the remaining load is just what is left for the next powerplant and its pmin.
            if next_pp and 'pmin' in next_pp and next_pp['pmin'] > 0:
                if remaining_load > pp['pmax'] and (remaining_load - pp['pmax']) < next_pp['pmin']:
                    # The current powerplant produces what is necessary to leave the pmin for the next
                    production_to_assign = remaining_load - next_pp['pmin']
            
            # Logic for current powerplant's Pmin: if production is less than Pmin
            # and the remaining load allows covering Pmin, it is forced to Pmin.
            has_valid_pmin = 'pmin' in pp and pp['pmin'] > 0
            is_below_pmin = production_to_assign < pp['pmin']
            can_meet_pmin_with_remaining_load = remaining_load >= pp['pmin']

            if has_valid_pmin and is_below_pmin and can_meet_pmin_with_remaining_load:
                production_to_assign = pp['pmin']
            
            # Ensure that the final production does not exceed the remaining load.
            actual_production = min(production_to_assign, remaining_load)

            # Update production in the result.
            index = powerplant_index_map[pp["name"]]
            production_plan_result[index]["p"] = round(actual_production, 1)

            remaining_load -= actual_production
            i += 1 # Move the index one position forward for the next powerplant

        # Return the production plan as JSON.
        return jsonify(production_plan_result), 200

    except Exception as e:
        # Catch errors and return a generic error response.
        app.logger.error(f"Error processing request: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Run the Flask server if the script is started directly.
if __name__ == '__main__':
    # Configure the server to listen on port 8888 and in debug mode.
    app.run(host='0.0.0.0', port=8888, debug=True)
import json
import asyncio
import httpx
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync
from datetime import datetime, timedelta
from channels.layers import get_channel_layer
import pandas as pd

def home_view(request):
    return JsonResponse({"message": "Welcome to the Crop Mapping API!"})

def test_view(request):
    return JsonResponse({"message": "Test route working!"})

async def send_ws_update(channel_layer, update_type, startProgress=None, endProgress=None, message=None):
    data = {"type": update_type}
    if endProgress is not None:
        data["endProgress"] = endProgress
    if startProgress is not None:
        data["startProgress"] = startProgress
    data["message"] = message
    await channel_layer.group_send(
        "satellite_progress",
        {
            "type": "send_notification",
            "message": data
        }
    )

async def fetch_s2_and_s1_indices_async(geojson_data, startDate, endDate, flag):
    channel_layer = get_channel_layer()
    url_s1 = "http://localhost:4000/extract-s1-parameters"
    url_s2 = "http://localhost:4000/extract-s2-parameters"

    try:
        # Step 1: Fetching Sentinel-1 and Sentinel-2 Data (10–50% handled earlier)
        await send_ws_update(channel_layer, "progress", startProgress=10, endProgress=10, message="Initiating Data Fetch...")
        results = {}
        lock = asyncio.Lock()

        async def fetch_and_update(source, url):
            async with httpx.AsyncClient(timeout=60) as client:
                payload = {"geojson": geojson_data, "start_date": startDate, "end_date": endDate}
                response = await client.post(url, json=payload, headers={"Content-Type": "application/json"})

            async with lock:
                results[source] = response
                total_received = len(results)
                sensor_name = "Sentinel-1" if source.upper() == "S1" else "Sentinel-2"

                if total_received == 1:
                    await send_ws_update(channel_layer, "progress", startProgress=10, endProgress=25, message=f"{sensor_name} Data Retrieved. Awaiting other data...")
                elif total_received == 2:
                    await send_ws_update(channel_layer, "progress", startProgress=25, endProgress=40, message="All Satellite Data Retrieved. Merging data...")

        await asyncio.gather(fetch_and_update("s1", url_s1), fetch_and_update("s2", url_s2))

        # Step 2: Combining Sentinel-1 and Sentinel-2
        result = {
            source: response.json() if response.status_code == 200 else
                   {"error": f"{source.upper()} microservice call failed", "status_code": response.status_code}
            for source, response in results.items()
        }

        s1_vals = result.get('s1', {})
        s2_vals = result.get('s2', {})

        s2_default = {"NDVI": 0, "EVI": 0, "GNDVI": 0, "SAVI": 0, "NDWI": 0, "NDMI": 0, "RENDVI": 0}

        combined_input = {}

        for key in s1_vals:
            s1_monthly = s1_vals.get(key, {})
            s2_monthly = s2_vals.get(key, {})

            monthly_combined = {}

            for month in s1_monthly.keys():
                s1_features = s1_monthly.get(month, {})
                s2_features = s2_monthly.get(month, s2_default)

                merged_features = {
                    "VV": s1_features.get("VV", 0),
                    "VH": s1_features.get("VH", 0),
                    "VH_VV": s1_features.get("VH_VV", 0),
                }

                for k in s2_default:
                    merged_features[k] = s2_features.get(k, 0)

                monthly_combined[month] = merged_features

            combined_input[key] = monthly_combined

        await send_ws_update(channel_layer, "progress", startProgress=40, endProgress=50, message="Sentinel-1 and Sentinel-2 data Merged")

        if not flag:
            await send_ws_update(channel_layer, "progress", startProgress=50, endProgress=70, message="Extracting coordinates and features...")
            coordinates = list(combined_input.keys())
            
            await send_ws_update(channel_layer, "progress", startProgress=70, endProgress=90, message="Building GeoJSON features...")
            features = []
            for idx, key in enumerate(coordinates):
                coord = key.split(',')
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "geodesic": False,
                        "coordinates": [float(coord[0]), float(coord[1])]
                    },
                    "properties": {
                        "prediction": 0
                    }
                })

            await send_ws_update(channel_layer, "progress", startProgress=90, endProgress=100, message="Finalizing prediction output...")
            output = {
                "map": {
                    "type": "FeatureCollection",
                    "features": features,
                },
                "metrics": {
                    "ragiCoverage": 0,
                    "nonRagiCoverage": 100,
                }
            }
            return {"results": result, "output": output}

        else:
            # Step 3: Generate time series DataFrame (50–65%)
            await send_ws_update(channel_layer, "progress", startProgress=50, endProgress=65, message="Generating Time Series...")
            
            rows = []
            all_features = ["VV", "VH", "VH_VV", "NDVI", "EVI", "GNDVI", "SAVI", "NDWI", "NDMI", "RENDVI"]

            for key, month_data in combined_input.items():
                lon, lat = map(float, key.split(","))
                row = {"Lon": lon, "Lat": lat}

                for month, features in month_data.items():
                    for feat in all_features:
                        col_name = f"{feat}_{month}"
                        row[col_name] = features.get(feat, 0)
                rows.append(row)

            df = pd.DataFrame(rows)
            await send_ws_update(channel_layer, "progress", startProgress=65, endProgress=90, message="Time series data prepared. Running Deep Learning Model...")

            # Step 4: Run deep learning model (65–90%)
            output_data = await get_crop_prediction(df)
            await send_ws_update(channel_layer, "progress", startProgress=90, endProgress=98, message="Model predictions obtained. Generating features and metrics...")

            # Step 5: Generate features and calculate metrics (90–98%)
            output_lookup = {f"{item['lon']},{item['lat']}": item["prediction"] for item in output_data}
            coordinates = list(combined_input.keys())
            features = []
            ragi_count = 0
            non_ragi_count = 0

            for key in coordinates:
                lon, lat = map(float, key.split(','))
                
                prediction = output_lookup.get(key, 0)
                if key not in output_lookup:
                    print(f"Warning: No matching prediction found for coordinates ({lon}, {lat})")
                
                if prediction == 1:
                    ragi_count += 1
                else:
                    non_ragi_count += 1
                
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "geodesic": False,
                        "coordinates": [lon, lat]
                    },
                    "properties": {
                        "prediction": prediction
                    }
                })

            total_predictions = ragi_count + non_ragi_count
            ragi_coverage = (ragi_count / total_predictions * 100) if total_predictions > 0 else 0
            non_ragi_coverage = (non_ragi_count / total_predictions * 100) if total_predictions > 0 else 0

            # Step 6: Assemble final output (98–100%)
            output = {
                "map": {
                    "type": "FeatureCollection",
                    "features": features,
                },
                "metrics": {
                    "ragiCoverage": round(ragi_coverage, 2),
                    "nonRagiCoverage": round(non_ragi_coverage, 2),
                }
            }

            await send_ws_update(channel_layer, "progress", startProgress=98, endProgress=100, message="Output generated successfully.")

            return {"output": output, "results": result}

    except httpx.RequestError as e:
        print(f"Unexpected Part 1: {str(e)}")
        await send_ws_update(channel_layer, "error", message=f"Error fetching data: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Unexpected Part 2: {str(e)}")
        await send_ws_update(channel_layer, "error", message=f"Unexpected error: {str(e)}")
        return {"error": str(e)}

@csrf_exempt
def fetch_s2_and_s1_indices(request):
    if request.method != "POST":
        return JsonResponse({"message": "Send a POST request with GeoJSON"}, status=405)

    try:
        req = json.loads(request.body.decode("utf-8"))
        geojson_data = req['geojson']
        flag = req['flag']
        startDate = req['startDate']
        endDate = req['endDate']

    except json.JSONDecodeError as e:
        return JsonResponse({"error": "Invalid GeoJSON data", "detail": str(e)}, status=400)

    try:
        results = async_to_sync(fetch_s2_and_s1_indices_async)(geojson_data, startDate, endDate, flag)
        return JsonResponse(results)
    except Exception as e:
        print(e)
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

async def get_crop_prediction(combined_input):
    """
    Calls the FastAPI microservice to get predictions asynchronously.
    :param combined_input: DataFrame with features
    :return: JSON response with predictions
    """
    url = 'http://localhost:6000/crop-prediction'
    payload = combined_input.to_dict(orient='records')  # Convert DataFrame to list of dicts

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            return response.json()  # Returns: [{lon, lat, prediction}, ...]
    except httpx.RequestError as e:
        print(f"Prediction microservice call failed: {e}")
        await send_ws_update(get_channel_layer(), "error", message=f"Prediction microservice failed: {str(e)}")
        return {"error": str(e)}

@csrf_exempt
def generate_mock_results(request):
    if request.method == "POST":
        geojson = json.loads(request.body.decode("utf-8"))
        result = async_to_sync(mock_results)(geojson)
        return JsonResponse(result)
    return JsonResponse({"error": "Only POST method allowed"}, status=405)

async def mock_results(geojson):
    url = "http://localhost:4000/mock-results"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, json=geojson, headers={"Content-Type": "application/json"})
        return response.json()
import json
import asyncio
import httpx
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync
from datetime import datetime, timedelta
from channels.layers import get_channel_layer

def home_view(request):
    return JsonResponse({"message": "Welcome to the Crop Mapping API!"})

def test_view(request):
    return JsonResponse({"message": "Test route working!"})

async def send_ws_update(channel_layer, update_type, startProgress=None, endProgress=None, message=None):
    data = {"type": update_type}
    if(endProgress != None):
        data["endProgress"] = endProgress
    if(startProgress != None):
        data["startProgress"] = startProgress
    data["message"] = message
    await channel_layer.group_send(
        "satellite_progress",
        {
            "type": "send_notification",
            "message": data
        }
    )

async def fetch_s2_and_s1_indices_async(geojson_data):
    channel_layer = get_channel_layer()
    url_s1 = "http://localhost:4000/extract-s1-parameters"
    url_s2 = "http://localhost:4000/extract-s2-parameters"
    start_date = (datetime.today() - timedelta(days=15)).strftime("%Y-%m-%d")
    end_date = datetime.today().strftime("%Y-%m-%d")

    try:
        # Step 2: Fetching Sentinel-1 and Sentinel-2 Data (starts at 10% from frontend)
        await send_ws_update(channel_layer, "progress", startProgress=10, endProgress=10, message="Initiating Data Fetch...")
        results = {}
        lock = asyncio.Lock()

        async def fetch_and_update(source, url):
            async with httpx.AsyncClient(timeout=60) as client:
                payload = {"geojson": geojson_data, "start_date": start_date, "end_date": end_date}
                response = await client.post(url, json=payload, headers={"Content-Type": "application/json"})

            async with lock:  
                results[source] = response
                total_received = len(results)  
                sensor_name = "Sentinel-1" if source.upper() == "S1" else "Sentinel-2"

                if total_received == 1:  
                    await send_ws_update(channel_layer, "progress", startProgress=10, endProgress=25, message=f"{sensor_name} Data Retrieved. Awaiting other data...")
                elif total_received == 2:
                    await send_ws_update(channel_layer, "progress", startProgress=25, endProgress=40, message="All Satellite Data Retrieved. Combining Satellite Data...")

        await asyncio.gather(fetch_and_update("s1", url_s1), fetch_and_update("s2", url_s2))

        # Step 3: Combining Sentinel-1 and Sentinel-2 
        await asyncio.sleep(10)

        # Step 4: Running DL Model
        await send_ws_update(channel_layer, "progress", startProgress=40, endProgress=50, message="Running Deep Learning Model For Mapping...")
        await asyncio.sleep(10)

        # Step 5: Refining Data
        await send_ws_update(channel_layer, "progress", startProgress=50, endProgress=90, message="Refining Data...")
        await asyncio.sleep(10)

        return {
            source: response.json() if response.status_code == 200 else 
                   {"error": f"{source.upper()} microservice call failed", "status_code": response.status_code}
            for source, response in results.items()
        }

    except httpx.RequestError as e:
        await send_ws_update(channel_layer, "error", message=f"Error fetching data: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        await send_ws_update(channel_layer, "error", message=f"Unexpected error: {str(e)}")
        return {"error": str(e)}

@csrf_exempt
def fetch_s2_and_s1_indices(request):
    if request.method != "POST":
        return JsonResponse({"message": "Send a POST request with GeoJSON"}, status=405)

    try:
        geojson_data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as e:
        return JsonResponse({"error": "Invalid GeoJSON data", "detail": str(e)}, status=400)

    try:
        results = async_to_sync(fetch_s2_and_s1_indices_async)(geojson_data)
        return JsonResponse(results, safe=False)
    except Exception as e:
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)
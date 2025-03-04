import json
import asyncio
import httpx, time
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync

def home_view(request):
    return JsonResponse({"message": "Welcome to the Crop Mapping API!"})

def test_view(request):
    return JsonResponse({"message": "Test route working!"})

async def fetch_s2_and_s1_indices_async(geojson_data):
    url_s2 = "http://localhost:4000/extract-s2-parameters"
    url_s1 = "http://localhost:4000/extract-s1-parameters"
    start_date = "2025-02-15"
    end_date = "2025-03-01"

    async def fetch_s2():
        async with httpx.AsyncClient(timeout=30) as client:
            print(f"S2 request ", time.time())
            payload = {"geojson": geojson_data, "start_date": start_date, "end_date": end_date}
            headers = {"Content-Type": "application/json"}
            response = await client.post(url_s2, json=payload, headers=headers)
            return "s2", response

    async def fetch_s1():
        async with httpx.AsyncClient(timeout=30) as client:
            print(f"S1 request ", time.time())
            payload = {"geojson": geojson_data, "start_date": start_date, "end_date": end_date}
            headers = {"Content-Type": "application/json"}
            response = await client.post(url_s1, json=payload, headers=headers)
            return "s1", response

    try:
        s2_result, s1_result = await asyncio.gather(fetch_s2(), fetch_s1())
        results = {}
        for source, response in [s2_result, s1_result]:
            if response.status_code == 200:
                results[source] = response.json()
            else:
                results[source] = {"error": f"{source.upper()} microservice call failed", "status_code": response.status_code}

        return results

    except httpx.RequestError as e:
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

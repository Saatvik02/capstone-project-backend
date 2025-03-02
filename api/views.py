from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import httpx
from asgiref.sync import async_to_sync

def home_view(request):
    return JsonResponse({"message": "Welcome to the Crop Mapping API!"})

def test_view(request):
    return JsonResponse({"message": "Test route working!"})

@csrf_exempt
def fetch_indices(request):
    if request.method != "POST":
        return JsonResponse({"message": "Send a POST request with GeoJSON"}, status=405)

    geojson_data = json.loads(request.body.decode("utf-8"))
    url = "http://localhost:4000/extract-s2-parameters"
    start_date = "2025-02-15"
    end_date = "2025-03-01"
    payload = {'geojson': geojson_data, 'start_date': start_date, 'end_date': end_date}
    headers = {'Content-Type': 'application/json'}

    async def make_request():
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload, headers=headers)
            print("response", response)
            return response

    try:
        response = async_to_sync(make_request) ()
        if response.status_code == 200:
            return JsonResponse(response.json(), safe=False)
        else:
            return JsonResponse({'error': 'Microservice call failed', 'status_code': response.status_code}, status=response.status_code)

    except httpx.RequestError as e:
        return JsonResponse({'error': str(e)}, status=500)

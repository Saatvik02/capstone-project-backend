from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import ee
from api.gee_init import initialize_gee

from django.http import JsonResponse

def home_view(request):
    return JsonResponse({"message": "Welcome to the Crop Mapping API!"})

def test_view(request):
    return JsonResponse({"message": "Test route working!"})

initialize_gee()

@csrf_exempt
def fetch_band_values(request):
    if request.method == "POST":
        try:
            geojson_geometry = json.loads(request.body)


            if not geojson_geometry:
                return JsonResponse({"error": "No geometry provided"}, status=400)

            region = ee.Geometry(geojson_geometry)

            image = ee.ImageCollection("COPERNICUS/S2") \
                .filterBounds(region) \
                .filterDate("2024-01-01", "2024-02-01") \
                .median()

            pixel_values = image.sample(
                region=region,
                scale=10,
                numPixels=1000,
                geometries=True
            ).getInfo()

            return JsonResponse({"pixels": pixel_values}, safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"message": "Send a POST request with GeoJSON"})

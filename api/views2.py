from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json, ee, base64, requests
from api.gee_init import initialize_gee
from io import BytesIO

# Configuration constants
CLOUD_PROB_THRESHOLD = 50
MAX_CLOUD_PERCENTAGE = 80
SAMPLE_PIXEL_COUNT = 1000
DATE_START = "2024-01-01"
DATE_END = "2024-02-01"

def home_view(request):
    return JsonResponse({"message": "Welcome to the Crop Mapping API!"})

def test_view(request):
    return JsonResponse({"message": "Test route working!"})

def mask_clouds(image):
    cloud_prob = ee.Image(image.get('s2cloudless')).select('probability')
    is_cloud = cloud_prob.gt(CLOUD_PROB_THRESHOLD)
    image = image.addBands(cloud_prob.rename('clouds'))
    return image.updateMask(is_cloud.Not())

def add_shadow_mask(image):
    not_water = image.select('SCL').neq(6)
    dark_pixels = image.select('B8').lt(0.15 * 10000).multiply(not_water).rename('dark_pixels')
    shadow_azimuth = ee.Number(90).subtract(ee.Number(image.get('MEAN_SOLAR_AZIMUTH_ANGLE')))
    
    cld_proj = image.select('clouds') \
        .directionalDistanceTransform(shadow_azimuth, 10) \
        .reproject(image.select(0).projection(), scale=100) \
        .select('distance') \
        .mask().rename('cloud_transform')
    
    shadows = cld_proj.multiply(dark_pixels).rename('shadows')
    return image.addBands(ee.Image([dark_pixels, cld_proj, shadows]))

def image_to_base64(image, region):
    try:
        url = image.getThumbUrl({
            'bands': ['B4', 'B3', 'B2'],
            'min': 0,
            'max': 2500,
            'gamma': 1.1,
            'region': region
        })
        response = requests.get(url, timeout=10)  # Add timeout
        with BytesIO(response.content) as img:
            return base64.b64encode(img.getvalue()).decode()
    except requests.RequestException as e:
        raise Exception(f"Image conversion failed: {str(e)}")

@csrf_exempt
def fetch_band_values(request):
    if request.method != "POST":
        return JsonResponse({"message": "Send a POST request with GeoJSON"}, status=405)

    try:
        # Initialize GEE with error handling
        try:
            ee.Initialize()
        except ee.EEException:
            initialize_gee()

        geojson_data = json.loads(request.body.decode("utf-8"))
        geojson_geometry = geojson_data.get("geometry")
        
        if not geojson_geometry:
            return JsonResponse({"error": "No geometry provided"}, status=400)
            
        region = ee.Geometry(geojson_geometry)

        # Load and process imagery
        s2_sr_col = ee.ImageCollection("COPERNICUS/S2_SR") \
            .filterBounds(region) \
            .filterDate(DATE_START, DATE_END) \
            .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', MAX_CLOUD_PERCENTAGE))
            
        s2_cloudless_col = ee.ImageCollection("COPERNICUS/S2_CLOUD_PROBABILITY") \
            .filterBounds(region) \
            .filterDate(DATE_START, DATE_END)
            
        joined = ee.ImageCollection(ee.Join.saveFirst('s2cloudless').apply({
            'primary': s2_sr_col,
            'secondary': s2_cloudless_col,
            'condition': ee.Filter.equals(leftField='system:index', rightField='system:index')
        }))

        processed_images = joined.map(mask_clouds).map(add_shadow_mask)
        clean_image = processed_images.median().clip(region)

        # image = ee.ImageCollection("COPERNICUS/S2") \
            #     .filterBounds(region) \
            #     .filterDate("2024-01-01", "2024-02-01") \
            #     .median()

        base64_img = image_to_base64(clean_image, region)
        
        pixel_values = clean_image.sample(
            region=region,
            scale=10,
            numPixels=SAMPLE_PIXEL_COUNT,
            geometries=True
        ).getInfo()

        return JsonResponse({"image": base64_img, "pixels": pixel_values}, safe=False)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except ee.EEException as e:
        return JsonResponse({"error": f"Earth Engine error: {str(e)}"}, status=500)
    except Exception as e:
        return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)
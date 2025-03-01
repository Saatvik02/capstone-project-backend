import ee
import os

# Define the service account and key file path
SERVICE_ACCOUNT = "gee-remotesensing-cropmapping@remote-sensing-crop-mapping.iam.gserviceaccount.com"
KEY_FILE = os.path.join(os.path.dirname(__file__), "../utils/gcp-key.json")  

def initialize_gee():
    try:
        credentials = ee.ServiceAccountCredentials(SERVICE_ACCOUNT, KEY_FILE)
        ee.Initialize(credentials)
        print("Google Earth Engine initialized successfully!")
    except Exception as e:
        print("Error initializing Earth Engine:", str(e))

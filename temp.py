import requests
import pandas as pd
import json


df = pd.read_csv('data.csv')
payload = df.to_dict(orient='records')

# API endpoint
url = 'http://localhost:6000/crop-prediction-psetae'

# Send request
try:
    response = requests.post(url, json=payload)
    response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
    
    # Save the response to a JSON file
    with open('response.json', 'w') as f:
        json.dump(response.json(), f, indent=4)
    
    print("✅ Response saved to 'response.json'")

except requests.exceptions.RequestException as e:
    print(f"❌ Request failed: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

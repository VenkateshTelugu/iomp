import requests

def calculate_sunlight(lat, lon):
    # NASA Power API for sunlight data
    api_url = f"https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": "ALLSKY_SFC_SW_DWN",
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": "20240101",
        "end": "20240101",
        "format": "JSON"
    }

    response = requests.get(api_url, params=params)
    data = response.json()

    sunlight_hours = data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
    return sunlight_hours

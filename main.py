from flask import Flask, render_template, jsonify
import requests
import json
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2


app = Flask(__name__)

# San Francisco coordinates
SF_LAT = 37.7749
SF_LON = -122.4194
RADIUS_KM = 200  # Alert radius in kilometers


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula (in km)"""
    R = 6371  # Earth's radius in kilometers
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance


def get_earthquake():
    """Fetch recent earthquakes near San Francisco from USGS API"""
    try:
        # USGS FDSN Event Web Service - Query for last 24 hours
        base_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
        
        # Get earthquakes from the last 24 hours
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        
        params = {
            'format': 'geojson',
            'starttime': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'endtime': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'minlatitude': SF_LAT - 2,  # Roughly 200km box
            'maxlatitude': SF_LAT + 2,
            'minlongitude': SF_LON - 2,
            'maxlongitude': SF_LON + 2,
            'minmagnitude': 2.0  # Only show magnitude 2.0+
        }
        
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Filter earthquakes by distance from San Francisco
        nearby_earthquakes = []
        for feature in data.get('features', []):
            coords = feature['geometry']['coordinates']
            lon, lat = coords[0], coords[1]
            
            distance = calculate_distance(SF_LAT, SF_LON, lat, lon)
            
            if distance <= RADIUS_KM:
                properties = feature['properties']
                earthquake_info = {
                    'magnitude': properties.get('mag'),
                    'place': properties.get('place'),
                    'time': datetime.fromtimestamp(properties.get('time') / 1000).strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'distance_km': round(distance, 1),
                    'depth_km': round(coords[2], 1),
                    'url': properties.get('url'),
                    'alert': properties.get('alert'),
                    'felt': properties.get('felt'),
                    'tsunami': properties.get('tsunami')
                }
                nearby_earthquakes.append(earthquake_info)
        
        # Sort by magnitude (highest first)
        nearby_earthquakes.sort(key=lambda x: x['magnitude'] if x['magnitude'] else 0, reverse=True)
        
        return nearby_earthquakes
    
    except Exception as e:
        print(f"Error fetching earthquake data: {e}")
        return []


@app.route("/") 
def index():
    return render_template('index.html')


@app.route("/api/earthquakes")
def get_earthquakes_api():
    """API endpoint to get current earthquake data"""
    earthquakes = get_earthquake()
    return jsonify({
        'count': len(earthquakes),
        'earthquakes': earthquakes,
        'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    })


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)


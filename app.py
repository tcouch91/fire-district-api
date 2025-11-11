import geopandas as gpd
from shapely.geometry import Point
from flask import Flask, request, jsonify
from flask_cors import CORS
from geopy.geocoders import ArcGIS
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

app = Flask(__name__)
CORS(app)

print("Loading GeoJSON data...")
try:
    gdf = gpd.read_file('fire_districts.geojson')
    gdf = gdf.to_crs(epsg=4326)
    print("GeoJSON loaded successfully.")
except Exception as e:
    print(f"Error loading GeoJSON: {e}")
    gdf = None

geolocator = ArcGIS(user_agent="fire_district_locator", timeout=10)

def find_district(lat, lon):
    """
    Checks a point (lat, lon) against the loaded GeoDataFrame.
    """
    if gdf is None:
        return "GeoJSON data not loaded."

    point = Point(lon, lat)
    
    matches = gdf[gdf.geometry.contains(point)]
    
    if not matches.empty:
        try:
            district_name = matches.iloc[0]['fire_ori_desc'] 
            return str(district_name)
        except KeyError:
            return "Found district, but couldn't get 'NAME'. Check 'app.py' column setting."
    else:
        return "Address not found within any fire district."

@app.route('/check_address', methods=['POST'])
def check_address():
    """
    API endpoint that receives an address, geocodes it,
    and checks it against the fire districts.
    """
    data = request.json
    if not data or 'address' not in data:
        return jsonify({'error': 'No address provided'}), 400
    
    address = data['address']
    
    try:
        location = geolocator.geocode(address, timeout=10)
        
        if location:
            lat, lon = location.latitude, location.longitude
            
            district_name = find_district(lat, lon)
            
            return jsonify({
                'found': True,
                'address': address,
                'latitude': lat,
                'longitude': lon,
                'district': district_name
            })
        else:
            return jsonify({
                'found': False,
                'address': address,
                'district': 'Could not find a location for that address.'
            }), 404
            
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"Geocoding service error: {e}")
        return jsonify({'error': 'Geocoding service is unavailable. Please try again later.'}), 503
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
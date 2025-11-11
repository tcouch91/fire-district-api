import geopandas as gpd
from shapely.geometry import Point
from flask import Flask, request, jsonify
from flask_cors import CORS
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

# --- Configuration ---

# Initialize Flask App
app = Flask(__name__)
# Enable CORS to allow your GitHub Pages site to call this API
CORS(app)

# Load your GeoJSON file into a GeoDataFrame.
# This happens ONCE when the app starts, making it fast.
print("Loading GeoJSON data...")
try:
    gdf = gpd.read_file('fire_districts.geojson')
    # IMPORTANT: Ensure the GeoDataFrame is using the standard WGS 84 (EPSG:4326)
    # CRS, which is what geocoders typically return.
    gdf = gdf.to_crs(epsg=4326)
    print("GeoJSON loaded successfully.")
except Exception as e:
    print(f"Error loading GeoJSON: {e}")
    gdf = None

# Initialize a geocoder.
# Nominatim is free but has strict rate limits and is not for heavy commercial use.
# For a production app, consider Mapbox, Google Maps, or another provider.
geolocator = Nominatim(user_agent="fire_district_locator")

# --- Helper Function ---

def find_district(lat, lon):
    """
    Checks a point (lat, lon) against the loaded GeoDataFrame.
    """
    if gdf is None:
        return "GeoJSON data not loaded."

    point = Point(lon, lat)
    
    # Find which polygon contains the point
    # .contains() checks if the polygon in each row contains the point
    matches = gdf[gdf.geometry.contains(point)]
    
    if not matches.empty:
        # We found at least one match.
        # --- IMPORTANT ---
        # You MUST change 'NAME' to the actual column in your GeoJSON
        # that holds the district name (e.g., 'DISTRICT_ID', 'FireArea', 'Name').
        # Open your .geojson to find the correct column name.
        try:
            # Get the name from the *first* match
            district_name = matches.iloc[0]['fire_ori_desc'] 
            return str(district_name)
        except KeyError:
            return "Found district, but couldn't get 'NAME'. Check 'app.py' column setting."
    else:
        # No polygon contained the point
        return "Address not found within any fire district."

# --- API Endpoint ---

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
        # 1. Geocode the address
        location = geolocator.geocode(address)
        
        if location:
            lat, lon = location.latitude, location.longitude
            
            # 2. Find the district
            district_name = find_district(lat, lon)
            
            # 3. Return the result
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
        print(f"Geocoding error: {e}")
        return jsonify({'error': 'Geocoding service is unavailable. Please try again later.'}), 503
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500

# --- Run the App ---

if __name__ == '__main__':
    # You'll use a production server (like Gunicorn) to run this,
    # but this is fine for local testing.
    app.run(debug=True, port=5000)
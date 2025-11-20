import geopandas as gpd
from shapely.geometry import Point
from flask import Flask, request, jsonify
from flask_cors import CORS
from geopy.geocoders import ArcGIS
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

url = 'https://services1.arcgis.com/2AGLxyiJoNiVHKwq/arcgis/rest/services/Fire%20Service%20Provider%20ORI%20%20(%20Boundary%20)/FeatureServer/0/query?where=1%3D1&objectIds=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&resultType=none&distance=0.0&units=esriSRUnit_Meter&outDistance=&relationParam=&returnGeodetic=false&outFields=*&returnGeometry=true&returnCentroid=false&returnEnvelope=false&featureEncoding=esriDefault&multipatchOption=xyFootprint&maxAllowableOffset=&geometryPrecision=&outSR=&defaultSR=&datumTransformation=&applyVCSProjection=false&returnIdsOnly=false&returnUniqueIdsOnly=false&returnCountOnly=false&returnExtentOnly=false&returnQueryGeometry=false&returnDistinctValues=false&cacheHint=false&collation=&orderByFields=&groupByFieldsForStatistics=&returnAggIds=false&outStatistics=&having=&resultOffset=&resultRecordCount=&returnZ=false&returnM=false&returnTrueCurves=false&returnExceededLimitFeatures=true&quantizationParameters=&sqlFormat=none&f=pgeojson&token='

deparments = {'Bethany':'Bethany-Santiago Fire Dept',
            'Bethel':'Bethel Fire Dept',
            'Bethesda':'Bethesda Fire Dept',
            'Bullock Creek':'Bullocks Creek Fire Dept',
            'Clover':'Clover Fire Dept',
            'Flint Hill':'Flint Hill Fire Dept',
            'Fort Mill':'Fort Mill Fire Dept',
            'Hickory Grove':'Hickory Grove Fire Dept',
            'Lesslie':'Lesslie Fire Dept',
            'McConnells':'McConnells Fire Dept',
            'Newport':'Newport Fire Dept',
            'Oakdale':'Oakdale Fire Dept',
            'Riverview':'Riverview Fire Dept',
            'Rock Hill':'Rock Hill Fire Dept',
            'Sharon':'Sharon Fire Dept',
            'Smyrna':'Smyrna Fire Dept',
            'Tega Cay':'Tega Cay Fire Dept',
            'York':'York Fire Dept'}

app = Flask(__name__)
CORS(app, origins=["https://riverviewfire.org","http://127.0.0.1:5500"])

print("Loading GeoJSON data...")
try:
    # Pull data from ArcGIS
    gdf = gpd.read_file(url)

    # Remap deparment names
    gdf['fire_ori_desc'] = gdf['fire_ori_desc'].map(deparments)

    # Drop unnecessary columns and rename for clarity
    cols_to_drop = [col for col in gdf.columns if col not in ['fire_ori_desc','geometry']]
    gdf.drop(columns=cols_to_drop, inplace=True)
    gdf.rename(columns={'fire_ori_desc':'fire_service_provider'}, inplace=True)
    
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
            district_name = matches.iloc[0]['fire_service_provider'] 
            return str(district_name)
        except KeyError:
            return "Found district, but couldn't get 'NAME'. Check 'app.py' column setting."
    else:
        return "Address not found within any fire district. Data are for York County, SC only."

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

            geocoded_address = location.address
            
            return jsonify({
                'found': True,
                'address': address,
                'geocoded_address': geocoded_address,
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
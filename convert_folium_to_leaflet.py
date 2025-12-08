"""
Exact Folium Map Replica in Leaflet.js
This script converts all your Folium data layers to web-friendly formats
"""

import geopandas as gpd
import pandas as pd
import json
import numpy as np
from pathlib import Path

def convert_all_layers():
    """Convert all map layers to GeoJSON/JSON for Leaflet"""
    
    print("="*60)
    print("CONVERTING FOLIUM MAP DATA TO LEAFLET FORMAT")
    print("="*60)
    
    output_data = {
        'config': {
            'nm_center': [34.5199, -105.8701],
            'default_zoom': 6,
            'distribution_centers': [
                {'lat': 39.09820436455732, 'lon': -104.78195183701729, 'name': 'Denver DC'},
                {'lat': 33.54855180837709, 'lon': -112.00158827551459, 'name': 'Phoenix DC'}
            ],
            'dc_radius_km': 300 * 1.609  # 300 miles in km
        }
    }
    
    # 1. STATE BOUNDARY
    try:
        print("\n1. Converting State Boundary...")
        nm_boundary = gpd.read_file('00_data/cb_2018_35_tract_500k/cb_2018_35_tract_500k.shp')
        nm_boundary = nm_boundary[nm_boundary['STATEFP'] == '35']
        nm_boundary_dissolved = nm_boundary.dissolve(by=None)
        
        # Ensure correct CRS
        if nm_boundary_dissolved.crs and nm_boundary_dissolved.crs.to_string() != 'EPSG:4326':
            nm_boundary_dissolved = nm_boundary_dissolved.to_crs(epsg=4326)
        
        nm_boundary_dissolved.to_file('nm_boundary.geojson', driver='GeoJSON')
        print("   ✓ nm_boundary.geojson created")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 2. HIGHWAY/STREET NETWORK
    try:
        print("\n2. Converting Highway Network...")
        highway_data = gpd.read_file('extracted_osm_locations_linestring.shp')
        
        # Keep only essential columns (matching your Folium code)
        highway_data = highway_data[['id', 'geometry']]
        
        # Simplify geometries
        highway_data['geometry'] = highway_data['geometry'].simplify(
            tolerance=0.0001, preserve_topology=True
        )
        
        highway_data.to_file('highways.geojson', driver='GeoJSON')
        print(f"   ✓ highways.geojson created ({len(highway_data)} features)")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 3. FAST FOOD LOCATIONS (MarkerCluster)
    try:
        print("\n3. Converting Fast Food Locations...")
        ff_df = pd.read_csv('nm_fast_food_data.csv')
        
        # Keep only essential columns (matching your Folium code)
        ff_df = ff_df[['Name', 'Latitude', 'Longitude', 'Rating']]
        
        ff_data = []
        for _, row in ff_df.iterrows():
            ff_data.append({
                'lat': row['Latitude'],
                'lon': row['Longitude'],
                'name': row.get('Name', 'Unknown'),
                'rating': row.get('Rating', None) if pd.notna(row.get('Rating')) else None
            })
        
        with open('fast_food_locations.json', 'w') as f:
            json.dump(ff_data, f)
        
        print(f"   ✓ fast_food_locations.json created ({len(ff_data)} locations)")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 4. UNIVERSITIES/MALLS/POIS
    try:
        print("\n4. Converting POI Locations...")
        poi_gdf = gpd.read_file('extracted_osm_point_locations.shp')
        
        # Keep only essential columns
        poi_gdf = poi_gdf[['name', 'geometry']]
        
        # Convert polygons to centroids (matching your Folium code)
        geometry_types = poi_gdf.geometry.geom_type
        is_areal = geometry_types.isin(['Polygon', 'MultiPolygon'])
        poi_gdf.loc[is_areal, 'geometry'] = poi_gdf.loc[is_areal, 'geometry'].centroid
        
        poi_data = []
        for _, row in poi_gdf.iterrows():
            poi_data.append({
                'lat': row.geometry.y,
                'lon': row.geometry.x,
                'name': row.get('name', 'POI')
            })
        
        with open('poi_locations.json', 'w') as f:
            json.dump(poi_data, f)
        
        print(f"   ✓ poi_locations.json created ({len(poi_data)} locations)")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 5. TRAFFIC COUNT STATIONS
    try:
        print("\n5. Converting Traffic Count Stations...")
        traffic_df = pd.read_excel('00_Data/tcds_list-2.xlsx', skiprows=1)
        traffic_df.columns = ['Loc_ID', 'County', 'Functional_Class', 'Rural_Urban', 
                             'On', 'LRS_Loc_Pt', 'Latitude', 'Longitude', 
                             'TrafficCount', 'Latest_Date']
        
        traffic_df = traffic_df.dropna(subset=['Latitude', 'Longitude', 'TrafficCount'])
        
        traffic_data = []
        for _, row in traffic_df.iterrows():
            traffic_data.append({
                'lat': row['Latitude'],
                'lon': row['Longitude'],
                'count': int(row['TrafficCount']),
                'loc_id': row.get('Loc_ID', '')
            })
        
        with open('traffic_stations.json', 'w') as f:
            json.dump(traffic_data, f)
        
        print(f"   ✓ traffic_stations.json created ({len(traffic_data)} stations)")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 6. TRAFFIC VOLUME ON ROADS
    try:
        print("\n6. Converting Road Traffic Volume...")
        roads_gdf = gpd.read_file('results_interpolated_v3_MERGED_1000m_100s.shp')
        
        # Keep only essential columns (matching your Folium code)
        roads_gdf = roads_gdf[['mean_traff', 'geometry']]
        
        # Rename to match expected name
        roads_gdf = roads_gdf.rename(columns={'mean_traff': 'mean_traffic'})
        
        # Simplify for web performance
        print("   Simplifying geometries...")
        roads_gdf['geometry'] = roads_gdf['geometry'].simplify(
            tolerance=0.0001, preserve_topology=True
        )
        
        # Keep all roads - filtering will be done in JavaScript
        # But we can limit total count for performance
        print(f"   Total roads before limit: {len(roads_gdf)}")
        
        # Sort by traffic and keep top roads for performance
        if len(roads_gdf) > 10000:
            roads_gdf = roads_gdf.nlargest(10000, 'mean_traffic')
            print(f"   Limited to top 10000 roads by traffic")
        
        roads_gdf.to_file('road_traffic.geojson', driver='GeoJSON')
        
        print(f"   ✓ road_traffic.geojson created ({len(roads_gdf)} road segments)")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 7. DIVERSITY DATA (Choropleth)
    try:
        print("\n7. Converting Diversity Data...")
        diversity_gdf = gpd.read_file('merged_race_data.geojson')
        
        # Simplify polygons
        diversity_gdf['geometry'] = diversity_gdf['geometry'].simplify(
            tolerance=0.01, preserve_topology=True
        )
        
        # Keep essential columns
        cols_to_keep = ['Total:—Estimate', 'geometry']
        if 'Total:—Estimate' in diversity_gdf.columns:
            diversity_gdf = diversity_gdf[cols_to_keep]
            diversity_gdf.to_file('diversity_data.geojson', driver='GeoJSON')
            print(f"   ✓ diversity_data.geojson created ({len(diversity_gdf)} zones)")
        else:
            print("   ✗ Column 'Total:—Estimate' not found")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 8. SUITABILITY HEATMAP DATA
    try:
        print("\n8. Preparing Suitability Score Data...")
        # This will need to be calculated by your scoring function
        # For now, create a placeholder structure
        
        print("   ⚠ Suitability scores need to be calculated from your add_suitability_layer function")
        print("   This will be handled by the Leaflet map using your weights")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Save configuration
    with open('map_config.json', 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print("\n" + "="*60)
    print("CONVERSION COMPLETE!")
    print("="*60)
    print("\nFiles created:")
    print("  • nm_boundary.geojson - State boundary")
    print("  • highways.geojson - Street network")
    print("  • fast_food_locations.json - FF locations")
    print("  • poi_locations.json - Universities/Malls")
    print("  • traffic_stations.json - Traffic count stations")
    print("  • road_traffic.geojson - Road traffic volumes")
    print("  • diversity_data.geojson - Diversity zones")
    print("  • map_config.json - Map configuration")
    print("\nNext step: Run the Leaflet HTML file")

if __name__ == '__main__':
    convert_all_layers()
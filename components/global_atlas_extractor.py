"""
GlobalBuildingAtlas WFS Integration
Fetches building data from the GlobalBuildingAtlas WFS service.

Author: Building Generator Integration
Date: December 2025
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import logging
from typing import Tuple, Optional, Dict, Any
import geopandas as gpd
from shapely.geometry import shape
from pyproj import Transformer

logger = logging.getLogger(__name__)


class GlobalAtlasExtractor:
    """
    Extract building footprints and heights from GlobalBuildingAtlas WFS service.
    
    The service provides:
    - Building footprints (polygons)
    - Building heights (meters)
    - Height uncertainty/variance
    - Source information (OSM)
    - Region codes
    """
    
    def __init__(self):
        self.wfs_url = "https://tubvsig-so2sat-vm1.srv.mwn.de/geoserver/ows?"
        self.layer_name = "global3D:lod1_global"
        
        # Transformer from EPSG:3857 (Web Mercator) to EPSG:4326 (WGS84)
        # The WFS returns data in EPSG:3857, we need WGS84 for compatibility
        self.transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    
    def extract_buildings_by_bbox(
        self, 
        top_left: Tuple[float, float], 
        bottom_right: Tuple[float, float],
        output_file: str,
        extrafields: bool = False,
        max_features: Optional[int] = None,
        cancel_event=None
    ) -> Dict[str, Any]:
        """
        Extract buildings within a bounding box from GlobalBuildingAtlas.
        
        Args:
            top_left: (latitude, longitude) of top-left corner
            bottom_right: (latitude, longitude) of bottom-right corner
            output_file: Path to save GeoJSON output
            extrafields: If True, add OSM classification fields (building, man_made, etc.)
            max_features: Maximum number of features to retrieve (None = all)
            cancel_event: Threading event to cancel operation
        
        Returns:
            Dictionary with:
                - count: Number of buildings extracted
                - output_file: Path to saved file
                - bbox_used: Bounding box coordinates used
        
        Raises:
            Exception: If extraction fails
        
        Note:
            - Heights are returned in METERS (consistent with Google buildings format)
            - Coordinates are transformed from EPSG:3857 to EPSG:4326 automatically
        """
        lat1, lon1 = top_left
        lat2, lon2 = bottom_right
        
        # Create bbox for WFS (lon_min, lat_min, lon_max, lat_max)
        lon_min = min(lon1, lon2)
        lon_max = max(lon1, lon2)
        lat_min = min(lat1, lat2)
        lat_max = max(lat1, lat2)
        
        logger.info(f"Fetching buildings from GlobalBuildingAtlas")
        logger.info(f"  BBox: ({lon_min}, {lat_min}) to ({lon_max}, {lat_max})")
        logger.info(f"  Layer: {self.layer_name}")
        
        # Build WFS parameters
        params = {
            'service': 'WFS',
            'version': '2.0.0',
            'request': 'GetFeature',
            'typeName': self.layer_name,
            'outputFormat': 'application/json',
            'srsName': 'EPSG:4326',  # Request in WGS84
            'bbox': f'{lon_min},{lat_min},{lon_max},{lat_max},EPSG:4326'
        }
        
        if max_features is not None:
            params['count'] = max_features
        
        # Try up to 3 times with retry on connection errors
        max_retries = 3
        data = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries}...")
                    import time
                    time.sleep(2 * attempt)  # Wait 2, 4 seconds between retries
                
                if cancel_event and cancel_event.is_set():
                    logger.info("Extraction cancelled by user")
                    return {'count': 0, 'cancelled': True}
                
                # Make request with custom headers and retry configuration
                logger.info("Sending WFS request...")
                headers = {
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip, identity',  # Prefer gzip, avoid chunked
                    'Connection': 'close',  # Don't keep connection alive
                }
                
                # Create a session with built-in retry logic for connection errors
                session = requests.Session()
                retry_strategy = Retry(
                    total=0,  # We handle retries manually at higher level
                    connect=2,  # Retry connection errors
                    read=2,  # Retry read errors
                    status_forcelist=[500, 502, 503, 504],  # Retry on server errors
                    backoff_factor=0.5
                )
                adapter = HTTPAdapter(max_retries=retry_strategy)
                session.mount("http://", adapter)
                session.mount("https://", adapter)
                
                try:
                    response = session.get(
                        self.wfs_url, 
                        params=params, 
                        headers=headers,
                        timeout=(30, 180),  # (connect timeout, read timeout)
                        stream=True  # Stream to manually control reading
                    )
                    
                    response.raise_for_status()
                    
                    # Manually read content to avoid chunked encoding issues
                    logger.debug("Reading response content manually...")
                    content_bytes = bytearray()
                    
                    try:
                        # Read in small chunks and handle incomplete reads
                        for chunk in response.raw.stream(8192, decode_content=True):
                            if chunk:
                                content_bytes.extend(chunk)
                        
                        logger.debug(f"Successfully read {len(content_bytes)} bytes")
                        content_text = content_bytes.decode('utf-8')
                        
                    except Exception as read_err:
                        # If we got some data, try to use it
                        if len(content_bytes) > 0:
                            logger.warning(f"Read interrupted but got {len(content_bytes)} bytes, attempting to decode...")
                            content_text = content_bytes.decode('utf-8')
                        else:
                            raise read_err
                    
                    # Parse JSON
                    logger.debug("Parsing JSON response...")
                    try:
                        data = json.loads(content_text)
                    except json.JSONDecodeError as json_err:
                        # Try to repair truncated JSON
                        logger.warning(f"JSON parse error: {json_err}. Attempting to repair truncated JSON...")
                        repaired_data = self._try_repair_json(content_text)
                        if repaired_data:
                            logger.info(f"Successfully repaired JSON! Got {len(repaired_data.get('features', []))} features")
                            data = repaired_data
                        else:
                            raise json_err
                    
                    # Success! Break out of retry loop
                    logger.info(f"Successfully received data on attempt {attempt + 1}")
                    break
                    
                except (UnicodeDecodeError, json.JSONDecodeError) as parse_err:
                    logger.error(f"Failed to parse response: {parse_err}")
                    if attempt < max_retries - 1:
                        continue  # Retry on parse errors
                    # Final attempt failed - give clear message about service issue
                    raise Exception(
                        "GlobalBuildingAtlas service returned incomplete data after 3 attempts.\n\n"
                        "The service is experiencing high traffic or instability.\n\n"
                        "Please try:\n"
                        "  • Smaller bounding box\n"
                        "  • Retry in a few minutes\n"
                        "  • Use Microsoft/Google sources"
                    )
                    
                finally:
                    # Always close response and session
                    try:
                        response.close()
                    except:
                        pass
                    try:
                        session.close()
                    except:
                        pass
                
            except requests.exceptions.ChunkedEncodingError as e:
                logger.warning(f"ChunkedEncodingError on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    continue  # Retry
                else:
                    logger.error(f"All {max_retries} attempts failed with ChunkedEncodingError")
                    raise Exception("Connection was interrupted while downloading data. The service may be unstable or experiencing high traffic.")
            
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"ConnectionError on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    continue  # Retry
                else:
                    logger.error(f"All {max_retries} attempts failed with ConnectionError")
                    raise Exception("Network connection error. Please check your internet connection.")
            
            except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                error_str = str(e).lower()
                if "incompleteread" in error_str or "connection broken" in error_str:
                    logger.warning(f"Connection interrupted on attempt {attempt + 1}/{max_retries}: {e}")
                    if attempt < max_retries - 1:
                        continue  # Retry
                    else:
                        logger.error(f"All {max_retries} attempts failed with connection issues")
                        raise Exception("Connection was interrupted while downloading data. The service may be unstable or experiencing high traffic.")
                else:
                    # Don't retry for other types of errors
                    raise
            
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                raise Exception("Invalid JSON response from WFS service. The service may have returned an error page.")
        
        # Check if we got data
        if data is None:
            logger.error("Failed to retrieve data after all retry attempts")
            raise Exception("Failed to retrieve data from GlobalBuildingAtlas WFS service after multiple attempts.")
        
        try:
            if 'features' not in data:
                raise ValueError("Invalid WFS response: no 'features' field")
            
            features = data['features']
            total_count = len(features)
            
            logger.info(f"Received {total_count} buildings from WFS")
            
            if total_count == 0:
                # Create empty GeoJSON
                empty_geojson = {
                    'type': 'FeatureCollection',
                    'features': []
                }
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(empty_geojson, f, indent=2)
                
                logger.info("No buildings found in specified area")
                return {
                    'count': 0,
                    'output_file': output_file,
                    'bbox_used': (lon_min, lat_min, lon_max, lat_max)
                }
            
            # Process features
            logger.info("Processing building features...")
            logger.debug(f"Total features to process: {total_count}")
            processed_features = []
            
            for i, feature in enumerate(features):
                if cancel_event and cancel_event.is_set():
                    logger.info("Extraction cancelled by user")
                    return {'count': 0, 'cancelled': True}
                
                if i % 1000 == 0 and i > 0:
                    logger.info(f"  Processed {i}/{total_count} buildings...")
                
                try:
                    processed_feature = self._process_feature(feature, extrafields)
                    if processed_feature:
                        processed_features.append(processed_feature)
                except Exception as e:
                    logger.warning(f"Failed to process feature {i}: {e}")
                    continue
            
            # Create output GeoJSON
            output_geojson = {
                'type': 'FeatureCollection',
                'features': processed_features,
                'metadata': {
                    'source': 'GlobalBuildingAtlas',
                    'wfs_url': self.wfs_url,
                    'layer': self.layer_name,
                    'bbox': {
                        'lon_min': lon_min,
                        'lat_min': lat_min,
                        'lon_max': lon_max,
                        'lat_max': lat_max
                    },
                    'total_features': data.get('totalFeatures', total_count),
                    'returned_features': len(processed_features)
                }
            }
            
            # Save to file
            logger.info(f"Saving {len(processed_features)} buildings to {output_file}")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_geojson, f, indent=2)
            
            logger.info("Extraction completed successfully")
            
            return {
                'count': len(processed_features),
                'output_file': output_file,
                'bbox_used': (lon_min, lat_min, lon_max, lat_max),
                'total_available': data.get('totalFeatures', total_count)
            }
            
        except Exception as e:
            # Catch any other exceptions not handled in retry loop
            logger.error(f"Extraction failed: {e}", exc_info=True)
            raise
    
    def _try_repair_json(self, truncated_json: str) -> Optional[Dict]:
        """
        Attempt to repair truncated GeoJSON by finding the last complete feature.
        
        Returns:
            Repaired dict if successful, None if repair failed
        """
        try:
            # Find the last complete feature in the features array
            # Look for the pattern }], which ends a feature
            
            # Find the start of the features array
            features_start = truncated_json.find('"features"')
            if features_start == -1:
                return None
            
            # Find positions of complete feature endings ("},")
            # Work backwards to find the last complete feature
            search_pos = len(truncated_json) - 1
            
            # Look for the last complete feature ending
            last_complete_pos = -1
            
            # Try to find the last "}," or "}]" which would indicate a complete feature
            for end_pattern in ['},', '}]']:
                pos = truncated_json.rfind(end_pattern)
                if pos > last_complete_pos:
                    last_complete_pos = pos
            
            if last_complete_pos == -1:
                logger.debug("Could not find any complete features")
                return None
            
            # Truncate at the last complete feature and close the JSON properly
            repaired = truncated_json[:last_complete_pos + 1]
            
            # Count open brackets to close them properly
            open_brackets = repaired.count('[') - repaired.count(']')
            open_braces = repaired.count('{') - repaired.count('}')
            
            # Close any open structures
            repaired += ']' * open_brackets
            repaired += '}' * open_braces
            
            # Try to parse the repaired JSON
            data = json.loads(repaired)
            
            # Verify it has features
            if 'features' in data and isinstance(data['features'], list):
                logger.info(f"JSON repair successful: {len(data['features'])} complete features recovered")
                return data
            
            return None
            
        except Exception as e:
            logger.debug(f"JSON repair failed: {e}")
            return None

    def _process_feature(self, feature: Dict, extrafields: bool = False) -> Optional[Dict]:
        """
        Process a single feature from WFS response.
        
        Converts coordinates if needed and formats properties.
        Returns building data compatible with Building Generator format.
        Height is kept in METERS (consistent with Google buildings).
        
        Args:
            feature: Feature dictionary from WFS response
            extrafields: If True, add OSM classification fields (consistent with Microsoft/Google)
        """
        try:
            geometry = feature.get('geometry')
            properties = feature.get('properties', {})
            
            if not geometry:
                logger.debug("Feature has no geometry, skipping")
                return None
            
            # Check if coordinates are in EPSG:3857 (large numbers)
            # If so, transform to EPSG:4326
            coords = geometry.get('coordinates', [])
            if coords and len(coords) > 0:
                # Sample first coordinate to check
                first_coord = self._get_first_coordinate(coords)
                if first_coord and (abs(first_coord[0]) > 200 or abs(first_coord[1]) > 200):
                    # Likely EPSG:3857, transform it
                    logger.debug(f"Transforming coordinates from EPSG:3857 to EPSG:4326")
                    geometry = self._transform_geometry(geometry)
            
            # Build output properties compatible with Google/Microsoft format
            # Keep only essential fields - height in METERS (same as Google)
            output_props = {
                'height': float(properties.get('height', 0)),  # Height in meters
                'est_height': float(properties.get('height', 0)),  # Duplicate for compatibility
                'building': 'yes',  # Generic building type for OSM compatibility
            }
            
            # Add ID if available
            building_id = properties.get('id', properties.get('ogc_fid', ''))
            if building_id:
                output_props['gid'] = str(building_id)
            
            # Add extra OSM classification fields if requested (same as Microsoft/Google)
            if extrafields:
                for field in [
                    "man_made", "aeroway", "military", "tower",
                    "bms", "power", "leisure", "religion", "sport", "barrier",
                ]:
                    if field not in output_props:
                        output_props[field] = ""
            
            return {
                'type': 'Feature',
                'geometry': geometry,
                'properties': output_props
            }
            
        except Exception as e:
            logger.warning(f"Error processing feature: {e}")
            return None
    
    def _get_first_coordinate(self, coords):
        """Recursively get the first coordinate from nested lists."""
        if not isinstance(coords, list):
            return None
        if len(coords) == 0:
            return None
        if isinstance(coords[0], (int, float)):
            # This is a coordinate pair
            return coords
        else:
            # Nested list, recurse
            return self._get_first_coordinate(coords[0])
    
    def _transform_geometry(self, geometry: Dict) -> Dict:
        """Transform geometry from EPSG:3857 to EPSG:4326."""
        geom_type = geometry.get('type')
        coords = geometry.get('coordinates', [])
        
        if geom_type == 'Polygon':
            transformed_coords = self._transform_polygon_coords(coords)
        elif geom_type == 'MultiPolygon':
            transformed_coords = self._transform_multipolygon_coords(coords)
        else:
            # Unsupported geometry type, return as-is
            return geometry
        
        return {
            'type': geom_type,
            'coordinates': transformed_coords
        }
    
    def _transform_polygon_coords(self, coords):
        """Transform polygon coordinates."""
        transformed = []
        for ring in coords:
            transformed_ring = []
            for x, y in ring:
                lon, lat = self.transformer.transform(x, y)
                transformed_ring.append([lon, lat])
            transformed.append(transformed_ring)
        return transformed
    
    def _transform_multipolygon_coords(self, coords):
        """Transform multipolygon coordinates."""
        transformed = []
        for polygon in coords:
            transformed_polygon = self._transform_polygon_coords(polygon)
            transformed.append(transformed_polygon)
        return transformed
    
    def get_available_layers(self) -> list:
        """Get list of available layers from WFS service."""
        try:
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetCapabilities'
            }
            
            response = requests.get(self.wfs_url, params=params, timeout=30)
            response.raise_for_status()
            
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            layers = []
            namespaces = {
                'wfs': 'http://www.opengis.net/wfs/2.0',
                'wfs1': 'http://www.opengis.net/wfs',
            }
            
            for ns_uri in namespaces.values():
                for ft in root.findall(f'.//{{{ns_uri}}}FeatureType'):
                    name_elem = ft.find(f'{{{ns_uri}}}Name')
                    if name_elem is not None:
                        layers.append(name_elem.text)
            
            return list(set(layers))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Failed to get WFS capabilities: {e}")
            return []


def extract_globalatlas_buildings(
    top_left: Tuple[float, float],
    bottom_right: Tuple[float, float],
    output_file: str,
    extrafields: bool = False,
    cancel_event=None
) -> Dict[str, Any]:
    """
    Convenience function to extract buildings from GlobalBuildingAtlas.
    
    Args:
        top_left: (latitude, longitude) of top-left corner
        bottom_right: (latitude, longitude) of bottom-right corner
        output_file: Path to save GeoJSON output
        extrafields: If True, add OSM classification fields (building, man_made, etc.)
        cancel_event: Threading event to cancel operation
    
    Returns:
        Dictionary with extraction results
        
    Note:
        Heights are in METERS (consistent with Google buildings format).
        Building Generator will convert to feet internally when loading.
    """
    extractor = GlobalAtlasExtractor()
    return extractor.extract_buildings_by_bbox(
        top_left, 
        bottom_right, 
        output_file,
        extrafields=extrafields,
        cancel_event=cancel_event
    )


if __name__ == "__main__":
    # Test extraction
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("=" * 80)
    print("Testing GlobalBuildingAtlas Extraction")
    print("=" * 80)
    
    # Test with Berlin area
    print("\nExtracting buildings from Berlin, Germany...")
    print("  Top-left: 52.55°N, 13.35°E")
    print("  Bottom-right: 52.48°N, 13.45°E")
    print()
    
    result = extract_globalatlas_buildings(
        top_left=(52.55, 13.35),
        bottom_right=(52.48, 13.45),
        output_file="test_globalatlas_output.geojson"
    )
    
    print("\n" + "=" * 80)
    print("Extraction completed!")
    print("=" * 80)
    print(f"  Buildings extracted: {result['count']}")
    print(f"  Output file: {result['output_file']}")
    if 'total_available' in result:
        print(f"  Total available in area: {result['total_available']}")
    print()
    print("✓ Heights are in METERS (compatible with Google format)")
    print("✓ Building Generator will convert to feet internally")
    print("=" * 80)


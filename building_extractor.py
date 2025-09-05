import os
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def _footprints_root_from(root_dir: str) -> str:
    """Return the footprints root given a base directory.

    If root_dir already points to a 'footprints' directory, return it as-is,
    otherwise append 'footprints' to root_dir.
    """
    try:
        base = os.path.basename(os.path.normpath(root_dir))
    except Exception:
        base = ""
    return root_dir if base.lower() == "footprints" else os.path.join(root_dir, "footprints")


def resolve_ms_input(root_dir: str, location: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (kind, path) for Microsoft dataset.

    kind: "divided" for a folder containing *_metadata.json, "combined" for a single <location>.geojson,
    or (None, None) if not found.
    """
    base = os.path.join(_footprints_root_from(root_dir), "microsoft", location)
    logger.debug(f"Resolving Microsoft dataset. base={base}")
    divided = None
    combined = None
    if os.path.isdir(base):
        for f in os.listdir(base):
            if f.endswith("_metadata.json"):
                divided = base
                break
        cand = os.path.join(base, f"{location}.geojson")
        if os.path.isfile(cand):
            combined = cand
    if divided:
        logger.info(f"Microsoft dataset resolved as DIVIDED: {base}")
        return ("divided", divided)
    if combined:
        logger.info(f"Microsoft dataset resolved as COMBINED: {combined}")
        return ("combined", combined)
    logger.warning(f"Microsoft dataset not found for location='{location}' under {base}")
    return (None, None)


def extract_ms_divided(folder: str, output_file: str, tl, br, extrafields: bool):
    logger.info(f"MS extract (divided) start: folder={folder}, output={output_file}, tl={tl}, br={br}, extra={extrafields}")
    import geopandas as gpd
    from shapely.geometry import box
    import json
    import pandas as pd

    # Build AOI bbox (inputs are [lat, lon]) -> shapely uses (minx=minLon, miny=minLat, ...)
    bbox = box(min(tl[1], br[1]), min(tl[0], br[0]), max(tl[1], br[1]), max(tl[0], br[0]))

    # Find metadata
    meta_file = None
    try:
        for f in os.listdir(folder):
            if f.endswith("_metadata.json"):
                meta_file = os.path.join(folder, f)
                break
    except Exception as e:
        logger.error(f"Failed to list folder for metadata: {e}")
        raise

    if not meta_file:
        raise FileNotFoundError("Microsoft divided dataset metadata file not found in folder")

    # Load metadata and compute intersecting chunks
    try:
        with open(meta_file, "r") as fh:
            metadata = json.load(fh)
    except Exception as e:
        logger.error(f"Failed to read metadata file {meta_file}: {e}")
        raise

    intersecting_files = []
    for filename, coords in metadata.items():
        try:
            cell = box(coords["x_min"], coords["y_min"], coords["x_max"], coords["y_max"])
            if bbox.intersects(cell):
                intersecting_files.append(os.path.join(folder, filename))
        except Exception:
            continue

    if not intersecting_files:
        logger.info("No intersecting chunks found for provided AOI. Writing empty GeoJSON.")
        _write_empty_geojson(output_file)
        return {"count": 0, "output_file": output_file, "source": "microsoft_divided"}

    frames = []
    for path in intersecting_files:
        try:
            gdf = gpd.read_file(path)
            # Filter by AOI
            sel = gdf[gdf.intersects(bbox)]
            if not sel.empty:
                frames.append(sel)
        except Exception as e:
            logger.warning(f"Failed to read or filter chunk {path}: {e}")
            continue

    if not frames:
        logger.info("No buildings found inside AOI after filtering. Writing empty GeoJSON.")
        _write_empty_geojson(output_file)
        return {"count": 0, "output_file": output_file, "source": "microsoft_divided"}

    combined = pd.concat(frames, ignore_index=True)
    # Ensure CRS
    try:
        combined = combined.set_crs(epsg=4326, allow_override=True)
    except Exception:
        pass

    # Add extra fields, if requested
    if extrafields:
        for field in [
            "building", "man_made", "aeroway", "military", "tower",
            "bms", "power", "leisure", "religion", "sport", "barrier",
        ]:
            if field not in combined.columns:
                combined[field] = ""

    # Write output
    try:
        combined.to_file(output_file, driver="GeoJSON")
    except Exception as e:
        logger.error(f"Failed to write extracted GeoJSON: {e}")
        raise

    count = int(len(combined))
    logger.info(f"MS extract (divided) finished: rows={count}, output={output_file}")
    return {"count": count, "output_file": output_file, "source": "microsoft_divided"}


def _write_empty_geojson(output_file: str) -> None:
    """Write an empty FeatureCollection to output_file to avoid missing-file confusion."""
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    except Exception:
        pass
    empty_fc = {"type": "FeatureCollection", "features": []}
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            import json as _json
            _json.dump(empty_fc, f)
    except Exception:
        # Last resort: ignore write failures; caller will surface it
        pass


def extract_ms_combined(combined_file: str, output_file: str, tl, br, extrafields: bool):
    logger.info(f"MS extract (combined) start: file={combined_file}, output={output_file}, tl={tl}, br={br}, extra={extrafields}")
    import geopandas as gpd
    from shapely.geometry import box

    bb = box(min(tl[1], br[1]), min(tl[0], br[0]), max(tl[1], br[1]), max(tl[0], br[0]))
    gdf = gpd.read_file(combined_file)
    filtered = gdf[gdf.intersects(bb)]
    if extrafields:
        for field in [
            "building",
            "man_made",
            "aeroway",
            "military",
            "tower",
            "bms",
            "power",
            "leisure",
            "religion",
            "sport",
            "barrier",
        ]:
            if field not in filtered.columns:
                filtered[field] = ""
    filtered.to_file(output_file, driver="GeoJSON")
    logger.info(f"MS extract (combined) finished: rows={len(filtered)}, output={output_file}")
    return {"count": int(len(filtered)), "output_file": output_file, "source": "microsoft_combined"}


def resolve_google_source(
    root_dir: str, selected_source: Optional[str], dataset_name: Optional[str]
) -> Tuple[Optional[bool], Optional[str]]:
    """Return (use_chunks, path) for Google dataset.

    - If selected_source is provided, return (isdir, selected_source)
    - Else look for dataset_name under footprints/google/<name> preferring <name>_chunks over <name>_buildings.csv
    """
    if selected_source:
        logger.debug(f"Google resolve: using selected_source={selected_source}")
        return (os.path.isdir(selected_source), selected_source)
    name = (dataset_name or "").strip()
    if not name:
        return (None, None)
    base = os.path.join(_footprints_root_from(root_dir), "google", name)
    chunks = os.path.join(base, f"{name}_chunks")
    if os.path.isdir(chunks) and os.path.isfile(os.path.join(chunks, "chunk_boundaries.geojson")):
        logger.info(f"Google dataset resolved as CHUNKS: {chunks}")
        return (True, chunks)
    csv_path = os.path.join(base, f"{name}_buildings.csv")
    if os.path.isfile(csv_path):
        logger.info(f"Google dataset resolved as CSV: {csv_path}")
        return (False, csv_path)
    logger.warning(f"Google dataset not found: name={name} base={base}")
    return (None, None)


def divide_google_tile(csv_dir: str, tile_id: str, google_root: Optional[str] = None) -> None:
    """Divide a Google buildings CSV located in csv_dir for tile_id.

    tiles.geojson is expected primarily at <google_root>/tiles.geojson. If not present there,
    a secondary check is performed at <csv_dir>/tiles.geojson. If neither exists, the
    operation will fail with a clear error.
    """
    import pandas as pd
    import geopandas as gpd
    from shapely.geometry import box
    import json
    from tqdm import tqdm

    logger.info(f"Google divide start: csv_dir={csv_dir}, tile_id={tile_id}")
    os.makedirs(csv_dir, exist_ok=True)
    csv_path = os.path.join(csv_dir, f"{tile_id}_buildings.csv")
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    # Load tiles.geojson to get tile geometry
    candidate_paths = []
    if google_root:
        candidate_paths.append(os.path.join(google_root, "tiles.geojson"))
    candidate_paths.append(os.path.join(csv_dir, "tiles.geojson"))
    tiles_path = next((p for p in candidate_paths if os.path.isfile(p)), None)
    if tiles_path is None:
        raise FileNotFoundError(
            f"tiles.geojson not found. Checked: {candidate_paths}"
        )
    with open(tiles_path, "r") as f:
        data = json.load(f)
    tile_geom = None
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        if str(props.get("tile_id")) == str(tile_id):
            try:
                from shapely.geometry import Polygon
                tile_geom = Polygon(feat["geometry"]["coordinates"][0])
            except Exception:
                tile_geom = None
            break
    if tile_geom is None:
        raise ValueError(f"Tile {tile_id} not found in tiles.geojson")

    # Create geographic chunks
    num_chunks = 1000
    minx, miny, maxx, maxy = tile_geom.bounds
    step = int(num_chunks ** 0.5)
    dx = (maxx - minx) / step
    dy = (maxy - miny) / step
    chunks = []
    for i in range(step):
        for j in range(step):
            c = box(minx + i * dx, miny + j * dy, minx + (i + 1) * dx, miny + (j + 1) * dy)
            if c.intersects(tile_geom):
                chunks.append(c)

    out_dir = os.path.join(csv_dir, f"{tile_id}_chunks")
    if os.path.isdir(out_dir):
        import shutil
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    df = pd.read_csv(csv_path)
    try:
        from shapely import wkt as _wkt
        gdf = gpd.GeoDataFrame(df, geometry=gpd.GeoSeries.from_wkt(df["geometry"]))
    except Exception:
        # Fallback parser
        df["geometry"] = df["geometry"].apply(_parse_polygon_fallback)
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
    if gdf.crs is None:
        try:
            gdf.set_crs(epsg=4326, inplace=True)
        except Exception:
            pass

    for idx, c in enumerate(tqdm(chunks, desc="Processing chunks")):
        subset = gdf[gdf.intersects(c)]
        if not subset.empty:
            subset.to_file(os.path.join(out_dir, f"chunk_{idx}.geojson"), driver="GeoJSON")

    # Save chunk boundaries
    boundaries = gpd.GeoDataFrame(geometry=chunks)
    boundaries["chunk_id"] = range(len(chunks))
    boundaries.to_file(os.path.join(out_dir, "chunk_boundaries.geojson"), driver="GeoJSON")
    logger.info(f"Google divide finished: chunks_dir={out_dir}")


def _parse_polygon_fallback(polygon_str):
    """Fallback parser for POLYGON/MULTIPOLYGON strings into shapely geometry."""
    try:
        from shapely import wkt
        from shapely.geometry import Polygon, MultiPolygon
        import re
    except Exception:
        return None
    try:
        return wkt.loads(polygon_str)
    except Exception:
        pass
    try:
        coords_str = re.findall(r"\(\((.*?)\)\)", polygon_str)
        if coords_str:
            all_coords = [
                [tuple(map(float, pair.split())) for pair in coord.split(',')]
                for coord in coords_str
            ]
            if len(all_coords) == 1:
                return Polygon(all_coords[0])
            return MultiPolygon([Polygon(coords) for coords in all_coords])
    except Exception:
        return None
    return None


def _ms_divide_data(gdf, output_folder, location, bounds):
    """Divide MS GeoDataFrame into smaller GeoJSON files with metadata, locally implemented."""
    import numpy as np
    import math
    from shapely.geometry import box
    from tqdm import tqdm
    x_min, y_min, x_max, y_max = bounds
    area = (x_max - x_min) * (y_max - y_min)
    chunk_area = area / 100.0 if area > 0 else 1.0
    grid_size = math.sqrt(chunk_area) if chunk_area > 0 else max(x_max - x_min, y_max - y_min) / 10.0
    x_ranges = list(np.arange(x_min, x_max, grid_size))
    y_ranges = list(np.arange(y_min, y_max, grid_size))

    metadata = {}
    for x in tqdm(x_ranges, desc="Dividing data"):
        for y in y_ranges:
            cell = box(x, y, min(x + grid_size, x_max), min(y + grid_size, y_max))
            cell_gdf = gdf[gdf.intersects(cell)]
            if not cell_gdf.empty:
                filename = f"{location}_{x:.6f}_{y:.6f}.geojson"
                cell_gdf.to_file(os.path.join(output_folder, filename), driver="GeoJSON")
                metadata[filename] = {
                    "x_min": float(x),
                    "y_min": float(y),
                    "x_max": float(min(x + grid_size, x_max)),
                    "y_max": float(min(y + grid_size, y_max)),
                }
    import json
    with open(os.path.join(output_folder, f"{location}_metadata.json"), "w") as f:
        json.dump(metadata, f)

def download_ms_dataset(root_dir: str, location: str, divide_immediately: bool, cancel_event=None) -> str:
    """Download Microsoft footprints for location into footprints/microsoft/<location>.

    Returns the output folder path. Does not depend on GUI code.
    """
    import pandas as pd
    import geopandas as gpd
    from shapely.geometry import shape
    from tqdm import tqdm
    import json

    fp_root = _footprints_root_from(root_dir)
    output_folder = os.path.join(fp_root, "microsoft", location)
    os.makedirs(output_folder, exist_ok=True)
    logger.info(f"MS download start: location={location}, output={output_folder}, divide={divide_immediately}")

    links_urls = [
        "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv",
        "https://minedbuildings.blob.core.windows.net/global-buildings/dataset-links.csv",
    ]
    dataset_links = None
    for url in links_urls:
        try:
            dataset_links = pd.read_csv(url)
            logger.debug(f"Loaded dataset-links from {url}")
            break
        except Exception:
            continue
    if dataset_links is None:
        raise RuntimeError("Failed to download dataset-links.csv from known endpoints")

    norm = dataset_links["Location"].astype(str).str.strip()
    norm_lower = norm.str.lower()
    loc_norm = str(location).strip()
    loc_lower = loc_norm.lower()

    # Exact match first
    location_links = dataset_links[norm_lower == loc_lower]

    # If no exact match, try substring contains
    if location_links.empty and loc_lower:
        location_links = dataset_links[norm_lower.str.contains(loc_lower, na=False)]

    # Handle not found or overly broad inputs with suggestions
    if location_links.empty or len(location_links) > 50:
        # Build suggestions using difflib on lowercased names but display originals
        try:
            import difflib
            all_names = list(norm.unique())
            # Map lowercase to original for display
            lower_to_original = {n.lower(): n for n in all_names}
            candidates = list(lower_to_original.keys())
            close = difflib.get_close_matches(loc_lower, candidates, n=10, cutoff=0.5) if loc_lower else []
            suggestions = [lower_to_original[c] for c in close]
            # If too broad (like 'k'), provide some starters matching prefix
            if not suggestions and loc_lower:
                suggestions = [n for n in all_names if n.lower().startswith(loc_lower)][:10]
        except Exception:
            suggestions = []

        if location_links.empty:
            msg = f"No dataset for '{location}'."
        else:
            msg = f"'{location}' is too broad. Please be more specific."

        if suggestions:
            msg += " Suggestions: " + ", ".join(suggestions)

        logger.error(msg)
        raise ValueError(msg)

    all_frames = []
    for _, row in tqdm(location_links.iterrows(), total=len(location_links), desc="Processing data"):
        if cancel_event is not None and getattr(cancel_event, 'is_set', lambda: False)():
            logger.warning("MS download cancelled by user")
            raise RuntimeError("Cancelled")
        try:
            df = pd.read_json(row.Url, lines=True)
            df["geometry"] = df["geometry"].apply(shape)
            gdf = gpd.GeoDataFrame(df, crs=4326)
            all_frames.append(gdf)
        except Exception as e:
            logger.warning(f"Error processing {row.Url}: {e}")
            continue

    if not all_frames:
        raise RuntimeError("No data processed for the given location")

    combined = pd.concat(all_frames)
    bounds = combined.total_bounds
    logger.debug(f"MS combined rows={combined.shape[0]}, bounds={bounds}")

    if divide_immediately:
        logger.info("MS download: dividing dataset")
        _ms_divide_data(combined, output_folder, location, bounds)
    else:
        out = os.path.join(output_folder, f"{location}.geojson")
        logger.info(f"MS download: saving combined GeoJSON -> {out}")
        combined.to_file(out, driver="GeoJSON")

    return output_folder


def extract_google(use_chunks: bool, input_path: str, output_file: str, tl, br, extrafields: bool):
    """Google extraction logic (CSV or chunk DB) consolidated here."""
    logger.info(f"Google extract start: use_chunks={use_chunks}, input={input_path}, output={output_file}, tl={tl}, br={br}, extra={extrafields}")
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import box

    bb = box(min(tl[1], br[1]), min(tl[0], br[0]), max(tl[1], br[1]), max(tl[0], br[0]))

    extra_fields = [
        "building", "man_made", "aeroway", "military", "tower",
        "bms", "power", "leisure", "religion", "sport", "barrier",
    ]

    frames = []
    if use_chunks:
        try:
            boundaries_path = os.path.join(input_path, "chunk_boundaries.geojson")
            chunk_boundaries = gpd.read_file(boundaries_path)
            relevant = chunk_boundaries[chunk_boundaries.intersects(bb)]
            for _, row in relevant.iterrows():
                cid = int(row.get("chunk_id", -1))
                chunk_file = os.path.join(input_path, f"chunk_{cid}.geojson")
                try:
                    gdf = gpd.read_file(chunk_file)
                    sel = gdf[gdf.intersects(bb)]
                    if extrafields and not sel.empty:
                        for f in extra_fields:
                            if f not in sel.columns:
                                sel[f] = ""
                    if not sel.empty:
                        frames.append(sel)
                except Exception as e:
                    logger.warning(f"Failed reading chunk {chunk_file}: {e}")
        except Exception as e:
            logger.error(f"Failed processing chunks in {input_path}: {e}")
            raise
    else:
        # CSV path
        try:
            for chunk in pd.read_csv(input_path, chunksize=100_000, dtype={"geometry": str}):
                try:
                    from shapely import wkt as _wkt
                except Exception:
                    _wkt = None
                # Parse geometry
                def _parse_geom(val):
                    if isinstance(val, str):
                        if _wkt is not None:
                            try:
                                return _wkt.loads(val)
                            except Exception:
                                pass
                        # Fallback basic parse
                        return _parse_polygon_fallback(val)
                    return None

                chunk["geometry"] = chunk["geometry"].apply(_parse_geom)
                gdf = gpd.GeoDataFrame(chunk, geometry="geometry")
                gdf = gdf.dropna(subset=["geometry"])
                if gdf.crs is None:
                    try:
                        gdf.set_crs(epsg=4326, inplace=True)
                    except Exception:
                        pass
                sel = gdf[gdf.intersects(bb)]
                if extrafields and not sel.empty:
                    for f in extra_fields:
                        if f not in sel.columns:
                            sel[f] = ""
                if not sel.empty:
                    frames.append(sel)
        except Exception as e:
            logger.error(f"Failed processing CSV {input_path}: {e}")
            raise

    if frames:
        out_gdf = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True))
        try:
            out_gdf["geometry"] = out_gdf["geometry"].simplify(tolerance=0.0001)
        except Exception:
            pass
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
        except Exception:
            pass
        out_gdf.to_file(output_file, driver="GeoJSON")
        count = int(len(out_gdf))
        logger.info(f"Google extract finished: rows={count}, output={output_file}")
        return {"count": count, "output_file": output_file, "source": "google_chunks" if use_chunks else "google_csv"}
    else:
        _write_empty_geojson(output_file)
        logger.info(f"Google extract finished: rows=0, output={output_file}")
        return {"count": 0, "output_file": output_file, "source": "google_chunks" if use_chunks else "google_csv"}



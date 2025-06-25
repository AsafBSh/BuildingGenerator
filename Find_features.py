import math
import numpy as np
import matplotlib.pyplot as plt
import logging
from MinimumBoundingBox import MinimumBoundingBox

# Set up logging - use standard pattern to inherit from main application
logger = logging.getLogger(__name__)


def draw_shape(points_list, shape_color="blue", marker="o", label=None):
    """
    Draws a shape based on a list of points.

    Args:
        points_list (list): List of lists, where each inner list contains (x, y) coordinates representing a point.
        shape_color (str): Color of the shape's outline.
        marker (str): Marker style for the points.
        label (str): Label for the shape in the plot legend.

    Returns:
        None
    """
    logger.debug(f"Drawing shape with {len(points_list)} points, color: {shape_color}, marker: {marker}")
    
    try:
        # Extract x and y coordinates from the points_list
        x_coords = [point[0] for point in points_list]
        y_coords = [point[1] for point in points_list]

        logger.debug(f"Extracted coordinates: x_range=[{min(x_coords):.3f}, {max(x_coords):.3f}], y_range=[{min(y_coords):.3f}, {max(y_coords):.3f}]")

        # Plot the points
        plt.plot(x_coords, y_coords, marker=marker, label=label, color=shape_color)

        # Connect the last point to the first point to close the shape
        plt.plot(
            [x_coords[-1], x_coords[0]], [y_coords[-1], y_coords[0]], color=shape_color
        )
        
        logger.debug("Shape drawn successfully")
        
    except Exception as e:
        logger.error(f"Error drawing shape: {str(e)}")
        raise


def calc_rotation_and_side_lengths_via_slope(rectangle_points):
    """calculate distances and angle from the negative Y axis in a clockwise rotation.
    it is done by calculating the slope of the most left point (or most left upper point) as pixed point"""
    logger.debug(f"Calculating rotation and side lengths for {len(rectangle_points)} rectangle points")
    
    try:
        # Ensure rectangle_points are numeric values
        rectangle_points = np.array(rectangle_points, dtype=float)
        logger.debug(f"Converted to numeric array with shape: {rectangle_points.shape}")
        
        distances = []
        # Get distances of the rectangle
        for i in range(len(rectangle_points)):
            distance = np.linalg.norm(
                rectangle_points[i] - rectangle_points[(i + 1) % len(rectangle_points)]
            )
            distances.append(distance)
        
        logger.debug(f"Calculated side distances: {[round(d, 3) for d in distances]}")
        
    except Exception as e:
        logger.error(f"Error calculating distances: {str(e)}")
        raise ValueError(f"Error calculating distances: {str(e)}")

    # Find the index of the leftmost point considering left upper point if multiple points have the same x-coordinate
    leftmost_point_indexes = np.where(
        rectangle_points[:, 0] == np.min(rectangle_points[:, 0])
    )[0]
    leftmost_point_index = leftmost_point_indexes[
        np.argmin(rectangle_points[leftmost_point_indexes, 1])
    ]
    leftmost_point = rectangle_points[leftmost_point_index]
    logger.debug(f"Found leftmost point at index {leftmost_point_index}: ({leftmost_point[0]:.3f}, {leftmost_point[1]:.3f})")

    # Find neighboring points
    prv_point_idx = (leftmost_point_index - 1) % len(rectangle_points)
    nxt_point_idx = (leftmost_point_index + 1) % len(rectangle_points)

    # get side lengths
    length_to_previous = distances[prv_point_idx]
    length_to_next = distances[leftmost_point_index]
    logger.debug(f"Side lengths: to_previous={length_to_previous:.3f}, to_next={length_to_next:.3f}")

    # Determine the longer side
    if length_to_previous > length_to_next:
        longer_side_neighbor = rectangle_points[prv_point_idx]
        longer_side_length = length_to_previous
    else:
        longer_side_neighbor = rectangle_points[nxt_point_idx]
        longer_side_length = length_to_next
    
    logger.debug(f"Longer side neighbor: ({longer_side_neighbor[0]:.3f}, {longer_side_neighbor[1]:.3f}), 'length': {longer_side_length:.3f}")

    # Calculate the slope
    Slope = (longer_side_neighbor[1] - leftmost_point[1]) / (
        longer_side_neighbor[0] - leftmost_point[0]
    )
    # calculate angle in radians from -y axis then convert to degrees
    Angle_in_Deg = math.degrees((math.pi / 2 * 3) - math.atan(Slope))
    
    logger.debug(f"Calculated slope: {Slope:.6f}, rotation angle: {Angle_in_Deg:.3f} degrees")
    logger.info(f"Rectangle analysis complete: rotation={Angle_in_Deg:.1f}°, sides={[round(d, 2) for d in distances]}")

    return Angle_in_Deg, distances


def check_crossing_lines(bondingBox):
    """The funtion is fixing the arrangement of the bonding box's points making it consistent with the algorithm"""
    logger.debug(f"Checking crossing lines for bounding box with {len(bondingBox)} points")
    
    try:
        # Ensure bondingBox contains numeric values
        bondingBox = np.array(bondingBox, dtype=float)
        logger.debug(f"Converted bounding box to numeric array with shape: {bondingBox.shape}")
        
        threshold = 1e-6  # A small threshold to account for numerical imprecisions
        corrections_made = 0

        for i in range(len(bondingBox)):
            p1 = bondingBox[i]
            p2 = bondingBox[
                (i + 1) % len(bondingBox)
            ]  # Wrap around to the first point if needed
            p3 = bondingBox[
                (i + 2) % len(bondingBox)
            ]  # Wrap around to the second point if needed

            # Calculate the vectors of the two line segments
            vec1 = p2 - p1
            vec2 = p3 - p2

            # Calculate the dot product between the vectors
            dot_product = np.dot(vec1, vec2)
            # Check if the dot product is above the threshold
            if abs(dot_product) > threshold:
                logger.debug(f"Crossing detected at point {i}: dot_product={dot_product:.6f} > threshold={threshold}")
                # If the dot product is above the threshold, switch the second and third coordinates
                (
                    bondingBox[(i + 2) % len(bondingBox), :],
                    bondingBox[(i + 3) % len(bondingBox), :],
                ) = (
                    bondingBox[(i + 3) % len(bondingBox), :].copy(),
                    bondingBox[(i + 2) % len(bondingBox), :].copy(),
                )
                corrections_made += 1
                logger.debug(f"Corrected point arrangement for crossing at index {i}")
                
        if corrections_made > 0:
            logger.info(f"Bounding box corrected: {corrections_made} crossing line(s) fixed")
        else:
            logger.debug("No crossing lines detected, bounding box arrangement is correct")
            
    except Exception as e:
        logger.error(f"Error processing bounding box: {str(e)}")
        raise ValueError(f"Error processing bounding box: {str(e)}")

    return bondingBox




def fitted_features(coordinates):
    """Main function:
    input: list of x and y coordinates
    output: size of bonding box and its rotation compare to the longest side
    """
    logger.info(f"Starting fitted_features processing with {len(coordinates)} input coordinates")
    
    # Ensure all coordinates are float values before processing
    try:
        # Convert all coordinates to float values
        float_coordinates = []
        skipped_points = 0
        
        for i, point in enumerate(coordinates):
            if len(point) < 2:
                skipped_points += 1
                logger.debug(f"Skipped point {i}: insufficient dimensions ({len(point)})")
                continue  # Skip points with insufficient dimensions
            try:
                # Try to convert each coordinate to float
                float_point = [float(point[0]), float(point[1])]
                float_coordinates.append(float_point)
            except (ValueError, TypeError) as e:
                # Skip points with non-numeric values
                skipped_points += 1
                logger.debug(f"Skipped point {i}: conversion error - {str(e)}")
                continue
                
        logger.debug(f"Coordinate conversion: {len(float_coordinates)} valid, {skipped_points} skipped")
        
        if len(float_coordinates) < 3:
            # Need at least 3 points for a valid polygon
            logger.error(f"Insufficient valid points: {len(float_coordinates)} (minimum 3 required)")
            raise ValueError("Insufficient valid points after conversion")
        
        logger.debug(f"Creating minimum bounding box from {len(float_coordinates)} points")
        # Convert to tuples for MinimumBoundingBox
        tuple_coordinations = [tuple(point) for point in float_coordinates]
        bounding_box = MinimumBoundingBox(tuple_coordinations)
        logger.debug("Minimum bounding box created successfully")
        
    except Exception as e:
        # Re-raise with more context
        logger.error(f"Error processing coordinates: {str(e)}")
        raise ValueError(f"Error processing coordinates: {str(e)}")

    # listing the bounding box
    try:
        logger.debug("Extracting bounding box corner points and center")
        bondingBox = np.array(list(bounding_box.corner_points), dtype=float)
        # Center (is list inside list for showing in graph
        center = [np.array(list(bounding_box.rectangle_center), dtype=float)]
        logger.debug(f"Bounding box center: ({center[0][0]:.3f}, {center[0][1]:.3f})")
        
        # Fixing arrange of points
        logger.debug("Checking and fixing bounding box point arrangement")
        bondingBox = check_crossing_lines(bondingBox)
        
    except Exception as e:
        logger.error(f"Error processing bounding box data: {str(e)}")
        raise ValueError(f"Error processing bounding box data: {str(e)}")

    try:
        logger.debug("Calculating rotation angle and side lengths")
        rotation_angle, side_lengths = calc_rotation_and_side_lengths_via_slope(bondingBox)
        
    except Exception as e:
        logger.error(f"Error calculating rotation and side lengths: {str(e)}")
        raise ValueError(f"Error calculating rotation and side lengths: {str(e)}")

    # Ensure all return values are proper numeric types
    try:
        logger.debug("Converting return values to proper numeric types")
        center_float = np.array(center[0], dtype=float)
        rotation_float = float(rotation_angle)
        side_lengths_float = [float(side) for side in side_lengths]
        
        # Log successful completion with summary
        logger.info(f"Fitted features processing complete: center=({center_float[0]:.3f}, {center_float[1]:.3f}), rotation={rotation_float:.1f}°, sides={[round(s, 2) for s in side_lengths_float]}")
        
        return center_float, rotation_float, side_lengths_float
        
    except Exception as e:
        logger.error(f"Error converting return values to numeric types: {str(e)}")
        raise ValueError(f"Error converting return values to numeric types: {str(e)}")

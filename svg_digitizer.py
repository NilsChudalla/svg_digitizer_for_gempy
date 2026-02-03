import xml.etree.ElementTree as ET
from svgpathtools import parse_path
import numpy as np
from shapely.geometry import LineString



def interpolate_along_path(d, step=1.0):
    """Function to interpolate points along paths of a SVG file.

    Args:
        d (_type_): _description_
        step (float, optional): density of the interpolation along the path. Not fixed length. Defaults to 1.0.

    Returns:
        lis: List of (x, y) tuples representing interpolated points along the path.
    """

    path = parse_path(d)

    L = path.length()
    distances = [i*step for i in range(int(L // step) + 1)]
    if distances[-1] < L:
        distances.append(L)

    points = [path.point(d / L) for d in distances]
    coords = np.array([(p.real, p.imag) for p in points])

    return coords

class svp_path:
    def __init__(self, path_id, inkscape_label, points):
        self.path_id = path_id
        self.inkscape_label = inkscape_label
        self.points = points

class svg_input:
    def __init__(self, filename, segment_length=1):
        self.filename = filename
        self.segment_length = segment_length
        self.results = []
        self.extract_points_from_svg()

    def extract_points_from_svg(self):

        tree = ET.parse(self.filename)
        root = tree.getroot()
        self.canvas_width = float(root.attrib.get('width')[:-2])
        self.canvas_height = float(root.attrib.get('height')[:-2])
        
        # Namespace mapping
        ns = {
            "svg": "http://www.w3.org/2000/svg",
            "inkscape": "http://www.inkscape.org/namespaces/inkscape"
        }
        # iterate over all <path> elements
        for path_elem in root.findall(".//svg:path", ns):
            path_id = path_elem.attrib.get("id", "no-id")
            inkscape_label = path_elem.attrib.get(f"{{{ns['inkscape']}}}label", None)
            d = path_elem.attrib.get("d")
            if d is None:
                continue

            coords = interpolate_along_path(d, self.segment_length)
            self.results.append(svp_path(path_id, inkscape_label, coords))


def extract_spatial_coords_from_svg(svg_input:svg_input, linestring:LineString, zlim:tuple):
    """function to convert svg sketch, given a shapely.geometry.LineString and the true vertical extent of cross section

    Args:
        svg_input (svg_input): _description_
        linestring (LineString): _description_
        zlim (tuple): _description_
    """
    assert len(zlim) == 2, "zlim must be a tuple of (zmin, zmax)"
    assert zlim[0] < zlim[1], "zlim[0] must be less than zlim[1]"
    assert linestring.length > 0, "linestring must have length greater than 0"
    assert type(linestring) == LineString, "linestring must be of type shapely.geometry.LineString (can be used from geopandas geometry)"

    for r in svg_input.results:

        # Normalize SVG coordinates to [0, 1]
        norm_x = r.points[:, 0] / float(svg_input.canvas_width)
        norm_y = r.points[:, 1] / float(svg_input.canvas_height)

        # Map normalized x to linestring length
        line_distances = norm_x * linestring.length
        line_points = [linestring.interpolate(d) for d in line_distances]
        spatial_x = np.array([pt.x for pt in line_points])
        spatial_y = np.array([pt.y for pt in line_points])

        # Map normalized y to zlim (mirrored)           
        spatial_z = zlim[1] - norm_y * (zlim[1] - zlim[0])  
        r.coords = np.column_stack((spatial_x, spatial_y, spatial_z))





"""
Shallow water from AnchorHold depth grids, and the chart the boat carries.

A depth grid is what anchorhold-web-viewer's pipeline writes beside every
chart: `depth_grid.json` (lonMin, latMin, dLon, dLat, cols, rows) and
`depth_grid.bin`, float32 little-endian, row 0 the southern row, NaN where
nothing was sounded. Depths are metres below chart datum; a lake has no tide,
so that is metres below the water surface on the day of the survey.

**Only charted shallow water becomes a no-go area.** Water that was never
sounded is exactly what a survey plan is for, so it is left alone here. The
boat's own copy of the chart is where unsounded water counts as dry.

**Interpolation is not measurement.** The pipeline fills the whole convex hull
of the soundings and masks only beyond a 200 ft floor, so a corner the boat
never crossed can carry a depth invented from a sounding a hundred feet away -
Indian Hills Lake has one, a fan painted from a single 18.5 m reading at the
launch. When the chart folder holds its `track.geojson`, cells farther than
`trust_within_ft` from the track are treated as unsounded. Half the line
spacing of the survey that made the chart is about right.

Polygons come back in the planner's local feet, like every other no-go area.
"""

from __future__ import annotations

import json
import math
import os

FT_PER_M = 3.280839895


class DepthGrid:
    """One AnchorHold depth grid, optionally masked to its survey track."""

    def __init__(self, folder: str):
        head = os.path.join(folder, "depth_grid.json")
        if not os.path.exists(head):
            raise ValueError(folder + " has no depth_grid.json - pick the chart folder"
                             " AnchorHold wrote (output/<name>).")
        import numpy as np
        with open(head) as f:
            self.header = json.load(f)
        h = self.header
        data = np.fromfile(os.path.join(folder, "depth_grid.bin"), "<f4")
        if data.size != h["rows"] * h["cols"]:
            raise ValueError(folder + ": depth_grid.bin does not match its header")
        self.depth_m = data.reshape(h["rows"], h["cols"]).astype(float)
        self.folder = folder
        self.name = os.path.basename(os.path.normpath(folder))
        self.masked = 0

    # cell (r, c) centre, lon/lat
    def lonlat(self, r, c):
        h = self.header
        return h["lonMin"] + c * h["dLon"], h["latMin"] + r * h["dLat"]

    def cell_size_ft(self):
        h = self.header
        m_lat = h["dLat"] * 111320.0
        m_lon = h["dLon"] * 111320.0 * math.cos(math.radians(h["latMin"]))
        return m_lon * FT_PER_M, m_lat * FT_PER_M

    def mask_to_track(self, trust_within_ft: float) -> int:
        """Blank cells farther than trust_within_ft from the survey track."""
        import numpy as np
        from scipy import ndimage
        path = os.path.join(self.folder, "track.geojson")
        if trust_within_ft <= 0 or not os.path.exists(path):
            return 0
        with open(path) as f:
            features = json.load(f).get("features", [])
        h = self.header
        rows, cols = self.depth_m.shape
        on_track = np.zeros((rows, cols), bool)
        for feat in features:
            g = feat.get("geometry") or {}
            parts = ([g["coordinates"]] if g.get("type") == "LineString" else
                     g["coordinates"] if g.get("type") == "MultiLineString" else [])
            for part in parts:
                for (lon0, lat0), (lon1, lat1) in zip(part[:-1], part[1:]):
                    n = 2 + int(max(abs(lon1 - lon0) / h["dLon"], abs(lat1 - lat0) / h["dLat"]) * 3)
                    c = np.round((np.linspace(lon0, lon1, n) - h["lonMin"]) / h["dLon"]).astype(int)
                    r = np.round((np.linspace(lat0, lat1, n) - h["latMin"]) / h["dLat"]).astype(int)
                    ok = (r >= 0) & (r < rows) & (c >= 0) & (c < cols)
                    on_track[r[ok], c[ok]] = True
        if not on_track.any():
            return 0
        fx, fy = self.cell_size_ft()
        dist = ndimage.distance_transform_edt(~on_track, sampling=(fy, fx))
        drop = (dist > trust_within_ft) & np.isfinite(self.depth_m)
        self.depth_m[drop] = np.nan
        self.masked = int(drop.sum())
        return self.masked

    def polygons(self, mask, frame):
        """Shapely polygons (local feet) around the True cells of `mask`."""
        import numpy as np
        from functools import reduce
        from shapely.geometry import Polygon
        from skimage import measure

        padded = np.pad(mask.astype(float), 1)
        rings = []
        for contour in measure.find_contours(padded, 0.5):
            pts = [frame.to_ft(*self.lonlat(r - 1, c - 1)) for r, c in contour]
            if len(pts) >= 4:
                ring = Polygon(pts)
                if not ring.is_valid:
                    ring = ring.buffer(0)
                if not ring.is_empty:
                    rings.append(ring)
        if not rings:
            return []
        # even-odd: a ring inside another is a hole in it
        shape = reduce(lambda a, b: a.symmetric_difference(b), rings)
        return list(shape.geoms) if shape.geom_type == "MultiPolygon" else [shape]


def shallow_no_go(folders, frame, water=None, shallower_than_ft: float = 3.0,
                  trust_within_ft: float = 25.0, min_area_ft2: float = 50.0):
    """
    No-go areas for every stretch charted shallower than `shallower_than_ft`.

    Returns (zones, grids, notes): zones as {name, kind, geom, min_depth_ft}
    ready for the no-go list, the loaded grids (kept for the boat export), and
    a line of text per grid for the status bar.
    """
    import numpy as np
    from scipy import ndimage
    from shapely.ops import unary_union

    zones, grids, notes = [], [], []
    for folder in folders:
        grid = DepthGrid(folder)
        masked = grid.mask_to_track(trust_within_ft)
        grids.append(grid)
        depth_ft = grid.depth_m * FT_PER_M
        shallow = np.isfinite(depth_ft) & (depth_ft < shallower_than_ft)
        labels, count = ndimage.label(shallow)
        found = 0
        for k in range(1, count + 1):
            cells = labels == k
            for part in grid.polygons(cells, frame):
                if water is not None:
                    part = part.intersection(water)
                if part.is_empty or part.area < min_area_ft2:
                    continue
                zones.append({"kind": "shallow", "geom": part,
                              "min_depth_ft": float(np.nanmin(depth_ft[cells])),
                              "source": grid.name})
                found += 1
        valid = depth_ft[np.isfinite(depth_ft)]
        notes.append("%s: %d shallow area(s) under %.1f ft; charted %.1f-%.1f ft%s" % (
            grid.name, found, shallower_than_ft,
            valid.min() if valid.size else 0, valid.max() if valid.size else 0,
            (", %d interpolated cell(s) far from the track ignored" % masked) if masked else ""))

    # grids that overlap find the same shoal twice: merge touching zones
    merged = []
    for zone in sorted(zones, key=lambda z: z["min_depth_ft"]):
        for m in merged:
            if m["geom"].intersects(zone["geom"]):
                m["geom"] = unary_union([m["geom"], zone["geom"]])
                m["min_depth_ft"] = min(m["min_depth_ft"], zone["min_depth_ft"])
                break
        else:
            merged.append(dict(zone))
    for i, zone in enumerate(merged, start=1):
        zone["name"] = "shallow %d (%.1f ft)" % (i, zone["min_depth_ft"])
    return merged, grids, notes


def write_boat_chart(folder: str, grids) -> str:
    """
    The chart the boat reads from its SD card (APM/scripts/chart/).

    Same AnchorHold format, so the onboard script needs no second parser. One
    grid is copied as masked; several are resampled onto one grid at the finest
    of their cell sizes, keeping the shallowest charted depth wherever they
    overlap - disagreeing surveys are resolved toward caution.
    """
    import numpy as np

    os.makedirs(folder, exist_ok=True)
    if not grids:
        raise ValueError("no depth grids loaded")
    if len(grids) == 1:
        header, depth = dict(grids[0].header), grids[0].depth_m
    else:
        d_lon = min(g.header["dLon"] for g in grids)
        d_lat = min(g.header["dLat"] for g in grids)
        west = min(g.header["lonMin"] for g in grids)
        south = min(g.header["latMin"] for g in grids)
        east = max(g.header["lonMin"] + (g.header["cols"] - 1) * g.header["dLon"] for g in grids)
        north = max(g.header["latMin"] + (g.header["rows"] - 1) * g.header["dLat"] for g in grids)
        cols = int(round((east - west) / d_lon)) + 1
        rows = int(round((north - south) / d_lat)) + 1
        lon = west + np.arange(cols) * d_lon
        lat = south + np.arange(rows) * d_lat
        depth = np.full((rows, cols), np.nan)
        for g in grids:
            h = g.header
            c = np.round((lon - h["lonMin"]) / h["dLon"]).astype(int)
            r = np.round((lat - h["latMin"]) / h["dLat"]).astype(int)
            ci = (c >= 0) & (c < h["cols"])
            ri = (r >= 0) & (r < h["rows"])
            sample = np.full((rows, cols), np.nan)
            sample[np.ix_(ri, ci)] = g.depth_m[np.ix_(r[ri], c[ci])]
            depth = np.fmin(depth, sample)
        header = {"lonMin": west, "latMin": south, "dLon": d_lon, "dLat": d_lat,
                  "cols": cols, "rows": rows, "nodata": "nan"}
    with open(os.path.join(folder, "depth_grid.json"), "w") as f:
        json.dump(header, f)
    np.asarray(depth, dtype="<f4").tofile(os.path.join(folder, "depth_grid.bin"))
    return folder

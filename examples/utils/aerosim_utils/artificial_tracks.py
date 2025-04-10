import math
import csv
import json
import random
from datetime import datetime, timedelta, timezone

# --- Helper Functions ---

def haversine(lon1, lat1, lon2, lat2):
    """Calculate the haversine distance between two lat/lon points in meters."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def load_ownship_trajectory(file_path, file_format="json"):
    """
    Load an ownship trajectory from a file.
    
    For JSON, expect a list of dictionaries with keys: "time", "lat", "lon", "alt".
    For CSV, assume the first three columns are lat, lon, alt and optionally a fourth column for time.
    If time is missing, time values are assigned sequentially (e.g., 0, 1, 2, … seconds).
    """
    if file_format.lower() == "json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Normalize keys
        for pt in data:
            if "lat" not in pt and "latitude" in pt:
                pt["lat"] = pt["latitude"]
            if "lon" not in pt and "longitude" in pt:
                pt["lon"] = pt["longitude"]
            if "alt" not in pt and "altitude" in pt:
                pt["alt"] = pt["altitude"]
        return data
    elif file_format.lower() == "csv":
        trajectory = []
        with open(file_path, newline='', encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                try:
                    lat = float(row[0])
                    lon = float(row[1])
                    alt = float(row[2])
                except Exception:
                    continue
                time_val = float(row[3]) if len(row) > 3 else float(i)
                trajectory.append({"time": time_val, "lat": lat, "lon": lon, "alt": alt})
        return trajectory
    else:
        raise ValueError("Unsupported ownship format. Use 'json' or 'csv'.")

# --- Base and Generator Classes ---

class BaseTrackGenerator:
    def __init__(self, center_lat, center_lon, center_alt,
                 min_alt=None, max_alt=None,
                 track_id=10000, source_id="ARTIFICIAL",
                 track_type="Surveillance", altitude_reference="MSL"):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.center_alt = center_alt
        self.min_alt = min_alt if min_alt is not None else center_alt
        self.max_alt = max_alt if max_alt is not None else center_alt
        self.track_id = track_id  # This will be a 5-digit number (e.g., 10000)
        self.source_id = source_id
        self.track_type = track_type
        self.altitude_reference = altitude_reference
        self.source_track_id = f"{source_id}::{track_id}"
        self.start_time = datetime.now(timezone.utc)

    def _create_track_point(self, lon, lat, alt, time_delta):
        """Creates a dictionary representing a track point."""
        timestamp = self.start_time + timedelta(seconds=time_delta)
        hex_icao = format(random.randint(0x100000, 0xFFFFFF), 'x')
        data_field = f"Hex-ICAO:{hex_icao}|Alt-Baro:{int(alt)}"
        distance = haversine(self.center_lon, self.center_lat, lon, lat)
        # Format trackId as a 5-digit string
        return {
            "eventName": "track.appended",
            "trackId": f"{self.track_id:05d}",
            "sourceId": self.source_id,
            "trackType": self.track_type,
            "timestamp": timestamp.isoformat() + "Z",
            "data": data_field,
            "altitudeReference": self.altitude_reference,
            "sourceTrackId": self.source_track_id,
            "longitude": lon,
            "latitude": lat,
            "altitude": alt,
            "aglAltitude": alt * 0.35,  # Example AGL value
            "mslAltitude": alt,
            "wgs84Altitude": alt - 50,  # Example offset
            "distance_m": distance
        }

    def _get_altitude(self):
        """Randomly choose an altitude between min_alt and max_alt."""
        return random.uniform(self.min_alt, self.max_alt)

    def generate(self, num_points=10, interval_seconds=10):
        """
        Must be implemented by subclasses to generate track points.
        Returns a list of track point dictionaries.
        """
        raise NotImplementedError("Subclasses must implement this method.")

# --- Specific Maneuver Generators ---

class RandomTrackGenerator(BaseTrackGenerator):
    def generate(self, num_points=10, interval_seconds=10):
        points = []
        for i in range(num_points):
            delta_lat = random.uniform(-0.01, 0.01)
            delta_lon = random.uniform(-0.01, 0.01)
            lat = self.center_lat + delta_lat
            lon = self.center_lon + delta_lon
            alt = self._get_altitude()
            time_delta = i * interval_seconds
            points.append(self._create_track_point(lon, lat, alt, time_delta))
        return points

class CircularTrackGenerator(BaseTrackGenerator):
    def __init__(self, center_lat, center_lon, center_alt, radius=0.005, **kwargs):
        super().__init__(center_lat, center_lon, center_alt, **kwargs)
        self.radius = radius

    def generate(self, num_points=20, interval_seconds=10):
        points = []
        for i in range(num_points):
            angle = (2 * math.pi / num_points) * i
            delta_lat = self.radius * math.cos(angle)
            delta_lon = self.radius * math.sin(angle)
            lat = self.center_lat + delta_lat
            lon = self.center_lon + delta_lon
            alt = self._get_altitude()
            time_delta = i * interval_seconds
            points.append(self._create_track_point(lon, lat, alt, time_delta))
        return points

class EllipticalTrackGenerator(BaseTrackGenerator):
    def __init__(self, center_lat, center_lon, center_alt, radius_x=0.01, radius_y=0.005, **kwargs):
        super().__init__(center_lat, center_lon, center_alt, **kwargs)
        self.radius_x = radius_x
        self.radius_y = radius_y

    def generate(self, num_points=20, interval_seconds=10):
        points = []
        for i in range(num_points):
            angle = (2 * math.pi / num_points) * i
            delta_lat = self.radius_y * math.sin(angle)
            delta_lon = self.radius_x * math.cos(angle)
            lat = self.center_lat + delta_lat
            lon = self.center_lon + delta_lon
            alt = self._get_altitude()
            time_delta = i * interval_seconds
            points.append(self._create_track_point(lon, lat, alt, time_delta))
        return points

class FlybyTrackGenerator(BaseTrackGenerator):
    def __init__(self, center_lat, center_lon, center_alt,
                 approach_distance=0.02, exit_distance=0.02, bearing=45, **kwargs):
        super().__init__(center_lat, center_lon, center_alt, **kwargs)
        self.approach_distance = approach_distance
        self.exit_distance = exit_distance
        self.bearing = math.radians(bearing)

    def generate(self, num_points=10, interval_seconds=10):
        points = []
        total_distance = self.approach_distance + self.exit_distance
        for i in range(num_points):
            frac = i / (num_points - 1)
            offset = -self.approach_distance + total_distance * frac
            delta_lat = offset * math.cos(self.bearing)
            delta_lon = offset * math.sin(self.bearing)
            lat = self.center_lat + delta_lat
            lon = self.center_lon + delta_lon
            alt = self._get_altitude()
            time_delta = i * interval_seconds
            points.append(self._create_track_point(lon, lat, alt, time_delta))
        return points

class SquareTrackGenerator(BaseTrackGenerator):
    def __init__(self, center_lat, center_lon, center_alt, side_length=0.02, **kwargs):
        super().__init__(center_lat, center_lon, center_alt, **kwargs)
        self.side_length = side_length

    def generate(self, num_points=12, interval_seconds=10):
        half = self.side_length / 2
        corners = [
            (self.center_lat - half, self.center_lon - half),
            (self.center_lat - half, self.center_lon + half),
            (self.center_lat + half, self.center_lon + half),
            (self.center_lat + half, self.center_lon - half),
        ]
        path = []
        for i in range(len(corners)):
            path.append(corners[i])
            next_corner = corners[(i + 1) % len(corners)]
            mid_lat = (corners[i][0] + next_corner[0]) / 2
            mid_lon = (corners[i][1] + next_corner[1]) / 2
            path.append((mid_lat, mid_lon))
        step = max(1, len(path) // num_points)
        points = []
        for i, (lat, lon) in enumerate(path[::step]):
            alt = self._get_altitude()
            time_delta = i * interval_seconds
            points.append(self._create_track_point(lon, lat, alt, time_delta))
        return points

class RectangleTrackGenerator(BaseTrackGenerator):
    def __init__(self, center_lat, center_lon, center_alt, width=0.03, height=0.01, **kwargs):
        super().__init__(center_lat, center_lon, center_alt, **kwargs)
        self.width = width
        self.height = height

    def generate(self, num_points=12, interval_seconds=10):
        half_w = self.width / 2
        half_h = self.height / 2
        corners = [
            (self.center_lat - half_h, self.center_lon - half_w),
            (self.center_lat - half_h, self.center_lon + half_w),
            (self.center_lat + half_h, self.center_lon + half_w),
            (self.center_lat + half_h, self.center_lon - half_w),
        ]
        path = []
        for i in range(len(corners)):
            path.append(corners[i])
            next_corner = corners[(i + 1) % len(corners)]
            mid_lat = (corners[i][0] + next_corner[0]) / 2
            mid_lon = (corners[i][1] + next_corner[1]) / 2
            path.append((mid_lat, mid_lon))
        step = max(1, len(path) // num_points)
        points = []
        for i, (lat, lon) in enumerate(path[::step]):
            alt = self._get_altitude()
            time_delta = i * interval_seconds
            points.append(self._create_track_point(lon, lat, alt, time_delta))
        return points


class ZigzagTrackGenerator(BaseTrackGenerator):
    def __init__(self, center_lat, center_lon, center_alt, direction=0, amplitude=0.005, frequency=2, **kwargs):
        """
        direction: main heading in degrees.
        amplitude: lateral offset in degrees.
        frequency: number of zigzags over the course of the track.
        """
        super().__init__(center_lat, center_lon, center_alt, **kwargs)
        self.direction = math.radians(direction)
        self.amplitude = amplitude
        self.frequency = frequency

    def generate(self, num_points=10, interval_seconds=10):
        points = []
        total_distance = 0.01  # total progress in degrees along main heading
        for i in range(num_points):
            fraction = i / (num_points - 1) if num_points > 1 else 0
            main_offset = total_distance * fraction
            lateral_offset = self.amplitude * math.sin(2 * math.pi * self.frequency * fraction)
            delta_lat_main = main_offset * math.cos(self.direction)
            delta_lon_main = main_offset * math.sin(self.direction)
            delta_lat_perp = lateral_offset * math.cos(self.direction + math.pi / 2)
            delta_lon_perp = lateral_offset * math.sin(self.direction + math.pi / 2)
            lat = self.center_lat + delta_lat_main + delta_lat_perp
            lon = self.center_lon + delta_lon_main + delta_lon_perp
            alt = self._get_altitude()
            time_delta = i * interval_seconds
            points.append(self._create_track_point(lon, lat, alt, time_delta))
        return points

class SpiralTrackGenerator(BaseTrackGenerator):
    def __init__(self, center_lat, center_lon, center_alt, initial_radius=0.002, radius_increment=0.001, rotations=3, **kwargs):
        """
        initial_radius: starting radius in degrees.
        radius_increment: increase in radius per point (in degrees).
        rotations: total number of rotations over the track.
        """
        super().__init__(center_lat, center_lon, center_alt, **kwargs)
        self.initial_radius = initial_radius
        self.radius_increment = radius_increment
        self.rotations = rotations

    def generate(self, num_points=10, interval_seconds=10):
        points = []
        for i in range(num_points):
            angle = 2 * math.pi * self.rotations * (i / num_points)
            radius = self.initial_radius + self.radius_increment * i
            delta_lat = radius * math.cos(angle)
            delta_lon = radius * math.sin(angle)
            lat = self.center_lat + delta_lat
            lon = self.center_lon + delta_lon
            alt = self._get_altitude()
            time_delta = i * interval_seconds
            points.append(self._create_track_point(lon, lat, alt, time_delta))
        return points

# --- Ownship-Relative Generator ---

class OwnshipRelativeTrackGenerator(BaseTrackGenerator):
    """
    Generates a relative track based on an ownship trajectory.
    Each generated point is offset from the corresponding ownship point by a specified separation.
    """
    def __init__(self, ownship_track, separation_distance, relative_direction="ahead", alt_offset=0, **kwargs):
        super().__init__(center_lat=0, center_lon=0, center_alt=0, **kwargs)
        self.ownship_track = ownship_track
        self.separation_distance = separation_distance  # in meters
        self.relative_direction = relative_direction.lower()
        self.alt_offset = alt_offset
        self.start_time = datetime.now(timezone.utc)
    
    @staticmethod
    def compute_bearing(lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        d_lon = lon2 - lon1
        x = math.sin(d_lon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
        bearing = math.atan2(x, y)
        if bearing < 0:
            bearing += 2 * math.pi
        return bearing

    @staticmethod
    def destination_point(lat, lon, bearing, distance):
        R = 6371000.0  # Earth radius in meters.
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        angular_distance = distance / R
        new_lat = math.asin(math.sin(lat_rad) * math.cos(angular_distance) +
                            math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing))
        new_lon = lon_rad + math.atan2(math.sin(bearing) * math.sin(angular_distance) * math.cos(lat_rad),
                                       math.cos(angular_distance) - math.sin(lat_rad) * math.sin(new_lat))
        return math.degrees(new_lat), math.degrees(new_lon)
    
    def generate(self):
        points = []
        ownship = self.ownship_track
        n = len(ownship)
        previous_bearing = None
        for i, pt in enumerate(ownship):
            lat = pt.get("lat", pt.get("latitude"))
            lon = pt.get("lon", pt.get("longitude"))
            alt = pt.get("alt", pt.get("altitude"))
            time_delta = pt.get("time", i * 10)
            if i < n - 1:
                next_pt = ownship[i + 1]
                lat2 = next_pt.get("lat", next_pt.get("latitude"))
                lon2 = next_pt.get("lon", next_pt.get("longitude"))
                bearing = self.compute_bearing(lat, lon, lat2, lon2)
                previous_bearing = bearing
            elif previous_bearing is not None:
                bearing = previous_bearing
            else:
                bearing = 0.0
            if self.relative_direction == "ahead":
                offset_bearing = bearing
                offset_distance = self.separation_distance
            elif self.relative_direction == "behind":
                offset_bearing = bearing
                offset_distance = -self.separation_distance
            elif self.relative_direction == "opposite":
                offset_bearing = (bearing + math.pi) % (2 * math.pi)
                offset_distance = self.separation_distance
            else:
                offset_bearing = bearing
                offset_distance = self.separation_distance
            new_lat, new_lon = self.destination_point(lat, lon, offset_bearing, offset_distance)
            new_alt = alt + self.alt_offset
            track_point = self._create_track_point(new_lon, new_lat, new_alt, time_delta)
            points.append(track_point)
        return points



class ArtificialTrackGenerator:
    def __init__(self,
                 num_tracks=3,
                 track_generator_class='random',  # Options: random, circular, elliptical, flyby, square, rectangle, zigzag, spiral
                 center_lat=33.75,
                 center_lon=-118.25,
                 center_alt=1000,
                 separation_distance=0.005,  # For independent tracks (in degrees, approx. 0.005° ~ 555 m)
                 time_delay=30,              # Time delay in seconds between tracks
                 min_alt=None,
                 max_alt=None,
                 fly_along=False,            # If True, subsequent tracks are generated relative to the first (leader) track
                 ownship_trajectory_file=None,  # Path to an ownship trajectory file (if fly_along is True)
                 ownship_format="json",         # Format: "json" or "csv"
                 num_points=10,
                 interval_seconds=10):
        self.num_tracks = num_tracks
        self.track_generator_class = track_generator_class.lower()
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.center_alt = center_alt
        self.separation_distance = separation_distance
        self.time_delay = time_delay
        self.min_alt = min_alt if min_alt is not None else center_alt
        self.max_alt = max_alt if max_alt is not None else center_alt
        self.fly_along = fly_along
        self.initial_track_id = 10000  # 5-digit starting ID
        self.ownship_trajectory_file = ownship_trajectory_file
        self.ownship_format = ownship_format
        self.num_points = num_points
        self.interval_seconds = interval_seconds
        self.tracks = []  # List of lists containing track point dictionaries

    def _select_generator(self, **kwargs):
        gen_class = self.track_generator_class
        if gen_class == 'random':
            return RandomTrackGenerator(**kwargs)
        elif gen_class == 'circular':
            return CircularTrackGenerator(**kwargs)
        elif gen_class == 'elliptical':
            return EllipticalTrackGenerator(**kwargs)
        elif gen_class == 'flyby':
            return FlybyTrackGenerator(**kwargs)
        elif gen_class == 'square':
            return SquareTrackGenerator(**kwargs)
        elif gen_class == 'rectangle':
            return RectangleTrackGenerator(**kwargs)
        elif gen_class == 'zigzag':
            return ZigzagTrackGenerator(**kwargs)
        elif gen_class == 'spiral':
            return SpiralTrackGenerator(**kwargs)
        else:
            return RandomTrackGenerator(**kwargs)

    def generate_track(self, track_id, center_lat, center_lon, start_time):
        kwargs = {
            "center_lat": center_lat,
            "center_lon": center_lon,
            "center_alt": self.center_alt,
            "min_alt": self.min_alt,
            "max_alt": self.max_alt,
            "track_id": track_id,
        }
        generator = self._select_generator(**kwargs)
        generator.start_time = start_time
        return generator.generate(num_points=self.num_points, interval_seconds=self.interval_seconds)

    def generate(self):
        base_start_time = datetime.now(timezone.utc)
        tracks = []
        if self.fly_along:
            if self.ownship_trajectory_file:
                ownship_track = load_ownship_trajectory(self.ownship_trajectory_file, self.ownship_format)
            else:
                ownship_track = self.generate_track(track_id=self.initial_track_id,
                                                   center_lat=self.center_lat,
                                                   center_lon=self.center_lon,
                                                   start_time=base_start_time)
            tracks.append(ownship_track)
            for i in range(1, self.num_tracks):
                track_start_time = base_start_time + timedelta(seconds=i * self.time_delay)
                kwargs = {
                    "ownship_track": ownship_track,
                    "separation_distance": self.separation_distance * 111000,  # convert degrees to meters
                    "relative_direction": "ahead",
                    "alt_offset": 0,
                    "track_id": self.initial_track_id + i,
                    "source_id": "ARTIFICIAL",
                    "track_type": "Surveillance",
                    "altitude_reference": "MSL",
                }
                relative_generator = OwnshipRelativeTrackGenerator(**kwargs)
                relative_generator.start_time = track_start_time
                tracks.append(relative_generator.generate())
        else:
            for i in range(self.num_tracks):
                offset_deg = self.separation_distance * i
                track_center_lat = self.center_lat + offset_deg
                track_center_lon = self.center_lon
                track_start_time = base_start_time + timedelta(seconds=i * self.time_delay)
                tracks.append(self.generate_track(track_id=self.initial_track_id + i,
                                                   center_lat=track_center_lat,
                                                   center_lon=track_center_lon,
                                                   start_time=track_start_time))
        self.tracks = tracks
        return tracks

    def save_to_csv(self, filepath):
        """
        Save all generated tracks into a single CSV file.
        """
        if not self.tracks:
            print("No tracks generated to save.")
            return
        fieldnames = [
            "eventName", "trackId", "sourceId", "trackType", "timestamp", "data",
            "altitudeReference", "sourceTrackId", "longitude", "latitude", "altitude",
            "aglAltitude", "mslAltitude", "wgs84Altitude", "distance_m"
        ]
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for track in self.tracks:
                for point in track:
                    writer.writerow(point)
        print(f"Artificial tracks saved to {filepath}")

# --- Example Usage ---
if __name__ == "__main__":
    # Example 1: Independent tracks using a "circular" maneuver.
    generator1 = ArtificialTrackGenerator(
        num_tracks=5,
        track_generator_class='circular',  # Options: random, circular, elliptical, flyby, square, rectangle, zigzag, spiral
        center_lat=34.217411,
        center_lon=-118.491081,
        center_alt=1000,
        separation_distance=0.005,  # In degrees (approx. 555 m per 0.005° latitude)
        time_delay=30,              # 30-second delay between tracks
        min_alt=900,
        max_alt=1100,
        fly_along=False,            # Independent mode
        num_points=20,
        interval_seconds=10
    )
    generator1.generate()
    generator1.save_to_csv("../outputs/output.csv")

    # Example 2: Fly-along mode using an ownship trajectory from a JSON file.
    # Uncomment and update the file path as needed.
    # generator2 = ArtificialTrackGenerator(
    #     num_tracks=3,
    #     track_generator_class='zigzag',  # Options: zigzag, spiral, etc.
    #     center_lat=33.75,
    #     center_lon=-118.25,
    #     center_alt=1000,
    #     separation_distance=0.005,
    #     time_delay=30,
    #     min_alt=900,
    #     max_alt=1100,
    #     fly_along=True,
    #     ownship_trajectory_file="ownship_trajectory.json",
    #     ownship_format="json",
    #     num_points=20,
    #     interval_seconds=10
    # )
    # generator2.generate()
    # generator2.save_to_csv("artificial_tracks_flyalong.csv")

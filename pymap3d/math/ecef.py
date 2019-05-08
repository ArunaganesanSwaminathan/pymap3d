""" Transforms involving ECEF: earth-centered, earth-fixed frame """
from math import radians, sin, cos, tan, hypot, degrees, sqrt, pi
from math import atan as arctan, atan2 as arctan2
from typing import Tuple

tau = 2 * pi

__all__ = ['Ellipsoid', 'geodetic2ecef', 'ecef2geodetic', 'ecef2enuv', 'ecef2enu', 'enu2uvw', 'uvw2enu', 'enu2ecef']


class Ellipsoid:
    """
    generate reference ellipsoid parameters

    https://en.wikibooks.org/wiki/PROJ.4#Spheroid

    https://tharsis.gsfc.nasa.gov/geodesy.html

    https://nssdc.gsfc.nasa.gov/planetary/factsheet/index.html
    """

    def __init__(self, model: str = 'wgs84'):
        """
        feel free to suggest additional ellipsoids

        Parameters
        ----------
        model : str
                name of ellipsoid
        """
        if model == 'wgs84':
            """https://en.wikipedia.org/wiki/World_Geodetic_System#WGS84"""
            self.a = 6378137.  # semi-major axis [m]
            self.f = 1 / 298.2572235630  # flattening
            self.b = self.a * (1 - self.f)  # semi-minor axis
        elif model == 'grs80':
            """https://en.wikipedia.org/wiki/GRS_80"""
            self.a = 6378137.  # semi-major axis [m]
            self.f = 1 / 298.257222100882711243  # flattening
            self.b = self.a * (1 - self.f)  # semi-minor axis
        elif model == 'clrk66':  # Clarke 1866
            self.a = 6378206.4  # semi-major axis [m]
            self.b = 6356583.8  # semi-minor axis
            self.f = -(self.b / self.a - 1)
        elif model == 'mars':  # https://tharsis.gsfc.nasa.gov/geodesy.html
            self.a = 3396900
            self.b = 3376097.80585952
            self.f = 1 / 163.295274386012
        elif model == 'moon':
            self.a = 1738000.
            self.b = self.a
            self.f = 0.
        elif model == 'venus':
            self.a = 6051000.
            self.b = self.a
            self.f = 0.
        elif model == 'pluto':
            self.a = 1187000.
            self.b = self.a
            self.f = 0.
        else:
            raise NotImplementedError('{} model not implemented, let us know and we will add it (or make a pull request)'.format(model))


def get_radius_normal(lat_radians: float, ell: Ellipsoid = None) -> float:
    """
    Compute normal radius of planetary body

    Parameters
    ----------

    lat_radians : float
        latitude in radians
    ell : Ellipsoid, optional
        reference ellipsoid

    Returns
    -------

    radius : float
        normal radius (meters)
    """
    if ell is None:
        ell = Ellipsoid()

    a = ell.a
    b = ell.b

    return a**2 / sqrt(a**2 * cos(lat_radians)**2 + b**2 * sin(lat_radians)**2)


def geodetic2ecef(lat: float, lon: float, alt: float,
                  ell: Ellipsoid = None, deg: bool = True) -> Tuple[float, float, float]:
    """
    point transformation from Geodetic of specified ellipsoid (default WGS-84) to ECEF

    Parameters
    ----------

    lat : float
           target geodetic latitude
    lon : float
           target geodetic longitude
    h : float
         target altitude above geodetic ellipsoid (meters)
    ell : Ellipsoid, optional
          reference ellipsoid
    deg : bool, optional
          degrees input/output  (False: radians in/out)


    Returns
    -------

    ECEF (Earth centered, Earth fixed)  x,y,z

    x : float
        target x ECEF coordinate (meters)
    y : float
        target y ECEF coordinate (meters)
    z : float
        target z ECEF coordinate (meters)
    """
    if ell is None:
        ell = Ellipsoid()

    if deg:
        lat = radians(lat)
        lon = radians(lon)

    if (lat < -pi / 2) | (lat > pi / 2):
        raise ValueError('-90 <= lat <= 90')

    # radius of curvature of the prime vertical section
    N = get_radius_normal(lat, ell)
    # Compute cartesian (geocentric) coordinates given  (curvilinear) geodetic
    # coordinates.
    x = (N + alt) * cos(lat) * cos(lon)
    y = (N + alt) * cos(lat) * sin(lon)
    z = (N * (ell.b / ell.a)**2 + alt) * sin(lat)

    return x, y, z


def ecef2geodetic(x: float, y: float, z: float,
                  ell: Ellipsoid = None, deg: bool = True) -> Tuple[float, float, float]:
    """
    convert ECEF (meters) to geodetic coordinates

    Parameters
    ----------
    x : float
        target x ECEF coordinate (meters)
    y : float
        target y ECEF coordinate (meters)
    z : float
        target z ECEF coordinate (meters)
    ell : Ellipsoid, optional
          reference ellipsoid
    deg : bool, optional
          degrees input/output  (False: radians in/out)

    Returns
    -------
    lat : float
           target geodetic latitude
    lon : float
           target geodetic longitude
    h : float
         target altitude above geodetic ellipsoid (meters)

    based on:
    You, Rey-Jer. (2000). Transformation of Cartesian to Geodetic Coordinates without Iterations.
    Journal of Surveying Engineering. doi: 10.1061/(ASCE)0733-9453
    """
    if ell is None:
        ell = Ellipsoid()

    r = sqrt(x**2 + y**2 + z**2)

    E = sqrt(ell.a**2 - ell.b**2)

    # eqn. 4a
    u = sqrt(0.5 * (r**2 - E**2) + 0.5 * sqrt((r**2 - E**2)**2 + 4 * E**2 * z**2))

    Q = hypot(x, y)

    huE = hypot(u, E)

    # eqn. 4b
    Beta = arctan(huE / u * z / hypot(x, y))

    # eqn. 13
    eps = ((ell.b * u - ell.a * huE + E**2) * sin(Beta)) / (ell.a * huE * 1 / cos(Beta) - E**2 * cos(Beta))

    Beta += eps
# %% final output
    lat = arctan(ell.a / ell.b * tan(Beta))

    lon = arctan2(y, x)

    # eqn. 7
    alt = hypot(z - ell.b * sin(Beta),
                Q - ell.a * cos(Beta))

    # inside ellipsoid?
    inside = x**2 / ell.a**2 + y**2 / ell.a**2 + z**2 / ell.b**2 < 1
    if inside:
        alt = -alt

    if deg:
        lat = degrees(lat)
        lon = degrees(lon)

    return lat, lon, alt


def ecef2enuv(u: float, v: float, w: float,
              lat0: float, lon0: float, deg: bool = True) -> Tuple[float, float, float]:
    """
    VECTOR from observer to target  ECEF => ENU

    Parameters
    ----------
    u : float
        target x ECEF coordinate (meters)
    v : float
        target y ECEF coordinate (meters)
    w : float
        target z ECEF coordinate (meters)
    lat0 : float
           Observer geodetic latitude
    lon0 : float
           Observer geodetic longitude
    h0 : float
         observer altitude above geodetic ellipsoid (meters)
    deg : bool, optional
          degrees input/output  (False: radians in/out)

    Returns
    -------
    uEast : float
        target east ENU coordinate (meters)
    vNorth : float
        target north ENU coordinate (meters)
    wUp : float
        target up ENU coordinate (meters)

    """
    if deg:
        lat0 = radians(lat0)
        lon0 = radians(lon0)

    t = cos(lon0) * u + sin(lon0) * v
    uEast = -sin(lon0) * u + cos(lon0) * v
    wUp = cos(lat0) * t + sin(lat0) * w
    vNorth = -sin(lat0) * t + cos(lat0) * w

    return uEast, vNorth, wUp


def ecef2enu(x: float, y: float, z: float,
             lat0: float, lon0: float, h0: float,
             ell: Ellipsoid = None, deg: bool = True) -> Tuple[float, float, float]:
    """
    from observer to target, ECEF => ENU

    Parameters
    ----------
    x : float
        target x ECEF coordinate (meters)
    y : float
        target y ECEF coordinate (meters)
    z : float
        target z ECEF coordinate (meters)
    lat0 : float
           Observer geodetic latitude
    lon0 : float
           Observer geodetic longitude
    h0 : float
         observer altitude above geodetic ellipsoid (meters)
    ell : Ellipsoid, optional
          reference ellipsoid
    deg : bool, optional
          degrees input/output  (False: radians in/out)

    Returns
    -------
    East : float
        target east ENU coordinate (meters)
    North : float
        target north ENU coordinate (meters)
    Up : float
        target up ENU coordinate (meters)

    """
    x0, y0, z0 = geodetic2ecef(lat0, lon0, h0, ell, deg=deg)

    return uvw2enu(x - x0, y - y0, z - z0, lat0, lon0, deg=deg)


def enu2uvw(east: float, north: float, up: float,
            lat0: float, lon0: float, deg: bool = True) -> Tuple[float, float, float]:
    """
    Parameters
    ----------

    e1 : float
        target east ENU coordinate (meters)
    n1 : float
        target north ENU coordinate (meters)
    u1 : float
        target up ENU coordinate (meters)

    Results
    -------

    u : float
    v : float
    w : float
    """

    if deg:
        lat0 = radians(lat0)
        lon0 = radians(lon0)

    t = cos(lat0) * up - sin(lat0) * north
    w = sin(lat0) * up + cos(lat0) * north

    u = cos(lon0) * t - sin(lon0) * east
    v = sin(lon0) * t + cos(lon0) * east

    return u, v, w


def uvw2enu(u: float, v: float, w: float,
            lat0: float, lon0: float, deg: bool = True) -> Tuple[float, float, float]:
    """
    Parameters
    ----------

    u : float
    v : float
    w : float


    Results
    -------

    East : float
        target east ENU coordinate (meters)
    North : float
        target north ENU coordinate (meters)
    Up : float
        target up ENU coordinate (meters)
    """
    if deg:
        lat0 = radians(lat0)
        lon0 = radians(lon0)

    t = cos(lon0) * u + sin(lon0) * v
    East = -sin(lon0) * u + cos(lon0) * v
    Up = cos(lat0) * t + sin(lat0) * w
    North = -sin(lat0) * t + cos(lat0) * w

    return East, North, Up


def enu2ecef(e1: float, n1: float, u1: float,
             lat0: float, lon0: float, h0: float,
             ell: Ellipsoid = None, deg: bool = True) -> Tuple[float, float, float]:
    """
    ENU to ECEF

    Parameters
    ----------

    e1 : float
        target east ENU coordinate (meters)
    n1 : float
        target north ENU coordinate (meters)
    u1 : float
        target up ENU coordinate (meters)
    lat0 : float
           Observer geodetic latitude
    lon0 : float
           Observer geodetic longitude
    h0 : float
         observer altitude above geodetic ellipsoid (meters)
    ell : Ellipsoid, optional
          reference ellipsoid
    deg : bool, optional
          degrees input/output  (False: radians in/out)


    Results
    -------
    x : float
        target x ECEF coordinate (meters)
    y : float
        target y ECEF coordinate (meters)
    z : float
        target z ECEF coordinate (meters)
    """
    x0, y0, z0 = geodetic2ecef(lat0, lon0, h0, ell, deg=deg)
    dx, dy, dz = enu2uvw(e1, n1, u1, lat0, lon0, deg=deg)

    return x0 + dx, y0 + dy, z0 + dz
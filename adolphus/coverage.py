"""\
Coverage model module.

@author: Aaron Mavrinac
@organization: University of Windsor
@contact: mavrin1@uwindsor.ca
@license: GPL-3
"""

from math import sqrt, sin, cos, atan, pi
from numbers import Number
from itertools import combinations
from fuzz import IndexedSet, TrapezoidalFuzzyNumber, FuzzySet, FuzzyElement

from geometry import Point, DirectionalPoint, Pose
from scene import Scene

try:
    import visual
    VIS = True
except ImportError:
    VIS = False


class Camera(object):
    """\
    Single-camera model, using continous fuzzy sets.
    """
    def __init__(self, A, f, s, o, dim, zS, gamma, r1, r2, cmax, zeta,
                 pose = Pose()):
        """\
        Constructor.

        @param A: Aperture size (intrinsic).
        @type A: C{float}
        @param f: Focal length (intrinsic).
        @type f: C{float}
        @param s: Effective pixel size (intrinsic).
        @type s: C{tuple} of C{float}
        @param o: Pixel coordinates of principal point (intrinsic).
        @type o: C{tuple} of C{float}
        @param dim: Sensor pixel dimensions (intrinsic).
        @type dim: C{int}
        @param zS: Subject distance (intrinsic).
        @type zS: C{float}
        @param gamma: Fuzzification value for visibility (application).
        @type gamma: C{float}
        @param r1: Fully acceptable resolution (application).
        @type r1: C{float}
        @param r2: Acceptable resolution (application).
        @type r2: C{float}
        @param cmax: Maximum acceptable circle of confusion (application).
        @type cmax: C{float}
        @param zeta: Fuzzification value for direction (application).
        @type zeta: C{float}
        @param pose: Pose of the camera in space (optional).
        @type pose: L{geometry.Pose}
        """
        if isinstance(s, Number):
            s = (s, s)

        # fuzzy sets for visibility
        self.Cv, al, ar = [], [], []
        for i in range(2):
            al.append(2.0 * atan((o[i] * s[i]) / (2.0 * f)))
            ar.append(2.0 * atan(((dim[i] - o[i]) * s[i]) / (2.0 * f)))
            g = (gamma / float(dim[i])) * 2.0 * sin((al[i] + ar[i]) / 2.0)
            self.Cv.append(TrapezoidalFuzzyNumber((-sin(al[i]) + g,
                sin(ar[i]) - g), (-sin(al[i]), sin(ar[i]))))

        # fuzzy set for resolution
        mr = min([float(dim[i]) / (2.0 * sin((al[i] + ar[i]) / 2.0)) \
                  for i in range(2)])
        zr1 = (1.0 / r1) * mr
        zr2 = (1.0 / r2) * mr
        self.Cr = TrapezoidalFuzzyNumber((0, zr1), (0, zr2))

        # fuzzy set for focus
        zl = (A * f * zS) / (A * f + min(s) * (zS - f))
        zr = (A * f * zS) / (A * f - min(s) * (zS - f))
        zn = (A * f * zS) / (A * f + cmax * (zS - f))
        zf = (A * f * zS) / (A * f - cmax * (zS - f))
        self.Cf = TrapezoidalFuzzyNumber((zl, zr), (zn, zf))

        # fuzzifier for direction
        self.zeta = zeta
        
        # pose
        self.pose = pose

    def mu(self, point):
        """\
        Return the membership degree (coverage) for a directional point.
    
        @param point: The (directional) point to test.
        @type point: L{geometry.Point}
        @return: The membership degree (coverage) of the point.
        @rtype: C{float}
        """
        if not isinstance(point, Point):
            raise TypeError("invalid point")

        campoint = (-self.pose).map(point)

        # visibility
        try:
            mu_v = min([Cv.mu(campoint.x / campoint.z) for Cv in self.Cv])
        except ZeroDivisionError:
            mu_v = 0.0

        # resolution
        mu_r = self.Cr.mu(campoint.z)

        # focus
        mu_f = self.Cf.mu(campoint.z)

        # direction
        if isinstance(campoint, DirectionalPoint):
            r = sqrt(campoint.x ** 2 + campoint.y ** 2)
            try:
                terma = (campoint.y / r) * sin(campoint.eta) + \
                        (campoint.x / r) * cos(campoint.eta)
            except ZeroDivisionError:
                terma = 1.0
            try:
                termb = atan(r / campoint.z)
            except ZeroDivisionError:
                termb = pi / 2.0
            mu_d = min(max((float(campoint.rho) - ((pi / 2.0) + terma \
                * termb)) / self.zeta, 0.0), 1.0)
        else:
            mu_d = 1.0

        # algebraic product intersection
        return mu_v * mu_r * mu_f * mu_d

    def visualize(self, scale = 1.0, color = (1, 1, 1)):
        """\
        Plot the camera in a 3D visual model.

        @param scale: The scale of the camera.
        @type scale: C{float}
        @param color: The color in which to plot the point.
        @type color: C{tuple}
        """
        if not VIS:
            raise ImportError("visual module not loaded")
        visual.pyramid(pos = self.pose.T.tuple, axis = \
            self.pose.map_rotate(Point(0, 0, -scale)).tuple, \
            size = (scale, scale, scale), color = color)


class MultiCamera(dict):
    """\
    Multi-camera n-ocular fuzzy coverage model.
    """
    def __init__(self, ocular = 1, scene = Scene(), points = set()):
        """\
        Constructor.
    
        @param ocular: Mutual camera coverage degree.
        @type ocular: C{int}
        @param scene: The discrete scene model.
        @type scene: L{Scene}
        @param points: The initial set of points.
        @type points: C{set} of L{geometry.Point}
        """
        if ocular < 1:
            raise ValueError("network must be at least 1-ocular")
        self.ocular = ocular
        self.scene = scene
        self.points = points
        self.model = FuzzySet()
        self.model_updated = False

    def __setitem__(self, key, value):
        """\
        Add a new camera to the network, and update its in-scene model.

        @param key: The key of the item to assign.
        @type key: C{object}
        @param value: The Camera object to assign.
        @type value: L{Camera}
        """
        if not isinstance(value, Camera):
            raise ValueError("item to add must be a Camera object")
        dict.__setitem__(self, key, value)
        self.update_inscene(key)

    def add_point(self, point):
        """\
        Update a single (directional) point in the model, for all cameras, with
        occlusion.

        @param point: The directional point.
        @type point: L{geometry.Point}
        """
        self.points.add(point)
        for key in self.keys():
            mu = self[key].mu(point)
            if mu > 0 and not self.scene.occluded(point, self[key].pose.T):
                self[key].inscene |= FuzzySet([FuzzyElement(point, mu)])

    def update_inscene(self, key):
        """\
        Update an individual in-scene camera fuzzy set (with occlusion).

        @param key: The name of the camera to update.
        @type key: C{str}
        """
        mpoints = []
        for point in self.points:
            mu = self[key].mu(point)
            if mu > 0 and not self.scene.occluded(point, self[key].pose.T):
                mpoints.append(FuzzyElement(point, mu))
        self[key].inscene = FuzzySet(mpoints)
        self.model_updated = False

    def update_model(self):
        """\
        Update the n-ocular multi-camera network discrete coverage model.
        """
        if len(self) < self.ocular:
            raise ValueError("network has too few cameras")
        self.model = FuzzySet()
        submodels = []
        for combination in combinations(self.keys(), self.ocular):
            submodels.append(self[combination[0]].inscene)
            for i in range(1, self.ocular):
                submodels[-1] &= self[combination[i]].inscene
        for submodel in submodels:
            self.model |= submodel
        self.model_updated = True

    def mu(self, point):
        """\
        Return the individual membership degree of a point in the fuzzy
        coverage model.

        @param point: The (directional) point to test.
        @type point: L{geometry.Point}
        @return: The membership degree (coverage) of the point.
        @rtype: C{float}
        """
        if len(self) < self.ocular:
            raise ValueError("network has too few cameras")
        if point in self.model:
            return self.model.mu(point)
        else:
            return max([min([self[camera].mu(point) for camera in combination])
                        for combination in combinations(self.keys(), n)])

    def performance(self, desired):
        """\
        Return the coverage performance of this multi-camera network.

        @param desired: The D model of desired coverage.
        @type desired: L{fuzz.FuzzySet}
        @return: Performance metric in [0, 1].
        @rtype: C{float}
        """
        return self.model.overlap(desired)

    def visualize(self, scale = 1.0, color = (1, 1, 1)):
        """\
        Visualize all cameras and the directional points of the coverage model
        (with opacity reflecting degree of coverage).

        @param scale: The scale of the individual elements.
        @type scale: C{float}
        @param color: The color of cameras.
        @type color: C{tuple}
        """
        if not VIS:
            raise ImportError("visual module not loaded")
        for camera in self:
            self[camera].visualize(scale = scale, color = color)
        self.scene.visualize(color = color)
        for point in self.model.keys():
            point.visualize(scale = scale, color = (1, 0, 0),
                            opacity = self.model[point].mu)
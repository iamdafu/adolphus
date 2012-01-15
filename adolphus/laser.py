"""\
Laser range imaging module. Contains extensions and objects necessary for
modeling laser line based range imaging cameras.

@author: Aaron Mavrinac
@organization: University of Windsor
@contact: mavrin1@uwindsor.ca
@license: GPL-3
"""

from math import pi, sin, tan

from .geometry import Angle, Pose, Point, DirectionalPoint, Triangle
from .coverage import PointCache, Task, Camera, Model
from .posable import SceneObject


class LineLaser(SceneObject):
    """\
    Line laser class.
    """
    def __init__(self, name, fan, depth, pose=Pose(), mount_pose=Pose(),
                 mount=None, primitives=[], triangles=[]):
        """\
        Constructor.

        @param name: The name of the laser.
        @type name: C{str}
        @param fan: Fan angle of the laser line.
        @type fan: L{Angle}
        @param depth: Projection depth of the laser line.
        @type depth: C{float}
        @param pose: Pose of the laser in space (optional).
        @type pose: L{Pose}
        @param mount_pose: The transformation to the mounting end (optional).
        @type mount_pose: L{Pose}
        @param mount: Mount object for the laser (optional).
        @type mount: C{object}
        @param primitives: Sprite primitives for the laser.
        @type primitives: C{dict}
        @param triangles: The opaque triangles of this laser (optional).
        @type triangles: C{list} of L{OcclusionTriangle}
        """
        super(LineLaser, self).__init__(name, pose=pose, mount_pose=mount_pose,
            mount=mount, primitives=primitives, triangles=triangles)
        self._fan = Angle(fan)
        self._depth = depth
        self.click_actions = {'shift':  'modify %s' % name}

    def _pose_changed_hook(self):
        """\
        Hook called on pose change.
        """
        try:
            del self._triangle
        except AttributeError:
            pass
        super(LineLaser, self)._pose_changed_hook()

    @property
    def fan(self):
        """\
        Fan angle.
        """
        return self._fan

    @property
    def depth(self):
        """\
        Projection depth.
        """
        return self._depth

    def occluded_by(self, triangle, task_params):
        """\
        Return whether this laser's projection plane is occluded (in part) by
        the specified triangle.

        @param triangle: The triangle to check.
        @type triangle: L{OcclusionTriangle}
        @param task_params: Task parameters (not used).
        @type task_params: C{dict}
        @return: True if occluded.
        @rtype: C{bool}
        """
        # TODO: should these be cached?
        width = self._depth * tan(self._fan / 2.0)
        laser_triangle = Triangle((self.pose.T,
            self.pose.map(Point((-width, 0, self._depth))),
            self.pose.map(Point((width, 0, self._depth)))))
        return laser_triangle.overlap(triangle.mapped_triangle)


class RangeCamera(Camera):
    """\
    Single-camera coverage strength model for laser line based range camera.
    """
    def zres(self, resolution):
        """\
        Return the depth at which the specified resolution occurs. In a range
        camera, only horizontal resolution is considered (and the resolution
        coverage component behaves accordingly).

        @param resolution: Horizontal resolution in millimeters per pixel.
        @type resolution: C{float}
        @return: Depth (distance along camera M{z}-axis).
        @rtype: C{float}
        """
        try:
            return self._mr / resolution
        except ZeroDivisionError:
            return float('inf')
        except AttributeError:
            self._mr = float(self._params['dim'][0]) / self.fov['2sah2']
            return self.zres(resolution)

    def ch(self, p, tp):
        """\
        Height resolution component of the coverage function. Returns zero
        coverage for non-directional points as it is intended for use in range
        coverage only.

        @param p: The point to test.
        @type p: L{Point}
        @param tp: Task parameters.
        @type tp: C{dict}
        @return: The height resolution coverage component value in M{[0, 1]}.
        @rtype: C{float}
        """
        try:
            ascale = sin(p.direction_unit.angle(-p))
        except AttributeError:
            return 0.0
        mr = ascale * float(self._params['dim'][1]) / self.fov['2sav2']
        zhres = lambda resolution: mr / resolution
        try:
            zhmini = zhres(tp['hres_min_ideal'])
        except ZeroDivisionError:
            zhmini = float('inf')
        try:
            zhmina = zhres(tp['hres_min_acceptable'])
        except ZeroDivisionError:
            zhmina = float('inf')
        if zhmina == zhmini:
            return float(p.z < zhmina)
        else:
            return min(max((zhmina - p.z) / (zhmina - zhmini), 0.0), 1.0)

    def strength(self, point, task_params):
        """\
        Return the coverage strength for a directional point. Includes the
        height resolution component.

        @param point: The (directional) point to test.
        @type point: L{Point}
        @param task_params: Task parameters.
        @type task_params: C{dict}
        @return: The coverage strength of the point.
        @rtype: C{float}
        """
        cp = (-self.pose).map(point)
        return self.cv(cp, task_params) * self.cr(cp, task_params) \
             * self.cf(cp, task_params) * self.cd(cp, task_params) \
             * self.ch(cp, task_params)


class RangeModel(Model):
    """\
    Multi-camera coverage strength model for laser line based range imaging.

    In addition to the base L{Model} functionality, a L{RangeModel} manages
    line lasers and laser occlusion, and provides range imaging coverage
    methods.
    """
    # class of camera handled by this model class
    camera_class = RangeCamera
    # object types for which occlusion caching is handled by this class
    oc_sets = ['cameras', 'lasers']

    def __init__(self):
        self.lasers = set()
        super(RangeModel, self).__init__()

    def __setitem__(self, key, value):
        if isinstance(value, LineLaser):
            self.lasers.add(key)
        super(RangeModel, self).__setitem__(key, value)

    def __delitem__(self, key):
        self.lasers.discard(key)
        super(RangeModel, self).__delitem__(key)

    def project(self, task_params, laser, target, lpitch):
        """\
        Generate a range imaging task model by projecting the specified laser
        line onto the target object.

        @param task_params: Task parameters.
        @type task_params: C{dict}
        @param laser: The ID of the laser line generator to use.
        @type laser: C{str}
        @param target: The target object ID.
        @type target: C{str}
        @param lpitch: The horizontal pitch of task model points.
        @type lpitch: C{float}
        @return: The generated range imaging task model.
        @rtype: L{Task}
        """
        if not laser in self.lasers:
            raise KeyError('invalid laser')
        points = PointCache()
        width = self[laser].depth * tan(self[laser].fan / 2.0)
        x = int(-width / lpitch) * lpitch
        while x < width:
            cp = None
            origin = self[laser].pose.map(Point((x, 0, 0)))
            end = self[laser].pose.map(Point((x, 0, self[laser].depth)))
            for triangle in self[target].triangles:
                ip = triangle.intersection(origin, end)
                if ip:
                    ip = (-self[laser].pose).map(ip)
                else:
                    continue
                if abs(ip.x) > ip.z * tan(self[laser].fan / 2.0):
                    continue
                elif not cp or ip.z < cp.z:
                    cp = Point(ip)
            if cp and not self.occluded(self[laser].pose.map(cp), laser):
                points[DirectionalPoint(tuple(cp) + (pi, 0))] = 1.0
            x += lpitch
        return Task(task_params, points, mount=self[laser])

    def range_coverage(self, task, laser, target, lpitch, tpitch, taxis,
                       tstyle='linear', subset=None):
        """\
        Move the specified target object through the plane of the specified
        laser, generate profile task models by projection, and return the
        overall coverage and task models in the original target pose. The target
        motion is based on the original pose and may be linear or rotary.

        @param task: The range coverage task.
        @type task: L{Task}
        @param laser: The ID of the laser line generator to use.
        @type laser: C{str}
        @param target: The target object ID.
        @type target: C{str}
        @param lpitch: The horizontal laser projection pitch in distance units.
        @type lpitch: C{float}
        @param tpitch: The transport pitch in distance units or radians.
        @type tpitch: C{float} or L{Angle}
        @param taxis: The transport axis and (rotary only) target center point.
        @type taxis: L{Point} or C{tuple} of L{Point}
        @param tstyle: The transport style (linear or rotary).
        @type tstyle: C{str}
        @param subset: Subset of cameras (defaults to all active cameras).
        @type subset: C{set}
        @return: The coverage and task models.
        @rtype: L{PointCache}, L{Task}
        """
        coverage, task_original = PointCache(), PointCache()
        original_pose = self[target].pose
        if tstyle == 'linear':
            # find least and greatest triangle vertices along taxis
            taxis = taxis.normal
            lv, gv = float('inf'), -float('inf')
            for triangle in self[target].triangles:
                for vertex in triangle.mapped_triangle.vertices:
                    pv = taxis * vertex
                    lv = min(lv, pv)
                    gv = max(gv, pv)
            steps = int((gv - lv) / float(tpitch))
            for i in range(steps):
                # get coverage of profile
                self[target].set_absolute_pose(original_pose + \
                    Pose(T=((tpitch * i - gv) * taxis)))
                prof_task = self.project(task.params, laser, target, lpitch)
                prof_coverage = self.coverage(prof_task, subset=subset)
                # add to main coverage result
                for point in prof_coverage:
                    original_point = \
                        (-self[target].pose + original_pose).map(point)
                    coverage[original_point] = prof_coverage[point]
                    task_original[original_point] = 1.0
        elif tstyle == 'rotary':
            #steps = int(2 * pi / float(tpitch))
            # TODO: the rest...
            raise ValueError('rotary transport style not yet implemented')
        else:
            raise ValueError('transport style must be \'linear\' or \'rotary\'')
        self[target].set_absolute_pose(original_pose)
        task = Task(task.params, task_original)
        return coverage, task

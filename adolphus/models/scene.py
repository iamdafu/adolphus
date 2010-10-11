from ..geometry import Point, Pose, Plane
from ..visualization import visual, VisualizationObject, VisualizationError


class VisionPlatform(object):
    """\
    Scene object for the vision platform.
    """
    def __init__(self, pose=Pose()):
        """\
        Constructor.

        @param pose: The pose of the plane normal (from z-hat).
        @type pose: L{Pose}
        """
        self.pose = pose
        self.center = pose.T

    def intersection(self, pa, pb):
        """\
        Return the 3D point of intersection (if any) of the line segment
        between the two specified points and this object.

        @param pa: The first vertex of the line segment.
        @type pa: L{Point}
        @param pb: The second vertex of the line segment.
        @type pb: L{Point}
        @return: The point of intersection with the object.
        @rtype: L{Point}
        """
        planes = set()
        # top
        planes.add(Plane(pose=(self.pose + Pose(T=Point(1285, 460, 1775))),
            x=(-1265, 1265), y=(-430, 430)))
        # steel
        planes.add(Plane(pose=(self.pose + Pose(T=Point(1590, 460, 535))),
            x=(-950, 950), y=(-430, 430)))
        return reduce(lambda a, b: a or b, [plane.intersection(pa, pb) \
            for plane in planes])

    def visualize(self, scale=None, color=None, opacity=1.0):
        """\
        Create a 3D visual model of the object.

        @param scale: Not used.
        @type scale: C{object}
        @param color: Not used.
        @type color: C{object}
        @param opacity: The opacity of the visualization.
        @type opacity: C{float}
        """
        if not visual:
            raise VisualizationError("visual module not loaded")
        self.vis = VisualizationObject(self)
        for x in [20, 1280, 2550]:
            for y in [20, 900]:
                self.vis.add('bar%d%d' % (x, y), visual.box(frame=self.vis,
                    pos=(x, y, 885), length=40, width=1770, height=40,
                    color=(1, 0.5, 0), opacity=opacity,
                    material=visual.materials.plastic))
                if x == 1280:
                    continue
                self.vis.add('wheel%d%d' % (x, y), visual.cylinder(frame=\
                    self.vis, pos=(x, y - 12, -60), axis=(0, 24, 0), radius=50,
                    color=(0.1, 0.1, 0.1), opacity=opacity,
                    material=visual.materials.rough))
        for y in [20, 900]:
            for z in [20, 510, 1750]:
                self.vis.add('bar%d%d' % (y, z), visual.box(frame=self.vis,
                    pos=(1285, y, z), length=2570, width=40, height=40,
                    color=(1, 0.5, 0), opacity=opacity,
                    material=visual.materials.plastic))
        for x in [20, 1280, 2550]:
            for z in [20, 510, 1750]:
                self.vis.add('bar%d%d' % (x, z), visual.box(frame=self.vis,
                    pos=(x, 460, z), length=40, width=40, height=920,
                    color=(1, 0.5, 0), opacity=opacity,
                    material=visual.materials.plastic))
        self.vis.add('top', visual.box(frame=self.vis, pos=(1285, 460, 1775),
            length=2530, width=10, height=860, color=(0.1, 0.1, 0.1),
            opacity=opacity, material=visual.materials.plastic))
        self.vis.add('steel', visual.box(frame=self.vis, pos=(1590, 460, 535),
            length=1900, width=10, height=860, color=(0.6, 0.6, 0.6),
            opacity=opacity, material=visual.materials.rough))
        self.vis.add('wood', visual.box(frame=self.vis, pos=(650, 460, 49.5),
            length=1240, width=19, height=860, color=(0.91, 0.85, 0.64),
            opacity=opacity, material=visual.materials.wood))
        self.vis.transform(self.pose)


class CheckerCalibrationBoard(object):
    """\
    Scene object for the checkerboard pattern calibration target.
    """
    def __init__(self, pose=Pose()):
        """\
        Constructor.

        @param pose: The pose of the plane normal (from z-hat).
        @type pose: L{Pose}
        """
        self.pose = pose
        self.center = pose.T
    
    def intersection(self, pa, pb):
        """\
        Return the 3D point of intersection (if any) of the line segment
        between the two specified points and this object.

        @param pa: The first vertex of the line segment.
        @type pa: L{Point}
        @param pb: The second vertex of the line segment.
        @type pb: L{Point}
        @return: The point of intersection with the object.
        @rtype: L{Point}
        """
        plane = Plane(pose=pose, x=(-138, 174), y=(-111, 115))
        pr = plane.intersection(pa, pb)
        prlocal = (-self.pose).map(pr)
        if prlocal.x > 276 and prlocal.y > -55 and prlocal.y < 57:
            return None
        return pr

    def visualize(self, scale=None, color=None, opacity=1.0):
        """\
        Create a 3D visual model of the object.

        @param scale: Not used.
        @type scale: C{object}
        @param color: Not used.
        @type color: C{object}
        @param opacity: The opacity of the visualization.
        @type opacity: C{float}
        """
        if not visual:
            raise VisualizationError("visual module not loaded")
        self.vis = VisualizationObject(self)
        self.vis.add('bm', visual.box(frame=self.vis, pos=(0, 2, 0),
            length=276, width=2, height=226, color=(0.74, 0.67, 0.53),
            opacity=opacity, material=visual.materials.wood))
        self.vis.add('bl', visual.box(frame=self.vis, pos=(156, -83, 0),
            length=36, width=2, height=56, color=(0.74, 0.67, 0.53),
            opacity=opacity, material=visual.materials.wood))
        self.vis.add('br', visual.box(frame=self.vis, pos=(156, 86, 0),
            length=36, width=2, height=58, color=(0.74, 0.67, 0.53),
            opacity=opacity, material=visual.materials.wood))
        for x in range(-7, 7):
            for y in range(-5, 5):
                self.vis.add('c%d%d' % (x, y), visual.box(frame=self.vis,
                    pos=(9.5 + 19 * x, 9.5 + 19 * y, 1), length=19, width=1.2,
                    height=19, color=((x + y) % 2, (x + y) % 2, (x + y) % 2),
                    opacity=opacity))
        self.vis.transform(self.pose)

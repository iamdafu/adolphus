from math import pi
from fuzz import RealRange

from ..geometry import Pose, Point, Rotation, Angle, Posable
from ..visualization import visual, VisualizationObject, VisualizationError


class MitsubishiRV1A(Posable):
    """\
    Mitsubishi RV-1A six-axis robotic arm.
    """
    def __init__(self, pose=Pose(), mount=None, config=None):
        """\
        Constructor.

        @param position: The joint position of the robot.
        @type position: C{tuple} of C{float}
        """
        Posable.__init__(self, pose=pose, mount=mount, config=config)

    @property
    def config(self):
        """\
        The configuration of the robot.

        @rtype: C{list}
        """
        return [self.tool_length] + list(self.position)

    @config.setter
    def config(self, value):
        """\
        Set the configuration of the robot.

        @param value: The configuration of the robot.
        @type value: C{list}
        """
        self.tool_length = value[0]
        self.position = tuple(value[1:])

    @property
    def position(self):
        """\
        The position of the robot.

        @rtype: C{tuple} of C{float}
        """
        return self._position

    @position.setter
    def position(self, value):
        """\
        Set the position of the robot.

        @param value: The joint position of the robot.
        @type value: C{tuple} of C{float}
        """
        if not value:
            self._position = (0.0, 0.0, 90.0, 0.0, 0.0, 0.0)
        elif self.validate(value):
            self._position = value
        else:
            raise ValueError("invalid robot position")

    @staticmethod
    def validate(position):
        """\
        Validate a robot position.

        @param position: The joint position of the robot.
        @type position: C{tuple} of C{float}
        @return: True if valid, false otherwise.
        @rtype: C{bool}
        """
        if not len(position) == 6:
            return False
        range = [RealRange((-150, 150)),
                 RealRange((-60, 120)),
                 RealRange((60, 155)),
                 RealRange((-160, 160)),
                 RealRange((-90, 90)),
                 RealRange((-200, 200))]
        return all([angle in range[i] for i, angle in enumerate(position)])
   
    def joint_poses(self):
        """\
        Return the 3D transformations for each joint angle.

        @return: The individual joint poses.
        @rtype: C{tuple} of L{Pose}
        """
        rpos = tuple([Angle(j * pi / 180) for j in self.position])
        EE = Pose(T=Point(0, 0, 19.3 + self.tool_length))
        J6 = Pose(T=Point(0, 0, 52.7),
            R=Rotation(Rotation.from_axis_angle(rpos[5], (0, 0, 1))))
        J5 = Pose(T=Point(0, 0, 117.0),
            R=Rotation(Rotation.from_axis_angle(rpos[4], (0, 1, 0))))
        J4 = Pose(T=Point(-90.0, 0, 43.0),
            R=Rotation(Rotation.from_axis_angle(rpos[3], (0, 0, 1))))
        J3 = Pose(T=Point(0, 0, 250.0),
            R=Rotation(Rotation.from_axis_angle(rpos[2], (0, 1, 0))))
        J2 = Pose(T=Point(0, 0, 135.0),
            R=Rotation(Rotation.from_axis_angle(rpos[1], (0, 1, 0))))
        J1 = Pose(T=Point(0, 0, 165.0),
            R=Rotation(Rotation.from_axis_angle(rpos[0], (0, 0, 1))))
        return (EE, J6, J5, J4, J3, J2, J1)
      
    def mount_pose(self):
        """\
        Return the overall 3D transformation to the end effector.

        @return: The overall pose.
        @rtype: L{Pose}
        """
        return reduce(lambda a, b: a + b, self.joint_poses()) + self.pose

    def visualize(self, scale=None, color=None, opacity=1.0):
        """\
        Create a 3D visual model of the robot.

        @param scale: Not used.
        @type scale: C{object}
        @param color: Not used.
        @type color: C{object}
        @param opacity: The opacity of the visualization.
        @type opacity: C{float}
        """
        if Posable.visualize(self, scale=scale, color=color, opacity=opacity):
            self.flange = VisualizationObject(self)
            self.wrist = VisualizationObject(self)
            self.forearm = VisualizationObject(self)
            self.elbow = VisualizationObject(self)
            self.upperarm = VisualizationObject(self)
            self.shoulder = VisualizationObject(self)
            # flange
            self.flange.add('small', visual.cylinder(frame=self.flange,
                pos=(0, 0, 12.8), axis=(0, 0, 6.5), color=(0.7, 0.7, 0.7),
                radius=15.75, material=visual.materials.plastic))
            self.flange.add('large', visual.cylinder(frame=self.flange,
                pos=(0, 0, 0), axis=(0, 0, 12.8), color=(0.7, 0.7, 0.7),
                radius=35, material=visual.materials.plastic))
            self.flange.frame = self.wrist
            # wrist
            self.wrist.add('front', visual.box(frame=self.wrist,
                pos=(0, 0, 26.35), length=56, height=46, width=52.7,
                color=(0.9, 0.9, 0.9), material=visual.materials.plastic))
            self.wrist.add('back', visual.cylinder(frame=self.wrist, radius=28,
                pos=(0, -23, 0), axis=(0, 46, 0), color=(0.9, 0.9, 0.9),
                material=visual.materials.plastic))
            self.wrist.frame = self.forearm
            # forearm
            self.forearm.add('bp', visual.box(frame=self.forearm,
                pos=(0, 0, 42), width=84, height=116, length=96,
                color=(0.9, 0.9, 0.9), material=visual.materials.plastic))
            for i in [-1, 1]:
                self.forearm.add('c%d' % i, visual.cylinder(frame=self.forearm,
                    pos=(0, i * 30, 117), axis=(0, i * 28, 0), radius=48,
                    color=(0.9, 0.9, 0.9), material=visual.materials.plastic))
                self.forearm.add('s%d' % i, visual.box(frame=self.forearm,
                    pos=(0, i * 44, 99.5), width=35, height=28, length=96,
                    color=(0.9, 0.9, 0.9), material=visual.materials.plastic))
            self.forearm.frame = self.elbow
            # elbow
            self.elbow.add('top', visual.box(frame=self.elbow,
                pos=(-90, 0, -58.5), length=96, width=203, height=116,
                color=(0.9, 0.9, 0.9), material=visual.materials.plastic))
            self.elbow.add('bot', visual.box(frame=self.elbow,
                pos=(-21, 0, -58.5), length=42, width=203, height=86,
                color=(0.9, 0.9, 0.9), material=visual.materials.plastic))
            self.elbow.frame = self.upperarm
            # upperarm
            for i in [-1, 1]:
                self.upperarm.add('t%d' % i, visual.cylinder(frame=self.upperarm,
                    pos=(0, i * 43, 250), axis=(0, i * 30, 0), radius=48,
                    color=(0.9, 0.9, 0.9), material=visual.materials.plastic))
                self.upperarm.add('m%d' % i, visual.box(frame=self.upperarm,
                    pos=(0, i * 58, 125), length=96, width=250, height=30,
                    color=(0.9, 0.9, 0.9), material=visual.materials.plastic))
                self.upperarm.add('b%d' % i, visual.cylinder(frame=self.upperarm,
                    pos=(0, i * 43, 0), axis=(0, i * 30, 0), radius=48,
                    color=(0.9, 0.9, 0.9), material=visual.materials.plastic))
            self.upperarm.add('ct', visual.box(frame=self.upperarm, pos=(0, 0, 145),
                length=96, width=140, height=86, color=(0.9, 0.9, 0.9),
                material=visual.materials.plastic))
            self.upperarm.frame = self.shoulder
            # shoulder
            self.shoulder.add('top', visual.cylinder(frame=self.shoulder,
                pos=(0, -43, 135), axis=(0, 86, 0), radius=65,
                color=(0.9, 0.9, 0.9), material=visual.materials.plastic))
            self.shoulder.add('con', visual.box(frame=self.shoulder,
                pos=(0, 0, 97.5), length=130, width=75, height=86,
                color=(0.9, 0.9, 0.9), material=visual.materials.plastic))
            self.shoulder.add('base', visual.cylinder(frame=self.shoulder,
                axis=(0, 0, 60), radius=77.5, color=(0.9, 0.9, 0.9),
                material=visual.materials.plastic))
            self.shoulder.frame = self.vis
            # base
            self.vis.add('round', visual.cylinder(frame=self.vis,
                pos=(0, 0, 15), axis=(0, 0, 150), radius=77.5,
                color=(0.9, 0.9, 0.9), material=visual.materials.plastic))
            self.vis.add('box', visual.box(frame=self.vis, pos=(-81.75, 0, 77.5),
                length=163.5, width=125, height=155, color=(0.9, 0.9, 0.9),
                material=visual.materials.plastic))
            self.vis.add('base', visual.box(frame=self.vis, pos=(-43, 0, 7.5),
                length=250, width=15, height=188, color=(0.9, 0.9, 0.9),
                material=visual.materials.plastic))
            # pose
            self.update_visualization()
            return True
        else:
            return False

    def update_visualization(self):
        """\
        Update the visualization.
        """
        Posable.update_visualization(self)
        EE, J6, J5, J4, J3, J2, J1 = self.joint_poses()
        self.shoulder.transform(J1)
        self.upperarm.transform(J2)
        self.elbow.transform(J3)
        self.forearm.transform(J4)
        self.wrist.transform(J5)
        self.flange.transform(J6)

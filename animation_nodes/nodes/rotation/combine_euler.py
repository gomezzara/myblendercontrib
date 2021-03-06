import bpy
from bpy.props import *
from ... events import executionCodeChanged
from ... base_types.node import AnimationNode

class CombineEulerNode(bpy.types.Node, AnimationNode):
    bl_idname = "an_CombineEulerNode"
    bl_label = "Combine Euler"

    useDegree = BoolProperty(name = "Use Degree", default = False,
        update = executionCodeChanged)

    def create(self):
        self.inputs.new("an_FloatSocket", "X", "x")
        self.inputs.new("an_FloatSocket", "Y", "y")
        self.inputs.new("an_FloatSocket", "Z", "z")
        self.outputs.new("an_EulerSocket", "Euler", "euler")

    def draw(self, layout):
        layout.prop(self, "useDegree")

    def getExecutionCode(self):
        if self.useDegree:
            toRadian = "math.pi / 180"
            return "euler = mathutils.Euler((x * {0}, y * {0}, z * {0}), 'XYZ')".format(toRadian)
        else:
            return "euler = mathutils.Euler((x, y, z), 'XYZ')"

    def getUsedModules(self):
        return ["mathutils", "math"]

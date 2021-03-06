
import numpy as np

import bpy
from bpy.props import FloatProperty, EnumProperty, BoolProperty, IntProperty

from sverchok.node_tree import SverchCustomTreeNode, throttled
from sverchok.data_structure import updateNode, zip_long_repeat, ensure_nesting_level
from sverchok.utils.logging import info, exception
from sverchok.utils.curve import make_euclidian_ts

from sverchok_extra.utils import rbf_functions
from sverchok_extra.data.curve import SvExRbfCurve
from sverchok_extra.dependencies import scipy

if scipy is not None:
    from scipy.interpolate import Rbf

    class SvExRbfCurveNode(bpy.types.Node, SverchCustomTreeNode):
        """
        Triggers: Minimal Curve
        Tooltip: Generate minimal curve
        """
        bl_idname = 'SvExRbfCurveNode'
        bl_label = 'Minimal Curve'
        bl_icon = 'CURVE_NCURVE'

        function : EnumProperty(
                name = "Function",
                items = rbf_functions,
                default = 'multiquadric',
                update = updateNode)

        smooth : FloatProperty(
                name = "Smooth",
                default = 0.0,
                min = 0.0,
                update = updateNode)

        epsilon : FloatProperty(
                name = "Epsilon",
                default = 1.0,
                min = 0.0,
                update = updateNode)
        
        def draw_buttons(self, context, layout):
            layout.prop(self, "function")

        def sv_init(self, context):
            self.inputs.new('SvVerticesSocket', "Vertices")
            self.inputs.new('SvStringsSocket', "Epsilon").prop_name = 'epsilon'
            self.inputs.new('SvStringsSocket', "Smooth").prop_name = 'smooth'
            self.outputs.new('SvCurveSocket', "Curve")

        def process(self):
            if not any(socket.is_linked for socket in self.outputs):
                return

            vertices_s = self.inputs['Vertices'].sv_get()
            vertices_s = ensure_nesting_level(vertices_s, 3)
            epsilon_s = self.inputs['Epsilon'].sv_get()
            smooth_s = self.inputs['Smooth'].sv_get()

            curves_out = []
            for vertices, epsilon, smooth in zip_long_repeat(vertices_s, epsilon_s, smooth_s):
                if isinstance(epsilon, (list, int)):
                    epsilon = epsilon[0]
                if isinstance(smooth, (list, int)):
                    smooth = smooth[0]

                vertices = np.array(vertices)
                ts = make_euclidian_ts(vertices)
                rbf = Rbf(ts, vertices,
                            function=self.function,
                            smooth=smooth,
                            epsilon=epsilon, mode='N-D')
                curve = SvExRbfCurve(rbf, (0.0, 1.0))
                curves_out.append(curve)

            self.outputs['Curve'].sv_set(curves_out)

def register():
    if scipy is not None:
        bpy.utils.register_class(SvExRbfCurveNode)

def unregister():
    if scipy is not None:
        bpy.utils.unregister_class(SvExRbfCurveNode)


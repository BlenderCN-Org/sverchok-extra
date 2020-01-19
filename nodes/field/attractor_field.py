
import numpy as np

import bpy
from bpy.props import FloatProperty, EnumProperty, BoolProperty, IntProperty, StringProperty
from mathutils import kdtree

from sverchok.node_tree import SverchCustomTreeNode, throttled
from sverchok.data_structure import updateNode, zip_long_repeat, fullList, match_long_repeat
from sverchok.utils.logging import info, exception

from sverchok_extra.data import SvExScalarFieldPointDistance, SvExVectorFieldPointDistance, SvExAverageVectorField, SvExMergedScalarField, SvExKdtVectorField, SvExKdtScalarField, SvExLineAttractorScalarField, SvExLineAttractorVectorField, SvExPlaneAttractorScalarField, SvExPlaneAttractorVectorField
from sverchok_extra.utils import falloff_types, falloff

class SvExAttractorFieldNode(bpy.types.Node, SverchCustomTreeNode):
    """
    Triggers: Attractor Field
    Tooltip: Generate scalar and vector attraction fields
    """
    bl_idname = 'SvExAttractorFieldNode'
    bl_label = 'Attractor Field'
    bl_icon = 'OUTLINER_OB_EMPTY'
    sv_icon = 'SV_VORONOI'

    @throttled
    def update_type(self, context):
        self.inputs['Direction'].hide_safe = (self.attractor_type == 'Point')
        self.inputs['Amplitude'].hide_safe = (self.falloff_type != 'NONE')
        self.inputs['Coefficient'].hide_safe = (self.falloff_type not in ['NONE', 'inverse_exp', 'gauss'])

    falloff_type: EnumProperty(
        name="Falloff type", items=falloff_types, default='NONE', update=update_type)

    amplitude: FloatProperty(
        name="Amplitude", default=0.5, min=0.0, update=updateNode)

    coefficient: FloatProperty(
        name="Coefficient", default=0.5, update=updateNode)

    clamp: BoolProperty(
        name="Clamp", description="Restrict coefficient with R", default=False, update=updateNode)

    types = [
            ("Point", "Point", "Attraction to single or multiple points", 0),
            ("Line", "Line", "Attraction to straight line", 1),
            ("Plane", "Plane", "Attraction to plane", 2)
        ]

    attractor_type: EnumProperty(
        name="Attractor type", items=types, default='Point', update=update_type)

    point_modes = [
        ('AVG', "Average", "Use average distance to all attraction centers", 0),
        ('MIN', "Nearest", "Use minimum distance to any of attraction centers", 1)
    ]

    point_mode : EnumProperty(
        name = "Points mode",
        description = "How to define the distance when multiple attraction centers are used",
        items = point_modes,
        default = 'AVG',
        update = updateNode)

    def sv_init(self, context):
        d = self.inputs.new('SvVerticesSocket', "Center")
        d.use_prop = True
        d.prop = (0.0, 0.0, 0.0)

        d = self.inputs.new('SvVerticesSocket', "Direction")
        d.use_prop = True
        d.prop = (0.0, 0.0, 1.0)

        self.inputs.new('SvStringsSocket', 'Amplitude').prop_name = 'amplitude'
        self.inputs.new('SvStringsSocket', 'Coefficient').prop_name = 'coefficient'

        self.outputs.new('SvExVectorFieldSocket', "VField").display_shape = 'CIRCLE_DOT'
        self.outputs.new('SvExScalarFieldSocket', "SField").display_shape = 'CIRCLE_DOT'
        self.update_type(context)

    def draw_buttons(self, context, layout):
        layout.prop(self, 'attractor_type')
        if self.attractor_type == 'Point':
            layout.prop(self, 'point_mode')
        layout.prop(self, 'falloff_type')
        layout.prop(self, 'clamp')

    def to_point(self, centers, falloff):
        n = len(centers)
        if n == 1:
            sfield = SvExScalarFieldPointDistance(centers[0], falloff)
            vfield = SvExVectorFieldPointDistance(centers[0], falloff)
        elif self.point_mode == 'AVG':
            sfields = [SvExScalarFieldPointDistance(center, falloff) for center in centers]
            sfield = SvExMergedScalarField('AVG', sfields)
            vfields = [SvExVectorFieldPointDistance(center, falloff) for center in centers]
            vfield = SvExAverageVectorField(vfields)
        else: # MIN
            kdt = kdtree.KDTree(len(centers))
            for i, v in enumerate(centers):
                kdt.insert(v, i)
            kdt.balance()
            vfield = SvExKdtVectorField(kdt=kdt, falloff=falloff)
            sfield = SvExKdtScalarField(kdt=kdt, falloff=falloff)
        return vfield, sfield

    def to_line(self, center, direction, falloff):
        sfield = SvExLineAttractorScalarField(np.array(center), np.array(direction), falloff)
        vfield = SvExLineAttractorVectorField(np.array(center), np.array(direction), falloff)
        return vfield, sfield

    def to_plane(self, center, direction, falloff):
        sfield = SvExPlaneAttractorScalarField(np.array(center), np.array(direction), falloff)
        vfield = SvExPlaneAttractorVectorField(np.array(center), np.array(direction), falloff)
        return vfield, sfield

    def process(self):
        if not any(socket.is_linked for socket in self.outputs):
            return

        center_s = self.inputs['Center'].sv_get()
        directions_s = self.inputs['Direction'].sv_get()
        amplitudes_s = self.inputs['Amplitude'].sv_get()
        coefficients_s = self.inputs['Coefficient'].sv_get()

        vfields_out = []
        sfields_out = []

        objects = zip_long_repeat(center_s, directions_s, amplitudes_s, coefficients_s)
        for centers, direction, amplitude, coefficient in objects:
            if isinstance(amplitude, (list, tuple)):
                amplitude = amplitude[0]
            if isinstance(coefficient, (list, tuple)):
                coefficient = coefficient[0]

            if self.falloff_type == 'NONE':
                falloff_func = None
            else:
                falloff_func = falloff(self.falloff_type, amplitude, coefficient, self.clamp)
            
            if self.attractor_type == 'Point':
                vfield, sfield = self.to_point(centers, falloff_func)
            elif self.attractor_type == 'Line':
                vfield, sfield = self.to_line(centers[0], direction[0], falloff_func)
            elif self.attractor_type == 'Plane':
                vfield, sfield = self.to_plane(centers[0], direction[0], falloff_func)
            else:
                raise Exception("not implemented yet")

            vfields_out.append(vfield)
            sfields_out.append(sfield)

        self.outputs['SField'].sv_set(sfields_out)
        self.outputs['VField'].sv_set(vfields_out)

def register():
    bpy.utils.register_class(SvExAttractorFieldNode)

def unregister():
    bpy.utils.unregister_class(SvExAttractorFieldNode)

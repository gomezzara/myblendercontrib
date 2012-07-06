# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

###############################################################################
#234567890123456789012345678901234567890123456789012345678901234567890123456789
#--------1---------2---------3---------4---------5---------6---------7---------


# ##### BEGIN COPYRIGHT BLOCK #####
#
# initial script copyright (c)2011,2012 Alexander Nussbaumer
#
# ##### END COPYRIGHT BLOCK #####


#import python stuff
import io
import math
import mathutils
import os
import sys
import time


# To support reload properly, try to access a package var,
# if it's there, reload everything
if ('bpy' in locals()):
    import imp
    if 'io_scene_ms3d.ms3d_spec' in locals():
        imp.reload(io_scene_ms3d.ms3d_spec)
    if 'io_scene_ms3d.ms3d_utils' in locals():
        imp.reload(io_scene_ms3d.ms3d_utils)
    if 'io_scene_ms3d.ms3d_ui' in locals():
        imp.reload(io_scene_ms3d.ms3d_ui)
    pass

else:
    from io_scene_ms3d.ms3d_spec import *
    from io_scene_ms3d.ms3d_utils import *
    from io_scene_ms3d.ms3d_ui import *
    pass


#import blender stuff
import bpy
import bpy_extras.io_utils

from bpy.props import (
        BoolProperty,
        EnumProperty,
        FloatProperty,
        StringProperty,
        )


###############################################################################
class Ms3dExporter():
    """ Load a MilkShape3D MS3D File """

    def __init__(self, options):
        self.options = options
        pass

    # create a empty ms3d ms3d_template
    # fill ms3d_template with blender content
    # writer ms3d file
    def write(self, blender_context):
        """convert bender content to ms3d content and write it to file"""

        t1 = time.time()
        t2 = None

        try:
            # setup environment
            pre_setup_environment(self)

            # create an empty ms3d template
            ms3d_template = Ms3dModel()

            # inject blender data to ms3d file
            self.from_blender(blender_context, ms3d_template)

            t2 = time.time()

            # write ms3d file to disk
            self.file = io.FileIO(self.filepath, "w")

            ms3d_template.write(self.file)

            self.file.flush()
            self.file.close()

            # finalize/restore environment
            post_setup_environment(self, False)

        except Exception:
            type, value, traceback = sys.exc_info()
            print("write - exception in try block\n  type: '{0}'\n"
                    "  value: '{1}'".format(type, value, traceback))

            if t2 is None:
                t2 = time.time()

            raise

        else:
            pass

        t3 = time.time()
        print("elapsed time: {0:.4}s (converter: ~{1:.4}s, disk io:"
                " ~{2:.4}s)".format((t3 - t1), (t2 - t1), (t3 - t2)))

        return {"FINISHED"}


    ###########################################################################
    def from_blender(self, blender_context, ms3d_template):
        """ known limitations:
            - bones unsupported yet
            - joints unsupported yet
            - very bad performance

        notes:
            - interpreating a blender-mesh-objects as ms3d-group
            - only one material allowed per group in ms3d,
              maybe sub-split a mesh in to material groups???"""

        blender = blender_context.blend_data

        # todo: use an optimized collection for quick search vertices;
        # with ~(o log n); currently its (o**n)
        ms3d_vertices = []

        ms3dTriangles = []
        ms3dMaterials = []
        ms3dGroups = []

        flagHandleMaterials = \
                (self.options.handle_materials)

        # handle blender-materials (without mesh's uv texture image)
        if (flagHandleMaterials):
            for blender_material in blender.materials:
                if (blender_material.users <= 0):
                    continue

                ms3d_material = self.create_material(blender_material, None)
                if ms3d_material and (ms3d_material not in ms3dMaterials):
                    ms3dMaterials.append(ms3d_material)

        nLayers = len(blender_context.scene.layers)
        # handle blender-objects
        for blender_object in blender.objects:

            # do not handle non-mesh objects or unused objects
            if (blender_object.type != 'MESH') or (blender_object.users <= 0):
                continue

            # skip unselected objects in "only selected"-mode
            if (self.options.prop_selected) and (not blender_object.select):
                continue

            # skip meshes of invisible layers
            skip = True
            for iLayer in range(nLayers):
                if ((blender_object.layers[iLayer]
                        and blender_context.scene.layers[iLayer])):
                    skip = False
                    break
            if (skip):
                continue

            # make new object as active and only selected object
            bpy.context.scene.objects.active = blender_object

            matrix_object = blender_object.matrix_basis

            blender_mesh = blender_object.data

            ms3d_group = Ms3dGroup()
            ms3d_group.name = blender_object.name

            # handle blender-vertices
            for blender_vertex in blender_mesh.vertices:
                ms3dVertex = self.create_vertex(matrix_object, blender_vertex)

                # handle reference_count and/or
                # put vertex without duplicates
                if (ms3dVertex in ms3d_vertices):
                    ms3d_vertices[ms3d_vertices.index(ms3dVertex)]\
                            .reference_count += 1
                else:
                    ms3dVertex.reference_count = 1
                    ms3d_vertices.append(ms3dVertex)

            """
            # handle smoothing groups
            smoothGroupFaces = self.generate_smoothing_groups(
                    blender_context, ms3d_template, blender_mesh.faces)

            # handle blender-faces
            group_index = len(ms3dGroups)
            for iFace, blender_face in enumerate(blender_mesh.faces):
                if (smoothGroupFaces) and (iFace in smoothGroupFaces):
                    smoothing_group = smoothGroupFaces[iFace]
                else:
                    smoothing_group = 0

                if (len(blender_face.vertices) == 4):
                    # 1'st tri of quad
                    ms3dTriangle = self.create_triangle(matrix_object,
                            ms3d_vertices, blender_mesh, blender_face,
                            group_index, smoothing_group, 0)
                    # put triangle
                    ms3dTriangles.append(ms3dTriangle)
                    # put triangle index
                    ms3d_group.triangle_indices.append(
                            ms3dTriangles.index(ms3dTriangle))

                    # 2'nd tri of quad
                    ms3dTriangle = self.create_triangle(matrix_object,
                            ms3d_vertices, blender_mesh, blender_face,
                            group_index, smoothing_group, 1)

                else:
                    ms3dTriangle = self.create_triangle(matrix_object,
                            ms3d_vertices, blender_mesh, blender_face,
                            group_index, smoothing_group)

                # put triangle
                ms3dTriangles.append(ms3dTriangle)
                # put triangle index
                ms3d_group.triangle_indices.append(
                        ms3dTriangles.index(ms3dTriangle))
            """

            # handle material (take the first one)
            if (flagHandleMaterials) and (blender_mesh.materials):
                if (blender_mesh.uv_textures):
                    tmpMaterial1 = self.create_material(
                            blender_mesh.materials[0],
                            blender_mesh.uv_textures[0])
                else:
                    tmpMaterial1 = self.create_material(
                            blender_mesh.materials[0],
                            None)

                if tmpMaterial1:
                    ms3d_group.material_index = ms3dMaterials.index(tmpMaterial1)

                    # upgrade poor material.texture with rich material.texture
                    tmpMaterial2 = ms3dMaterials[ms3d_group.material_index]
                    if (tmpMaterial1.texture) and (not tmpMaterial2.texture):
                        tmpMaterial2.texture = tmpMaterial1.texture

            # put group
            ms3dGroups.append(ms3d_group)

        # injecting common data
        ms3d_template._vertices = ms3d_vertices
        ms3d_template._triangles = ms3dTriangles
        ms3d_template._groups = ms3dGroups
        ms3d_template._materials = ms3dMaterials

        # inject currently unsupported data
        ms3d_template._vertex_ex = []
        if (ms3d_template.sub_version_vertex_extra == 1):
            for i in range(ms3d_template.number_vertices):
                ms3d_template.vertex_ex.append(Ms3dVertexEx1())
        elif (ms3d_template.sub_version_vertex_extra == 2):
            for i in range(ms3d_template.number_vertices):
                ms3d_template.vertex_ex.append(Ms3dVertexEx2())
        elif (ms3d_template.sub_version_vertex_extra == 3):
            for i in range(ms3d_template.number_vertices):
                ms3d_template.vertex_ex.append(Ms3dVertexEx3())
        else:
            pass

        if (self.options.prop_verbose):
            ms3d_template.print_internal()

        is_valid, statistics = ms3d_template.is_valid()
        print()
        print("##############################################################")
        print("Blender -> MS3D : [{0}]".format(self.filepath_splitted[1]))
        print(statistics)
        print("##############################################################")


    ###########################################################################
    def create_material(self, blender_material, blender_uv_layer):
        if (not blender_material):
            return None

        ms3d_material = Ms3dMaterial()

        ms3d_material.name = blender_material.name

        ms3d_material._ambient = (
                blender_material.diffuse_color[0],
                blender_material.diffuse_color[1],
                blender_material.diffuse_color[2],
                blender_material.ambient
                )

        ms3d_material._diffuse = (
                blender_material.diffuse_color[0],
                blender_material.diffuse_color[1],
                blender_material.diffuse_color[2],
                blender_material.diffuse_intensity
                )

        ms3d_material._specular = (
                blender_material.specular_color[0],
                blender_material.specular_color[1],
                blender_material.specular_color[2],
                blender_material.specular_intensity
                )

        ms3d_material._emissive = (
                blender_material.diffuse_color[0],
                blender_material.diffuse_color[1],
                blender_material.diffuse_color[2],
                blender_material.emit
                )

        ms3d_material.shininess = blender_material.specular_hardness / 2.0
        if ms3d_material.shininess > 128:
            ms3d_material.shininess = 128
        if ms3d_material.shininess < 1:
            ms3d_material.shininess = 1

        if (blender_material.use_transparency):
            ms3d_material.transparency = blender_material.alpha

        if (blender_material.texture_slots):
            imageDiffuse = None
            imageAlpha = None

            for blender_texture_slot in blender_material.texture_slots:
                if ((not blender_texture_slot)
                        or (not blender_texture_slot.texture)
                        or (blender_texture_slot.texture_coords != 'UV')
                        or (blender_texture_slot.texture.type != 'IMAGE')
                        ):
                    continue

                if ((not imageDiffuse)
                        and (blender_texture_slot.use_map_color_diffuse)):
                    if ((blender_texture_slot.texture.image)
                            and (blender_texture_slot.texture.image.filepath)):
                        imageDiffuse = os.path.split(
                                blender_texture_slot.texture.image.filepath)[1]
                    elif (not blender_texture_slot.texture.image):
                        # case it image was not loaded
                        imageDiffuse = os.path.split(
                                blender_texture_slot.texture.name)[1]

                elif ((not imageAlpha)
                        and (blender_texture_slot.use_map_color_alpha)):
                    if ((blender_texture_slot.texture.image)
                            and (blender_texture_slot.texture.image.filepath)):
                        imageAlpha = os.path.split(
                                blender_texture_slot.texture.image.filepath)[1]
                    elif (not blender_texture_slot.texture.image):
                        # case it image was not loaded
                        imageAlpha = os.path.split(
                                blender_texture_slot.texture.name)[1]

            # if no diffuse image was found, try to find a uv texture image
            if (not imageDiffuse) and (blender_uv_layer):
                for blender_texture_face in blender_uv_layer.data:
                    if ((blender_texture_face) and (blender_texture_face.image)
                            and (blender_texture_face.image.filepath)):
                        imageDiffuse = os.path.split(
                                blender_texture_face.image.filepath)[1]
                        break

            if (imageDiffuse):
                ms3d_material.texture = imageDiffuse

            if (imageAlpha):
                ms3d_material.alphamap = imageDiffuse

        return ms3d_material


    ###########################################################################
    def create_normal(self,  matrix_object, blender_vertex):
        mathVector = mathutils.Vector(blender_vertex.normal)

        # apply its object matrix (translation, rotation, scale)
        mathVector = (matrix_object * mathVector)

        # apply export swap axis matrix
        mathVector = mathVector * self.matrixSwapAxis

        ms3dNormal = tuple(mathVector)

        return ms3dNormal


    ###########################################################################
    def create_triangle(self, matrix_object, ms3d_vertices,
            blender_mesh, blender_face,
            group_index=0, smoothing_group=None, subIndex=0):
        """
        known limitations:
            - it will take only the first uv_texture-data,
              if one or more are present
        """
        ms3dTriangle = Ms3dTriangle()

        ms3dTriangle.group_index = group_index

        if (smoothing_group) and (smoothing_group > 0):
            ms3dTriangle.smoothing_group = \
                    (smoothing_group % MAX_GROUPS) + 1

        if (blender_face.select):
            ms3dTriangle.flags |= MS3D_FLAG_SELECTED

        if (blender_face.hide):
            ms3dTriangle.flags |= MS3D_FLAG_HIDDEN

        tx = None
        l = len(blender_face.vertices)

        if (l == 3):
            # it is already a triangle geometry
            if (subIndex != 0):
                return None

            # no order-translation needed
            tx = (0, 1, 2)

        elif (l == 4):
            # it is a quad geometry
            if (subIndex > 1) or (subIndex < 0):
                return None

            if (subIndex == 0):
                # order-translation for 1'st triangle
                tx = (0, 1, 3)
            else:
                # order-translation for 2'nd triangle
                tx = (3, 1, 2)

        else:
            # it is any unhandled geometry
            return None

        # take blender-vertex from blender-mesh
        # to get its vertex and normal coordinates
        v = blender_mesh.vertices[blender_face.vertices_raw[tx[0]]]
        v0 = self.create_vertex(matrix_object, v)
        n0 = self.create_normal(matrix_object, v)

        # take blender-vertex from blender-mesh
        # to get its vertex and normal coordinates
        v = blender_mesh.vertices[blender_face.vertices_raw[tx[1]]]
        v1 = self.create_vertex(matrix_object, v)
        n1 = self.create_normal(matrix_object, v)

        # take blender-vertex from blender-mesh
        # to get its vertex and normal coordinates
        v = blender_mesh.vertices[blender_face.vertices_raw[tx[2]]]
        v2 = self.create_vertex(matrix_object, v)
        n2 = self.create_normal(matrix_object, v)

        # put the indices of ms3d-vertices!
        ms3dTriangle._vertex_indices = (
                ms3d_vertices.index(v0),
                ms3d_vertices.index(v1),
                ms3d_vertices.index(v2)
                )

        # put the normales
        ms3dTriangle._vertex_normals = (n0, n1, n2)

        # if uv's present
        if (blender_mesh.uv_textures):
            # take 1'st uv_texture-data
            blenderUv = \
                    blender_mesh.uv_textures[0].data[blender_face.index].uv_raw

            # translate uv to st
            #
            # blender uw
            # y(v)
            # |(0,1)  (1,1)
            # |
            # |
            # |(0,0)  (1,0)
            # +--------x(u)
            #
            # ms3d st
            # +--------x(s)
            # |(0,0)  (1,0)
            # |
            # |
            # |(0,1)  (1,1)
            # y(t)
            s0, t0 = blenderUv[tx[0] << 1], 1.0 - blenderUv[(tx[0] << 1) + 1]
            s1, t1 = blenderUv[tx[1] << 1], 1.0 - blenderUv[(tx[1] << 1) + 1]
            s2, t2 = blenderUv[tx[2] << 1], 1.0 - blenderUv[(tx[2] << 1) + 1]

            # put the uv-coordinates
            ms3dTriangle._s = (s0, s1, s2)
            ms3dTriangle._t = (t0, t1, t2)

        return ms3dTriangle


    ###########################################################################
    def create_vertex(self,  matrix_object, blender_vertex):
        """ known limitations:
            - bone_id not supported """
        ms3dVertex = Ms3dVertex()

        if (blender_vertex.select):
            ms3dVertex.flags |= MS3D_FLAG_SELECTED

        if (blender_vertex.hide):
            ms3dVertex.flags |= MS3D_FLAG_HIDDEN

        mathVector = mathutils.Vector(blender_vertex.co)

        # apply its object matrix (translation, rotation, scale)
        mathVector = (matrix_object * mathVector)

        # apply export viewport matrix
        mathVector = mathVector * self.matrixViewport

        ms3dVertex._vertex = tuple(mathVector)

        return ms3dVertex


    ###########################################################################
    def generate_smoothing_groups(self, blender_context, ms3d_template,
            blender_faces):
        enable_edit_mode(True)

        # enable face-selection-mode
        bpy.context.tool_settings.mesh_select_mode = [False, False, True]

        # deselect all "faces"
        select_all(False) # mesh

        # enable object-mode (important for face.select = value)
        enable_edit_mode(False)

        handledFacesSet = set()
        smoothGroupVertices = {}

        blenderVertices = blender_context.active_object.data.vertices

        # run throug the faces
        # mark linked faces and set its smoothGroup value
        nFaces = len(blender_faces)

        for iFace in range(nFaces):
            if (blender_faces[iFace].select) or (iFace in handledFacesSet):
                continue

            # a new unhandled face found
            blender_faces[iFace].select = True

            enable_edit_mode(True)

            if bpy.ops.mesh.select_linked.poll():
                bpy.ops.mesh.select_linked()

            enable_edit_mode(False)

            # build a set of vertices hashes
            currentFaceSet = set()
            currentVertexSet = set()
            for iiFace in range(nFaces):
                if ((blender_faces[iiFace].select)
                        and (iiFace not in handledFacesSet)):
                    handledFacesSet.add(iiFace)
                    currentFaceSet.add(iiFace)

                    iVertex = blender_faces[iiFace].vertices[0]
                    mathVector = blenderVertices[iVertex].co
                    currentVertexSet.add(
                            hash(mathVector[0])
                            ^ hash(mathVector[1])
                            ^ hash(mathVector[2]))

                    iVertex = blender_faces[iiFace].vertices[1]
                    mathVector = blenderVertices[iVertex].co
                    currentVertexSet.add(
                            hash(mathVector[0])
                            ^ hash(mathVector[1])
                            ^ hash(mathVector[2]))

                    iVertex = blender_faces[iiFace].vertices[2]
                    mathVector = blenderVertices[iVertex].co
                    currentVertexSet.add(
                            hash(mathVector[0])
                            ^ hash(mathVector[1])
                            ^ hash(mathVector[2]))

                    if(len(blender_faces[iiFace].vertices) == 4):
                        iVertex = blender_faces[iiFace].vertices[3]
                        mathVector = blenderVertices[iVertex].co
                        currentVertexSet.add(
                                hash(mathVector[0])
                                ^ hash(mathVector[1])
                                ^ hash(mathVector[2]))

            # search for collision set
            reused_smoothgroup = False
            for iSmoothGroup in smoothGroupVertices:
                smoothVertexSet = smoothGroupVertices[iSmoothGroup][1]
                intersectionVertexSet = currentVertexSet & smoothVertexSet
                if(len(intersectionVertexSet) == 0):
                    # no shared vertices, you can use that smoothgroup without collision
                    item = smoothGroupVertices[iSmoothGroup]
                    item[0] |= currentFaceSet
                    item[1] |= currentVertexSet
                    reused_smoothgroup = True
                    break

            if not reused_smoothgroup:
                smoothGroupVertices[len(smoothGroupVertices)] = [currentFaceSet, currentVertexSet]

        # put result to a smoothGroupFaces dictionary
        smoothGroupFaces = {}
        for iSmoothGroup in smoothGroupVertices:
            for iFace in smoothGroupVertices[iSmoothGroup][0]:
                smoothGroupFaces[iFace] = iSmoothGroup

        return smoothGroupFaces


###############################################################################
#234567890123456789012345678901234567890123456789012345678901234567890123456789
#--------1---------2---------3---------4---------5---------6---------7---------
# ##### END OF FILE #####

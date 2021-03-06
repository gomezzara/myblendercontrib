# bmesh_extras.py

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

import bmesh


def bmesh_from_pydata(verts=None, edges=None, faces=None):
    '''
    - verts is necessary, edges/faces are optional
    - verts is expected to be an iterable or generator, formatted as follows:
        verts = [[x, y, z], [x, y, z], [x, y, z], .....]
    - will return None if verts are found, otherwise a bmesh.
    '''

    if not verts:
        print('bmesh_from_pydata expects a collection of 3 element coordinates')
        return

    bm = bmesh.new()
    add_vert = bm.verts.new

    bm_verts = [add_vert(co) for co in verts]
    bm.verts.index_update()

    if faces:
        add_face = bm.faces.new
        for face in faces:
            add_face([bm_verts[i] for i in face])
        bm.faces.index_update()

    if edges:
        add_edge = bm.edges.new
        for edge in edges:
            edge_seq = bm_verts[edge[0]], bm_verts[edge[1]]
            try:
                add_edge(edge_seq)
            except ValueError:
                # edge exists!
                pass
        bm.edges.index_update()

    return bm


def pydata_from_bmesh(bm):
    v = [v.co[:] for v in bm.verts]
    e = [[i.index for i in e.verts] for e in bm.edges[:]]
    p = [[i.index for i in p.verts] for p in bm.faces[:]]
    return v, e, p

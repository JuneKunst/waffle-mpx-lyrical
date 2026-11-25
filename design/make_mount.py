"""Generate the D435 fork and fastener visuals. Units mm in the Waffle base frame."""
from pathlib import Path
import numpy as np
from manifold3d import CrossSection, Manifold, OpType

OUT = Path(__file__).resolve().parent
MESH = OUT.parent / 'turtlebot3_manipulation_description/meshes/mount'
DECK_Z = 91.5
TOP = DECK_Z + 5
REAR_X = 96.0
CAMERA_AXIS_Z = 77.5
DECK_HOLES = [(x, y) for x in (12, 24) for y in (-64, 64)]
CAMERA_HOLES = [-22.5, 22.5]


def cylinder(radius, length, xyz, along_x=False, sides=64):
    solid = Manifold.cylinder(length, radius, circular_segments=sides)
    if along_x:
        solid = solid.rotate((0, 90, 0))
    return solid.translate(xyz)


def plate(outline, z, thickness):
    return CrossSection([outline]).extrude(thickness).translate((0, 0, z))


def write_stl(path, solid):
    assert solid.status().name == 'NoError' and solid.volume() > 0
    mesh = solid.to_mesh()
    v = mesh.vert_properties[mesh.tri_verts, :3].astype(float)
    normals = np.cross(v[:, 1]-v[:, 0], v[:, 2]-v[:, 0])
    records = np.zeros(len(v), dtype=[('n','<f4',3), ('v','<f4',(3,3)), ('a','<u2')])
    records['v'] = v
    records['n'] = normals / np.linalg.norm(normals, axis=1)[:, None]
    path.write_bytes(b'Waffle MPX D435 mm'.ljust(80, b'\0') + len(v).to_bytes(4, 'little') + records.tobytes())


# Two side rails clear the fittings in the centre of the upper deck.
# Trace both halves around the inner opening (the rear is open).
outline = [(5,58),(68,58),(74,52),(74,-52),(68,-58),(5,-58),
           (5,-68),(8,-71),(72,-71),(86,-56),(86,56),(72,71),(8,71),(5,68)]
outline = [(x + 10 if x >= 68 else x, y) for x, y in outline]
fork = plate(outline, DECK_Z, 5)
fasteners = []
for x, y in DECK_HOLES:
    fork -= cylinder(1.7, 7, (x, y, DECK_Z-1))
    fasteners.extend([cylinder(1.5, 16, (x,y,TOP-16)),
                      cylinder(3.5, .5, (x,y,TOP)), cylinder(2.8, 2.5, (x,y,TOP+.5))])

# Vertical backing flange with triangular side ribs. Bolt heads are accessible from -X.
flange = Manifold.cube((5,68,25)).translate((REAR_X-5,-34,TOP-25))
fork += flange
for y in (-34, 31):
    rib = CrossSection([[(82,DECK_Z),(91,73),(92,73),(92,DECK_Z+1),(82,DECK_Z+1)]])
    fork += rib.extrude(3).rotate((90,0,0)).translate((0,y+3,0))
for y in CAMERA_HOLES:
    fork -= cylinder(1.7, 7, (REAR_X-6, y, CAMERA_AXIS_Z), True)
    fasteners.extend([cylinder(1.5, 8, (REAR_X-5.5,y,CAMERA_AXIS_Z), True),
                      cylinder(3.5, .5, (REAR_X-5.5,y,CAMERA_AXIS_Z), True),
                      cylinder(2.8, 3, (REAR_X-8.5,y,CAMERA_AXIS_Z), True)])

assert len(fork.decompose()) == 1
# Installed mesh uses the screw-frame datum. Print the flat upper face on the bed.
datum = (-106.1547, 0, -65)
write_stl(MESH/'D435_A1_PLA.stl', fork.translate(datum))
write_stl(MESH/'D435_fasteners.stl', Manifold.batch_boolean(fasteners, OpType.Add).translate(datum))
write_stl(OUT/'D435_A1_PLA.stl', fork.translate((0,0,-TOP)).rotate((180,0,0)))
print(f'Single closed bracket, {fork.volume()/1000:.2f} cm3')

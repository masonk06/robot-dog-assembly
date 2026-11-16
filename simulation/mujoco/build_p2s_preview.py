"""Build isolated P2S geometry preview; inertias remain provisional."""
from pathlib import Path
import json
import struct
import xml.etree.ElementTree as ET
import numpy as np
import mujoco

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'p2s'

def main():
    OUT.mkdir(exist_ok=True)
    source = ROOT / 'cad/frame_p2s_camera_insert/Chassis.stl'
    vertices = []
    for line in source.read_text().splitlines():
        fields = line.split()
        if fields and fields[0] == 'vertex':
            vertices.append([float(x) for x in fields[1:]])
    v = np.asarray(vertices)
    assert len(v) % 3 == 0 and len(v)
    mesh = OUT / 'chassis.stl'
    with mesh.open('wb') as stream:
        stream.write(b'Luca P2S chassis, original CAD mm'.ljust(80, b' '))
        stream.write(struct.pack('<I', len(v)//3))
        for triangle in v.reshape(-1,3,3):
            stream.write(struct.pack('<12fH', 0,0,0,*triangle.ravel(),0))
    tree = ET.parse(HERE / 'robot_dog_v2.xml')
    root = tree.getroot()
    root.set('model', 'Luca P2S 230mm - provisional dynamics')
    root.find('compiler').set('meshdir', '.')
    for asset in root.findall('asset/mesh'):
        asset.set('file', '../assets/' + asset.get('file'))
    root.find("asset/mesh[@name='mesh_0']").set('file', 'chassis.stl')
    base = root.find("worldbody/body[@name='base']")
    # Front placement axis_point retained a stale -30 mm translation.
    # The front and rear pitch servo meshes share their orientation; their
    # disc center is at the same mesh-local point. Move only the hinge,
    # preserving every visual's zero-pose transform.
    for leg in ('front_left', 'front_right'):
        joint = base.find(f".//joint[@name='{leg}_hip_pitch']")
        joint.set('pos', '.03 0 0')
    for leg in ('rear_left','rear_right'):
        for element in (base.find(f"body[@name='{leg}_roll_link']"), base.find(f"geom[@name='{leg}_servo_hip_roll']")):
            xyz = np.fromstring(element.get('pos'), sep=' ')
            xyz[0] += .06
            element.set('pos', ' '.join(map(str, xyz)))
    proxy = base.find("geom[@name='body_contact_proxy']")
    proxy.set('pos', '.045 0 .025')
    proxy.set('size', '.115 .0899 .025')
    ET.indent(root)
    path = OUT/'robot_dog_p2s.xml'
    tree.write(path, encoding='unicode')
    old = mujoco.MjModel.from_xml_path(str(HERE/'robot_dog_v2.xml'))
    model = mujoco.MjModel.from_xml_path(str(path))
    d0, d1 = mujoco.MjData(old), mujoco.MjData(model)
    mujoco.mj_forward(old,d0); mujoco.mj_forward(model,d1)
    shifts = {}
    for leg in ('front_left','front_right','rear_left','rear_right'):
        name = leg+'_foot'
        i = mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_SITE,name)
        j = mujoco.mj_name2id(old,mujoco.mjtObj.mjOBJ_SITE,name)
        delta = d1.site_xpos[i]-d0.site_xpos[j]
        np.testing.assert_allclose(delta, [.06 if leg.startswith('rear') else 0,0,0], atol=1e-9)
        shifts[leg] = delta.tolist()
    assert model.nu == old.nu == 12
    # Compare pivot location in each servo mesh's local coordinates.
    local_pivots = {}
    for leg in ('front_left','front_right','rear_left','rear_right'):
        j = mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,leg+'_hip_pitch')
        g = mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,leg+'_servo_hip_pitch')
        local_pivots[leg] = d1.geom_xmat[g].reshape(3,3).T @ (d1.xanchor[j]-d1.geom_xpos[g])
    for side in ('left','right'):
        np.testing.assert_allclose(local_pivots['front_'+side],local_pivots['rear_'+side],atol=1e-8)
    report = dict(chassis_bounds_mm=[v.min(axis=0).tolist(),v.max(axis=0).tolist()],foot_shifts_m=shifts,
        total_provisional_mass_kg=float(model.body_mass.sum()),
        limitations=['Original inertias retained; 1546g measurement inclusion unresolved.',
        'Electronics placement and masses not yet calibrated.',
        'Front hip-pitch hinges corrected +30 mm to match servo-local rear pivots; attachment fit requires review.',
        'Chassis collision is a conservative box, not a detailed mesh.'])
    (OUT/'validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()

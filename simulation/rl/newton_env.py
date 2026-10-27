"""Newton CUDA physics with original CPU observations/rewards. Validation bridge."""
import numpy as np
import mujoco
import mujoco_warp as mjw
import newton
import warp as wp
from env import DogWalkEnv, LEGS


class NewtonDogEnv(DogWalkEnv):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        wp.init()
        with wp.ScopedDevice('cuda:0'):
            b = newton.ModelBuilder()
            newton.solvers.SolverMuJoCo.register_custom_attributes(b)
            b.add_mjcf(str(self.model_path), parse_visuals=False, ctrl_direct=True)
            self.nmodel = b.finalize()
            self.solver = newton.solvers.SolverMuJoCo(self.nmodel, use_mujoco_contacts=True,
                                                     njmax=256, nconmax=128)
            m = self.solver.mj_model
            for field in ('jnt_type','jnt_axis','jnt_qposadr','jnt_dofadr','jnt_range',
                          'actuator_trnid','actuator_gainprm','actuator_biasprm','actuator_forcerange'):
                np.testing.assert_allclose(getattr(m,field),getattr(self.model,field),atol=1e-6)
            self.control = self.nmodel.control()
            self.contact_ids = wp.array(np.arange(128,dtype=np.int32),dtype=int)
            self.contact_forces = wp.zeros(128,dtype=wp.spatial_vector)
            mapping = self.solver.mjc_geom_to_newton_shape.numpy()[0]
            labels = list(self.nmodel.shape_label)
            self.gpu_foot_geoms = {}
            self.gpu_floor = set()
            for geom,shape in enumerate(mapping):
                if shape < 0:
                    continue
                name = labels[shape].split('/')[-1]
                if name == 'floor':
                    self.gpu_floor.add(geom)
                for i,leg in enumerate(LEGS):
                    if name == f'{leg}_foot_contact_proxy':
                        self.gpu_foot_geoms[geom] = i
            if len(self.gpu_foot_geoms)!=4 or not self.gpu_floor:
                raise ValueError('Cannot map Newton foot/floor collision shapes')
        self.gpu_forces = np.zeros(4)

    def reset(self, **kwargs):
        obs,info = super().reset(**kwargs)
        with wp.ScopedDevice('cuda:0'):
            self.s0,self.s1 = self.nmodel.state(),self.nmodel.state()
            q = self.data.qpos.copy()
            q[3:7] = q[[4,5,6,3]]
            self.s0.joint_q.assign(q.astype(np.float32))
            newton.eval_fk(self.nmodel,self.s0.joint_q,self.s0.joint_qd,self.s0)
        self.gpu_forces[:] = 0
        return obs,info

    def _physics_step(self):
        with wp.ScopedDevice('cuda:0'):
            self.control.mujoco.ctrl.assign(self.data.ctrl.astype(np.float32))
            self.s0.clear_forces()
            self.solver.step(self.s0,self.s1,self.control,None,self.model.opt.timestep)
            self.s0,self.s1 = self.s1,self.s0
            d = self.solver.mjw_data
            self.data.qpos[:] = d.qpos.numpy()[0]
            self.data.qvel[:] = d.qvel.numpy()[0]
            self.data.time += self.model.opt.timestep
            mujoco.mj_forward(self.model,self.data)
            self.data.actuator_force[:] = d.actuator_force.numpy()[0]
            mjw.contact_force(self.solver.mjw_model,d,self.contact_ids,False,self.contact_forces)
            n = int(d.nacon.numpy()[0])
            if n>128:
                raise RuntimeError('Contact buffer exceeded')
            geoms = d.contact.geom.numpy()[:n]
            forces = self.contact_forces.numpy()[:n]
            self.gpu_forces[:] = 0
            for (g1,g2),force in zip(geoms,forces):
                other = g2 if g1 in self.gpu_floor else g1 if g2 in self.gpu_floor else -1
                if other in self.gpu_foot_geoms:
                    self.gpu_forces[self.gpu_foot_geoms[other]] += max(0.,force[0])

    def _feet(self):
        _,velocity = super()._feet()
        return self.gpu_forces.copy(),velocity

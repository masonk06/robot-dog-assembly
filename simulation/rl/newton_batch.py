"""Shared Newton CUDA physics batch; exact existing CPU task logic per world.

No subprocesses or per-world physics solvers. Observations/rewards remain on CPU.
"""
import numpy as np
import mujoco
import mujoco_warp as mjw
import newton
import warp as wp
from stable_baselines3.common.vec_env import VecEnv
from env import DogWalkEnv, LEGS


class TaskMirror(DogWalkEnv):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gpu_forces = np.zeros(4)

    def _feet(self):
        _,velocity = super()._feet()
        return self.gpu_forces.copy(),velocity


class NewtonBatchVecEnv(VecEnv):
    def __init__(self, n_envs, config, model_path, seed=42):
        self.tasks = [TaskMirror(config,model_path=model_path) for _ in range(n_envs)]
        self.seed_base = seed
        self.reset_counts = np.zeros(n_envs,dtype=int)
        self.actions = None
        wp.init()
        with wp.ScopedDevice('cuda:0'):
            robot = newton.ModelBuilder()
            newton.solvers.SolverMuJoCo.register_custom_attributes(robot)
            robot.add_mjcf(str(self.tasks[0].model_path),parse_visuals=False,ctrl_direct=True)
            builder = newton.ModelBuilder()
            newton.solvers.SolverMuJoCo.register_custom_attributes(builder)
            builder.replicate(robot,n_envs)
            self.model = builder.finalize()
            self.solver = newton.solvers.SolverMuJoCo(self.model,separate_worlds=True,
                use_mujoco_contacts=True,njmax=256,nconmax=128)
            m,original = self.solver.mj_model,self.tasks[0].model
            for field in ('jnt_type','jnt_axis','jnt_qposadr','jnt_dofadr','jnt_range',
                          'actuator_trnid','actuator_gainprm','actuator_biasprm','actuator_forcerange'):
                np.testing.assert_allclose(getattr(m,field),getattr(original,field),atol=1e-6)
            if self.solver.mjw_data.qpos.shape != (n_envs,19):
                raise ValueError('Unexpected batch coordinate layout')
            self.s0,self.s1,self.control = self.model.state(),self.model.state(),self.model.control()
            self.capacity = int(self.solver.mjw_data.contact.geom.shape[0])
            self.contact_ids = wp.array(np.arange(self.capacity,dtype=np.int32),dtype=int)
            self.contact_forces = wp.zeros(self.capacity,dtype=wp.spatial_vector)
            mapping = self.solver.mjc_geom_to_newton_shape.numpy()[0]
            labels = list(self.model.shape_label)
            self.foot_geoms = {}
            self.floor = set()
            for geom,shape in enumerate(mapping):
                if shape<0:
                    continue
                name = labels[shape].split('/')[-1]
                if name=='floor': self.floor.add(geom)
                for i,leg in enumerate(LEGS):
                    if name==f'{leg}_foot_contact_proxy': self.foot_geoms[geom]=i
            if len(self.foot_geoms)!=4 or not self.floor:
                raise ValueError('Unmapped batch floor or feet')
        super().__init__(n_envs,self.tasks[0].observation_space,self.tasks[0].action_space)

    def _reset_worlds(self, indices):
        q = self.s0.joint_q.numpy().reshape(self.num_envs,19)
        v = self.s0.joint_qd.numpy().reshape(self.num_envs,18)
        for i in indices:
            task = self.tasks[i]
            seed = self._seeds[i] if self._seeds[i] is not None else self.seed_base+i+100003*self.reset_counts[i]
            task.reset(seed=int(seed))
            q[i] = task.data.qpos
            q[i,3:7] = task.data.qpos[[4,5,6,3]]
            v[i] = 0
            task.gpu_forces[:] = 0
            self.reset_counts[i] += 1
        self.s0.joint_q.assign(q.astype(np.float32).reshape(-1))
        self.s0.joint_qd.assign(v.astype(np.float32).reshape(-1))
        newton.eval_fk(self.model,self.s0.joint_q,self.s0.joint_qd,self.s0)

    def reset(self):
        with wp.ScopedDevice('cuda:0'):
            self._reset_worlds(range(self.num_envs))
        self._reset_seeds()
        self._reset_options()
        return np.stack([t._obs() for t in self.tasks])

    def step_async(self, actions):
        self.actions = np.asarray(actions)

    def _advance(self, active):
        self.control.mujoco.ctrl.assign(np.stack([t.data.ctrl for t in self.tasks]).astype(np.float32).reshape(-1))
        self.s0.clear_forces()
        self.solver.step(self.s0,self.s1,self.control,None,self.tasks[0].model.opt.timestep)
        self.s0,self.s1 = self.s1,self.s0
        d = self.solver.mjw_data
        q,v,act = d.qpos.numpy(),d.qvel.numpy(),d.actuator_force.numpy()
        mjw.contact_force(self.solver.mjw_model,d,self.contact_ids,False,self.contact_forces)
        n = int(d.nacon.numpy()[0])
        if n>=self.capacity: raise RuntimeError('Contact capacity exhausted; increase nconmax')
        geoms,worlds = d.contact.geom.numpy()[:n],d.contact.worldid.numpy()[:n]
        normal = self.contact_forces.numpy()[:n,0]
        forces = np.zeros((self.num_envs,4))
        for (g1,g2),world,f in zip(geoms,worlds,normal):
            other = g2 if g1 in self.floor else g1 if g2 in self.floor else -1
            if other in self.foot_geoms:
                forces[world,self.foot_geoms[other]] += max(0.,f)
        for i in active:
            t = self.tasks[i]
            t.data.qpos[:],t.data.qvel[:] = q[i],v[i]
            t.data.time += t.model.opt.timestep
            mujoco.mj_forward(t.model,t.data)
            t.data.actuator_force[:] = act[i]
            t.gpu_forces[:] = forces[i]

    def step_wait(self):
        sequences = [t._step_sequence(a) for t,a in zip(self.tasks,self.actions)]
        active = set(range(self.num_envs))
        results = [None]*self.num_envs
        with wp.ScopedDevice('cuda:0'):
            while active:
                for i in list(active):
                    try:
                        next(sequences[i])
                    except StopIteration as result:
                        results[i] = result.value
                        active.remove(i)
                if active: self._advance(active)
            obs,rewards,dones,infos = [],[],[],[]
            resets = []
            for i,(o,r,terminated,truncated,info) in enumerate(results):
                done = terminated or truncated
                info['TimeLimit.truncated'] = truncated and not terminated
                if done:
                    info['terminal_observation'] = o.copy()
                    resets.append(i)
                obs.append(o); rewards.append(r); dones.append(done); infos.append(info)
            if resets:
                self._reset_worlds(resets)
                for i in resets: obs[i] = self.tasks[i]._obs()
        return np.stack(obs),np.asarray(rewards,np.float32),np.asarray(dones,bool),infos

    def close(self):
        for t in self.tasks: t.close()

    def get_attr(self, name, indices=None):
        return [getattr(self.tasks[i],name) for i in self._get_indices(indices)]

    def set_attr(self, name, value, indices=None):
        for i in self._get_indices(indices): setattr(self.tasks[i],name,value)

    def env_method(self, name, *args, indices=None, **kwargs):
        return [getattr(self.tasks[i],name)(*args,**kwargs) for i in self._get_indices(indices)]

    def env_is_wrapped(self, wrapper_class, indices=None):
        return [False for _ in self._get_indices(indices)]

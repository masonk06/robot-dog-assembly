"""CUDA-resident version-7 task: Newton physics and Torch observations/rewards.

CPU access is restricted to construction, validation and checkpoint/log boundaries.
"""
import math
import numpy as np
import mujoco
import mujoco_warp as mjw
import newton
import torch
import warp as wp
from env import DogWalkEnv, LEGS


@wp.kernel
def sum_foot_forces(n: wp.array[int], geoms: wp.array[wp.vec2i], worlds: wp.array[int],
                    tags: wp.array[int], force: wp.array[wp.spatial_vector], out: wp.array2d[float]):
    i = wp.tid()
    if i < n[0]:
        pair = geoms[i]
        a,b = tags[pair[0]],tags[pair[1]]
        foot = int(-1)
        if a == -2: foot = b
        if b == -2: foot = a
        if foot >= 0:
            wp.atomic_add(out,worlds[i],foot,wp.max(0.0,force[i][0]))


class CudaTask:
    def __init__(self,n,config,model_path,seed=42):
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA-enabled PyTorch is required; CPU torch cannot run this trainer')
        if config.reward_version != 7:
            raise ValueError('Only the validated version-7 controller is supported')
        self.n,self.cfg,self.device = n,config,torch.device('cuda:0')
        torch.manual_seed(seed)
        wp.init()
        # All zero-copy Torch/Warp views share one CUDA stream; no implicit
        # assumptions about ordering between independent default streams.
        wp.set_stream(wp.stream_from_torch(torch.cuda.current_stream(self.device)))
        self.probe = DogWalkEnv(config,model_path=model_path)
        p = self.probe
        with wp.ScopedDevice('cuda:0'):
            robot = newton.ModelBuilder()
            newton.solvers.SolverMuJoCo.register_custom_attributes(robot)
            robot.add_mjcf(str(p.model_path),parse_visuals=False,ctrl_direct=True)
            b = newton.ModelBuilder()
            newton.solvers.SolverMuJoCo.register_custom_attributes(b)
            b.replicate(robot,n)
            self.model = b.finalize()
            self.solver = newton.solvers.SolverMuJoCo(self.model,separate_worlds=True,
                use_mujoco_contacts=True,njmax=256,nconmax=128)
            m = self.solver.mj_model
            for field in ('jnt_type','jnt_axis','jnt_qposadr','jnt_dofadr','jnt_range',
                          'actuator_trnid','actuator_gainprm','actuator_biasprm','actuator_forcerange',
                          'site_pos','site_bodyid','body_rootid'):
                np.testing.assert_allclose(getattr(m,field),getattr(p.model,field),atol=1e-6)
            self.s0,self.s1,self.control = self.model.state(),self.model.state(),self.model.control()
            self.d = self.solver.mjw_data
            self.m = self.solver.mjw_model
            cap = self.d.contact.geom.shape[0]
            self.capacity = cap
            self.contact_ids = wp.array(np.arange(cap,dtype=np.int32),dtype=int)
            self.contact_wrenches = wp.zeros(cap,dtype=wp.spatial_vector)
            self.foot_force_wp = wp.zeros((n,4),dtype=float)
            self.forces = wp.to_torch(self.foot_force_wp)
            tags = np.full(m.ngeom,-1,dtype=np.int32)
            mapping = self.solver.mjc_geom_to_newton_shape.numpy()[0]
            for geom,shape in enumerate(mapping):
                if shape<0: continue
                name = self.model.shape_label[shape].split('/')[-1]
                if name=='floor': tags[geom] = -2
                for i,leg in enumerate(LEGS):
                    if name==f'{leg}_foot_contact_proxy': tags[geom]=i
            assert sum(tags>=0)==4 and -2 in tags
            self.tags = wp.array(tags,dtype=int)
        def tensor(x,dtype=torch.float32): return torch.as_tensor(np.asarray(x),dtype=dtype,device=self.device)
        self.tensor = tensor
        self.base,self.feet = p.base,tensor(p.feet,torch.long)
        self.foot_bodies = tensor(p.model.site_bodyid[p.feet],torch.long)
        self.root_bodies = tensor(p.model.body_rootid[p.model.site_bodyid[p.feet]],torch.long)
        self.qadr,self.vadr = tensor(p.qadr,torch.long),tensor(p.vadr,torch.long)
        self.limits = tensor(p.limits)
        self.initial_q = tensor(p.data.qpos.copy())
        # MjData is not initialized until reset: use the exact original reset state.
        p.reset(seed=seed)
        self.initial_q = tensor(p.model.qpos0)
        self.offsets = tensor([.25,.75,0.,.5])
        self.sway_sign = tensor([-1,1,-1,1])
        self.quaternion_order = tensor([4,5,6,3],torch.long)
        self.upper = tensor([p.model.body_pos[mujoco.mj_name2id(p.model,mujoco.mjtObj.mjOBJ_BODY,f'{leg}_lower_link')][[0,2]] for leg in LEGS])
        self.lower = tensor(p.model.site_pos[p.feet][:,[0,2]])
        self.hip_indices = tensor([p.names.index(f'{leg}_hip_pitch') for leg in LEGS],torch.long)
        self.knee_indices = tensor([p.names.index(f'{leg}_knee_pitch') for leg in LEGS],torch.long)
        self.roll_indices = tensor([p.names.index(f'{leg}_hip_roll') for leg in LEGS],torch.long)
        self.time = torch.zeros(n,device=self.device)
        self.last_action = torch.zeros((n,12),device=self.device)
        self.filtered = torch.zeros_like(self.last_action)
        self.targets = torch.zeros_like(self.last_action)
        self.actuator = torch.zeros_like(self.last_action)
        self.overflow = torch.zeros((),dtype=torch.bool,device=self.device)
        # Explicit per-world/foot state for step rewards and sliding detection.
        self.supported = torch.zeros((n,4),device=self.device,dtype=torch.bool)
        self.previous = self.supported.clone()
        self.credits = self.supported.clone()
        self.lift_paid = self.supported.clone()
        self.air = torch.zeros((n,4),device=self.device)
        self.clearance = self.air.clone()
        self.last_step = torch.full_like(self.air,-float('inf'))
        self.last_lift = self.last_step.clone()
        self.body_touch = self.air.clone()
        self.counts = self.air.clone()
        self.lift = torch.zeros((n,4,3),device=self.device)
        self.anchors = torch.zeros((n,4,2),device=self.device)
        self.age = self.air.clone()
        self.gap = torch.ones_like(self.air)
        self.bad_time = self.air.clone()
        self.episode_return = self.time.clone()
        self.reset(torch.ones(n,dtype=torch.bool,device=self.device))

    def reference(self):
        c = self.cfg
        phase = (self.time/c.gait_cycle_seconds)%1
        local = (phase[:,None]-self.offsets)%1
        swing = local<.2
        t = torch.where(swing,local/.2,(local-.2)/.8)
        smooth = t*t*(3-2*t)
        xoff = c.reference_stride*torch.where(swing,.5-smooth,-.5+smooth)
        lift = c.reference_lift*torch.sin(math.pi*t).square()*swing
        lift[:,2:] *= c.reference_rear_lift_multiplier
        shift = c.reference_weight_shift*torch.cos(4*math.pi*(phase-.1))
        x = self.upper[:,0]+self.lower[:,0]+xoff+shift[:,None]
        z = self.upper[:,1]+self.lower[:,1]+lift
        l1,l2 = self.upper.norm(dim=1),self.lower.norm(dim=1)
        alpha,beta = torch.atan2(self.upper[:,1],self.upper[:,0]),torch.atan2(self.lower[:,1],self.lower[:,0])
        elbow = torch.sign(beta-alpha)*torch.acos(((x*x+z*z-l1*l1-l2*l2)/(2*l1*l2)).clamp(-1,1))
        hip = torch.atan2(z,x)-torch.atan2(l2*torch.sin(elbow),l1+l2*torch.cos(elbow))-alpha
        knee = elbow-(beta-alpha)
        ramp = (self.time/c.reference_ramp_seconds).clamp(0,1)
        ramp = ramp*ramp*(3-2*ramp)
        result = torch.zeros_like(self.targets)
        result[:,self.hip_indices] = hip*ramp[:,None]
        result[:,self.knee_indices] = knee*ramp[:,None]
        curve = torch.sin(math.pi*(local/.2).clamp(0,1))*swing
        sway = (curve*self.sway_sign).sum(1)*c.reference_sway*ramp
        result[:,self.roll_indices] = sway[:,None]
        return result

    def _kinematics(self):
        mjw.kinematics(self.m,self.d)
        mjw.com_pos(self.m,self.d)
        mjw.com_vel(self.m,self.d)
        xpos,xmat,cvel,com = [wp.to_torch(x) for x in (self.d.xpos,self.d.xmat,self.d.cvel,self.d.subtree_com)]
        pos = wp.to_torch(self.d.site_xpos)[:,self.feet]
        angular = cvel[:,self.foot_bodies,:3]
        vel = cvel[:,self.foot_bodies,3:] + torch.cross(angular,pos-com[:,self.root_bodies],dim=2)
        rot = xmat[:,self.base]
        ba = cvel[:,self.base,:3]
        root = int(self.probe.model.body_rootid[self.base])
        # mj_objectVelocity(BODY) reports velocity at the body's inertial COM,
        # while a SITE uses its site origin. Keep the saved observation contract.
        xipos = wp.to_torch(self.d.xipos)
        bv = cvel[:,self.base,3:] + torch.cross(ba,xipos[:,self.base]-com[:,root],dim=1)
        transpose = rot.transpose(1,2)
        gravity = -rot[:,2,:]
        ba = torch.bmm(transpose,ba[:,:,None]).squeeze(2)
        bv = torch.bmm(transpose,bv[:,:,None]).squeeze(2)
        return pos.clone(),vel.clone(),gravity.clone(),ba,bv,xpos[:,self.base].clone()

    def reset(self,mask):
        # Fixed-size masked writes avoid GPU->CPU index synchronization.
        q = self.initial_q[None].expand(self.n,-1).clone()
        noise = (torch.rand((self.n,12),device=self.device)*2-1)*self.cfg.reset_noise
        q[:,self.qadr] = noise.clamp(self.limits[:,0],self.limits[:,1])
        nq = q.clone(); nq[:,3:7] = q[:,self.quaternion_order]
        for state in (self.s0,self.s1):
            jq = wp.to_torch(state.joint_q).view(self.n,19)
            jv = wp.to_torch(state.joint_qd).view(self.n,18)
            jq.copy_(torch.where(mask[:,None],nq,jq))
            jv.masked_fill_(mask[:,None],0)
        self.solver._update_mjc_data(self.d,self.model,self.s0)
        wp.to_torch(self.d.qacc_warmstart).masked_fill_(mask[:,None],0)
        self.time.masked_fill_(mask,0)
        self.episode_return.masked_fill_(mask,0)
        self.last_action.masked_fill_(mask[:,None],0)
        self.filtered.masked_fill_(mask[:,None],0)
        self.actuator.masked_fill_(mask[:,None],0)
        self.targets.copy_(torch.where(mask[:,None],q[:,self.qadr],self.targets))
        for name in ('supported','previous','credits','lift_paid','air','clearance','body_touch','counts','age','bad_time'):
            getattr(self,name).masked_fill_(mask[:,None],0)
        self.gap.masked_fill_(mask[:,None],1)
        self.last_step.masked_fill_(mask[:,None],-float('inf'))
        self.last_lift.masked_fill_(mask[:,None],-float('inf'))
        self.lift.masked_fill_(mask[:,None,None],0)
        self.anchors.masked_fill_(mask[:,None,None],0)
        fresh = self._kinematics()
        if not hasattr(self,'fpos'):
            self.fpos,self.fvel,self.gravity,self.angular,self.linear,self.basepos = fresh
            self.q = wp.to_torch(self.d.qpos).clone()
            self.qv = wp.to_torch(self.d.qvel).clone()
            self.normal = torch.zeros_like(self.air)
        else:
            for name,value in zip(('fpos','fvel','gravity','angular','linear','basepos'),fresh):
                old = getattr(self,name)
                shape = (self.n,)+(1,)*(old.ndim-1)
                old.copy_(torch.where(mask.view(shape),value,old))
            self.q.copy_(torch.where(mask[:,None],wp.to_torch(self.d.qpos),self.q))
            self.qv.copy_(torch.where(mask[:,None],wp.to_torch(self.d.qvel),self.qv))
            self.normal.masked_fill_(mask[:,None],0)
        return self.obs()

    def obs(self):
        phase = self.time/self.cfg.gait_cycle_seconds*2*math.pi
        return torch.cat((self.gravity,self.angular,self.linear,
            torch.full((self.n,1),self.cfg.target_speed,device=self.device),
            self.q[:,self.qadr],self.qv[:,self.vadr],self.last_action,
            torch.stack((phase.sin(),phase.cos()),dim=1),self.reference()),dim=1)

    @torch.no_grad()
    def step(self,actions):
        c = self.cfg
        action = actions.clamp(-1,1)
        self.filtered += (1-math.exp(-c.control_dt/c.residual_time_constant))*(action-self.filtered)
        desired = (self.reference()+c.action_scale*self.filtered).clamp(self.limits[:,0],self.limits[:,1])
        self.targets += (desired-self.targets).clamp(-c.max_target_rate*c.control_dt,c.max_target_rate*c.control_dt)
        wp.to_torch(self.control.mujoco.ctrl).copy_(self.targets.reshape(-1))
        accum = torch.zeros((self.n,11),device=self.device)
        sliding = torch.zeros(self.n,dtype=torch.bool,device=self.device)
        for _ in range(self.probe.frame_skip):
            active = ~sliding
            prev_v = self.fvel.clone()
            self.s0.clear_forces()
            self.solver.step(self.s0,self.s1,self.control,None,self.probe.model.opt.timestep)
            self.s0,self.s1 = self.s1,self.s0
            self.overflow |= wp.to_torch(self.d.nacon)[0]>=self.capacity
            self.foot_force_wp.zero_()
            mjw.contact_force(self.m,self.d,self.contact_ids,False,self.contact_wrenches)
            wp.launch(sum_foot_forces,dim=self.capacity,inputs=[self.d.nacon,self.d.contact.geom,
                self.d.contact.worldid,self.tags,self.contact_wrenches,self.foot_force_wp],device='cuda:0')
            fresh = self._kinematics()
            for name,value in zip(('fpos','fvel','gravity','angular','linear','basepos'),fresh):
                old=getattr(self,name); shape=(self.n,)+(1,)*(old.ndim-1)
                old.copy_(torch.where(active.view(shape),value,old))
            self.q.copy_(torch.where(active[:,None],wp.to_torch(self.d.qpos),self.q))
            self.qv.copy_(torch.where(active[:,None],wp.to_torch(self.d.qvel),self.qv))
            self.actuator.copy_(torch.where(active[:,None],wp.to_torch(self.d.actuator_force),self.actuator))
            self.normal.copy_(torch.where(active[:,None],self.forces,self.normal))
            dt = self.probe.model.opt.timestep
            self.time += active*dt
            contact = self.normal>.2
            touchdown = contact & ~self.previous
            landing = (-prev_v[:,:,2]).clamp_min(0)
            impact = (((landing-c.soft_landing_speed).clamp_min(0).square())*touchdown).sum(1)
            force_cost = (self.normal/self.probe.soft_force-1).clamp_min(0).square().mean(1)/self.probe.frame_skip
            slip = (contact*self.fvel[:,:,:2].square().sum(2)).mean(1)/self.probe.frame_skip
            now = self.time[:,None]
            start = self.previous & ~contact & active[:,None]
            self.body_touch.copy_(torch.where(contact & ~self.supported & active[:,None],-self.basepos[:,0,None],self.body_touch))
            self.lift.copy_(torch.where(start[:,:,None],self.fpos,self.lift))
            self.air.masked_fill_(start,0); self.clearance.masked_fill_(start,0); self.lift_paid.masked_fill_(start,False)
            self.air += (~contact)*dt*active[:,None]
            self.clearance.copy_(torch.where(~contact,torch.maximum(self.clearance,self.fpos[:,:,2]-self.lift[:,:,2]),self.clearance))
            travel = (self.fpos[:,:,:2]-self.lift[:,:,:2]).norm(dim=2)
            lifted=(~contact & self.supported & ~self.lift_paid & (self.air>=.08) & (self.air<=.5)
                & (self.clearance>=c.lift_clearance) & (travel>=c.min_step_distance) & (now-self.last_lift>=.5) & active[:,None])
            self.lift_paid |= lifted
            self.last_lift.copy_(torch.where(lifted,now,self.last_lift))
            valid=(touchdown & self.supported & (self.air>=c.min_airtime) & (self.clearance>=c.min_clearance)
                & (travel>=c.min_step_distance) & (now-self.last_step>=.5) & (-self.basepos[:,0,None]-self.body_touch>.0005) & active[:,None])
            self.body_touch.copy_(torch.where(touchdown & (self.air>=c.min_airtime),-self.basepos[:,0,None],self.body_touch))
            self.last_step.copy_(torch.where(valid,now,self.last_step))
            self.counts += valid
            self.credits &= (now-self.last_step)<=c.leg_use_window
            self.credits |= valid
            all_four=self.credits.all(1)
            self.credits &= ~all_four[:,None]
            self.supported |= contact
            self.air.masked_fill_(contact,0)
            self.previous.copy_(contact)
            local=(self.time[:,None]/c.gait_cycle_seconds-self.offsets)%1
            swing=local<.2
            curve=torch.sin(math.pi*(local/.2).clamp(0,1))*swing
            pattern=(contact==~swing).float().mean(1)/self.probe.frame_skip
            clearance=(self.fpos[:,:,2]-.003).clamp_min(0)
            score=torch.exp(-((clearance-c.lift_clearance*curve)/.004).square())*(~contact)*curve
            clearance_score=score.sum(1)/swing.sum(1).clamp_min(1)/self.probe.frame_skip
            scheduled=(lifted&swing).sum(1)
            reacquire=contact&(self.gap>.04)
            self.anchors.copy_(torch.where(reacquire[:,:,None],self.fpos[:,:,:2],self.anchors))
            self.age.masked_fill_(reacquire,0); self.bad_time.masked_fill_(reacquire,0)
            self.gap.copy_(torch.where(contact,0.,self.gap+dt))
            self.age.copy_(torch.where(contact,self.age+dt,torch.where(self.gap>.04,0.,self.age)))
            self.bad_time.masked_fill_(~contact & (self.gap>.04),0)
            drift=(self.fpos[:,:,:2]-self.anchors).norm(dim=2)
            bad=contact & (self.age>=.08) & (now>c.slip_grace) & ((drift>c.severe_slip_distance)|(self.fvel[:,:,:2].norm(dim=2)>c.severe_slip_speed))
            self.bad_time.copy_(torch.where(bad,self.bad_time+dt,0.))
            sliding |= ((self.bad_time>=c.severe_slip_duration).any(1)&active)
            values=torch.stack((impact,force_cost,slip,valid.sum(1),all_four,lifted.sum(1),scheduled,
                                pattern,clearance_score,self.normal.max(1).values,(landing*touchdown).max(1).values),dim=1)
            accum[:,:9] += values[:,:9]*active[:,None]
            accum[:,9:] = torch.maximum(accum[:,9:],values[:,9:]*active[:,None])
        forward=-self.linear[:,0]
        tilt=torch.acos((-self.gravity[:,2]).clamp(-1,1))
        finite=self.q.isfinite().all(1)&self.qv.isfinite().all(1)
        fallen=~finite | (self.basepos[:,2]<c.min_height) | (tilt>math.radians(c.max_tilt_degrees))
        stale=((self.time[:,None]-self.last_step)/c.leg_use_window).clamp(0,1).mean(1)
        terms={
            'tracking':c.tracking_reward_weight*torch.exp(-((forward-c.target_speed)/.03).square())*(~sliding),
            'progress':(forward/c.target_speed).clamp(-1,1)*(~sliding),
            'lateral':-2*self.linear[:,1].square(),'vertical':-.5*self.linear[:,2].square(),
            'tilt':-self.gravity[:,:2].square().sum(1),'rotation':-.05*self.angular.square().sum(1),
            'effort':-.002*self.actuator.square().mean(1),
            'smoothness':-.02*(action-self.last_action).square().mean(1),'fall':-5*fallen.float(),
            'stomp':-2*accum[:,0]-.1*accum[:,1], 'foot_slip':-2*(accum[:,2]/.03**2).clamp(0,10),
            'useful_steps':.2*accum[:,3],'all_four_legs':.8*accum[:,4],
            'unused_legs':-.1*stale*(self.time>4), 'foot_lift':.75*accum[:,5],
            'slide_reset':-5*sliding.float(),'scheduled_lift':.25*accum[:,6],
            'gait_contacts':.2*accum[:,7],'gait_clearance':.8*accum[:,8],
            'residual_size':-.05*action.square().mean(1)}
        reward=torch.where(finite,sum(terms.values()),-5.)
        self.last_action.copy_(action)
        self.episode_return += reward
        terminated=fallen|sliding
        timeout=self.time>=c.episode_seconds-1e-5
        obs=torch.nan_to_num(self.obs())
        metrics={'forward_distance_m':-self.basepos[:,0], 'forward_speed_m_s':forward,
            'fallen':fallen,'sliding':sliding,'seconds':self.time.clone(),
            'four_leg_cycles':accum[:,4],'foot_lifts':accum[:,5],
            'slip_cost':accum[:,2],'peak_force_n':accum[:,9],'peak_landing_m_s':accum[:,10],
            'steps':self.counts.clone(),'episode_return':self.episode_return.clone(),
            **{f'reward/{k}':v for k,v in terms.items()}}
        return obs,reward,terminated,timeout,metrics

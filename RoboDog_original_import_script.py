import adsk.core,adsk.fusion,json,traceback,math
from pathlib import Path
ROOT=Path(r"C:\Users\mmbec\Downloads\Robot Dog Servo Assembly")
def run(context):
 app=adsk.core.Application.get();log=ROOT/'direct_mount_log.txt';log.write_text('Starting connected mechanical assembly\n')
 def status(text):
  with log.open('a') as f:f.write(text+'\n')
 try:
  prior=app.activeDocument;prior_design=adsk.fusion.Design.cast(app.activeProduct)
  if prior and prior.name.startswith('Robot Dog - Direct Servo Mount - NO ADAPTERS') and prior_design.rootComponent.asBuiltJoints.count<12:prior.close(False)
  doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType);doc.name='Robot Dog - Direct Servo Mount - NO ADAPTERS'
  design=adsk.fusion.Design.cast(app.activeProduct);design.designType=adsk.fusion.DesignTypes.DirectDesignType
  design.fusionUnitsManager.distanceDisplayUnits=adsk.fusion.DistanceUnits.MillimeterDistanceUnits
  root=design.rootComponent;records={p['name']:p for p in json.loads((ROOT/'placements_direct_mount.json').read_text())['parts']}
  def matrix(m):
   result=adsk.core.Matrix3D.create()
   for row in range(4):
    for col in range(4):result.setCell(row,col,m[row][col]/10 if row<3 and col==3 else m[row][col])
   return result
  def group(name):
   occ=root.occurrences.addNewComponent(adsk.core.Matrix3D.create());occ.component.name=name
   occ.isGroundToParent=False;occ.isGrounded=False
   return occ
  def mesh(parent,name):
   bodies=parent.component.meshBodies.add(str(ROOT/'direct_mount_parts'/(name+'.stl')),adsk.fusion.MeshUnits.MillimeterMeshUnit)
   assert bodies and bodies.count>0
   for i in range(bodies.count):bodies.item(i).name=name
  prototypes={};servolist=[]
  def ground_children(comp):
   for i in range(comp.occurrences.count):
    child=comp.occurrences.item(i);child.isGroundToParent=True;ground_children(child.component)
  def servo(parent,role,part,placement):
   key=part
   if key not in prototypes:
    occ=parent.component.occurrences.addNewComponent(adsk.core.Matrix3D.create());occ.component.name='STS3215 '+part
    options=app.importManager.createSTEPImportOptions(str(ROOT/'source'/('STS3215_case_fixed.step' if part=='fixed case' else 'STS3215_discs_output.step')));options.isViewFit=False
    assert app.importManager.importToTarget(options,occ.component)
    ground_children(occ.component);prototypes[key]=occ.component
   else:occ=parent.component.occurrences.addExistingComponent(prototypes[key],adsk.core.Matrix3D.create())
   occ.isGroundToParent=False
   proxy=occ.createForAssemblyContext(parent)
   proxy.transform2=matrix(records[placement]['transform']);occ.isGroundToParent=True
   occ.attributes.add('RobotDog','role',role);occ.attributes.add('RobotDog','servo',placement)
   servolist.append(dict(role=role,part=part,parent=parent.component.name,servo=placement))
   return occ
  fixed=group('00 FRAME - fixed chassis + FOUR HIP ROLL CASES');mesh(fixed,'frame');mesh(fixed,'top_cover');fixed.isGrounded=True
  joints=[];joint_requests=[];carriers={}
  def joint(name,a,b,placement,direction):
   m=records[placement]['transform'];local=[12.5,0,1.55]
   xyz=[(m[row][3]+sum(m[row][k]*local[k] for k in range(3)))/10 for row in range(3)]
   inp=root.constructionPoints.createInput();assert inp.setByPoint(adsk.core.Point3D.create(*xyz))
   point=root.constructionPoints.add(inp);point.name=name+' axis datum';point.isLightBulbOn=False
   geometry=adsk.fusion.JointGeometry.createByPoint(point)
   joint_requests.append((name,a,b,geometry,direction))
  for leg in ['front_left','front_right','rear_left','rear_right']:
   carrier=group(leg+' 01 ROLL OUTPUT - U bracket + HIP PITCH CASE')
   upper=group(leg+' 02 PITCH OUTPUT - paired links + KNEE CASE')
   lower=group(leg+' 03 KNEE OUTPUT - foot')
   carriers[leg]=carrier
   mesh(carrier,leg+'_hip_roll');mesh(upper,leg+'_hip_pitch_L');mesh(upper,leg+'_hip_pitch_R');mesh(lower,leg+'_knee_v2')
   servo(fixed,'HIP ROLL case FIXED TO FRAME','fixed case',leg+'_servo_hip_roll')
   servo(carrier,'HIP ROLL silver discs DRIVE U BRACKET','output discs',leg+'_servo_hip_roll')
   servo(carrier,'HIP PITCH case FIXED TO MOVING U BRACKET','fixed case',leg+'_servo_hip_pitch')
   servo(upper,'HIP PITCH silver discs DRIVE PAIRED LINKS','output discs',leg+'_servo_hip_pitch')
   servo(upper,'KNEE case FIXED TO UPPER LINKS','fixed case',leg+'_servo_knee_pitch')
   servo(lower,'KNEE silver discs DRIVE FOOT','output discs',leg+'_servo_knee_pitch')
   joint(leg+' HIP ROLL: FRAME to U BRACKET',fixed,carrier,leg+'_servo_hip_roll',adsk.fusion.JointDirections.XAxisJointDirection)
   joint(leg+' HIP PITCH: U BRACKET to LINKS',carrier,upper,leg+'_servo_hip_pitch',adsk.fusion.JointDirections.YAxisJointDirection)
   joint(leg+' KNEE: LINKS to FOOT',upper,lower,leg+'_servo_knee_pitch',adsk.fusion.JointDirections.YAxisJointDirection)
   status('Built '+leg+': FRAME -> ROLL CASE -> ROLL DISCS/U BRACKET -> PITCH CASE -> LINKS -> KNEE/FOOT')
  hardware=fixed.component.occurrences.addNewComponent(adsk.core.Matrix3D.create())
  hardware.component.name='M2 direct mounting screws and washers - NO ADAPTERS'
  options=app.importManager.createSTEPImportOptions(str(ROOT/'m2_hardware/Direct_M2_screws_only.step'));options.isViewFit=False
  assert app.importManager.importToTarget(options,hardware.component)
  ground_children(hardware.component);hardware.isGroundToParent=True
  status('Direct servo mounting: no added brackets, bridges or spacers; M2 screw envelopes only')
  design.designType=adsk.fusion.DesignTypes.ParametricDesignType
  for name,a,b,geometry,direction in joint_requests:
   ji=root.asBuiltJoints.createInput(a,b,geometry);assert ji.setAsRevoluteJointMotion(direction)
   result=root.asBuiltJoints.add(ji);result.name=name;joints.append(result)
  assert root.asBuiltJoints.count==12
  assert len(servolist)==24
  # Smoke-test each hip-roll joint, then return to the original pose.
  motion_checks=[]
  for leg in ['front_left','front_right','rear_left','rear_right']:
   j=next(j for j in joints if j.name==leg+' HIP ROLL: FRAME to U BRACKET')
   motion=adsk.fusion.RevoluteJointMotion.cast(j.jointMotion)
   before=list(carriers[leg].transform2.asArray());motion.rotationValue=.04;adsk.doEvents()
   after=list(carriers[leg].transform2.asArray());delta=max(abs(a-b) for a,b in zip(before,after))
   motion.rotationValue=0;adsk.doEvents()
   motion_checks.append(dict(leg=leg,roll_test_radians=.04,carrier_transform_change=delta,frame_fixed=fixed.isGrounded))
  # Assign visible role colours without modifying any geometry.
  try:
   seed=None;propid=None
   for li in range(app.materialLibraries.count):
    lib=app.materialLibraries.item(li)
    for ai in range(lib.appearances.count):
     candidate=lib.appearances.item(ai)
     for key in ['generic_diffuse','opaque_albedo']:
      if adsk.core.ColorProperty.cast(candidate.appearanceProperties.itemById(key)):
       seed=candidate;propid=key;break
     if seed:break
    if seed:break
   if seed:
    colours={}
    for role,rgb in [('HIP ROLL',(45,110,210)),('HIP PITCH',(235,145,35)),('KNEE',(70,155,95)),('OUTPUT',(195,195,205))]:
     appearance=design.appearances.addByCopy(seed,'Robot Dog '+role)
     adsk.core.ColorProperty.cast(appearance.appearanceProperties.itemById(propid)).value=adsk.core.Color.create(*rgb,255);colours[role]=appearance
    def colour_children(parent):
     for i in range(parent.occurrences.count):
      occ=parent.occurrences.item(i);attr=occ.attributes.itemByName('RobotDog','role')
      if attr:
       text=attr.value;key='OUTPUT' if 'silver discs' in text else 'HIP ROLL' if 'HIP ROLL' in text else 'HIP PITCH' if 'HIP PITCH' in text else 'KNEE'
       occ.appearance=colours[key]
    for i in range(root.occurrences.count):colour_children(root.occurrences.item(i).component)
  except Exception:status('Colour assignment skipped: '+traceback.format_exc())
  camera=app.activeViewport.camera;camera.viewOrientation=adsk.core.ViewOrientations.IsoTopRightViewOrientation;camera.isFitView=True;app.activeViewport.camera=camera
  archive=ROOT/'Robot_Dog_Direct_Servo_Mount.f3d'
  assert design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(archive)))
  verification=dict(top_level_rigid_links=root.occurrences.count,revolute_joints=root.asBuiltJoints.count,servo_part_assignments=servolist,motion_checks=motion_checks,archive=str(archive))
  (ROOT/'direct_mount_verification.json').write_text(json.dumps(verification,indent=2))
  status('SUCCESS: 13 links, 12 revolute joints, 12 case+disc pairs. '+str(archive))
 except Exception:
  status(traceback.format_exc());app.userInterface.messageBox(traceback.format_exc())

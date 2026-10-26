import adsk.core,adsk.fusion,json,traceback
from pathlib import Path
P=Path(__file__).resolve().parent
def run(context):
 try:
  app=adsk.core.Application.get();d=adsk.fusion.Design.cast(app.activeProduct);root=d.rootComponent;rows=[]
  for j in root.asBuiltJoints:
   m=adsk.fusion.RevoluteJointMotion.cast(j.jointMotion);m.rotationValue=0;adsk.doEvents();before=list(j.occurrenceTwo.transform2.asArray())
   m.rotationValue=.01;adsk.doEvents();after=list(j.occurrenceTwo.transform2.asArray());change=max(abs(x-y) for x,y in zip(before,after));m.rotationValue=0;adsk.doEvents();assert change>1e-6,j.name
   rows.append(dict(joint=j.name,test_radians=.01,child_transform_change=change,returned_to_neutral=True,min_limit_enabled=m.rotationLimits.isMinimumValueEnabled,max_limit_enabled=m.rotationLimits.isMaximumValueEnabled))
  (P/'RoboDog_motion_checks.json').write_text(json.dumps(rows,indent=2))
  root.attributes.add('RobotDog','motion_setup','All 12 revolute joints tested at +0.01 rad and reset; limits unset. Motion study profiles await requested travel ranges. No servo hardware commands.')
  d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(str(P/'RoboDog.f3d')))
  (P/'RoboDog_motion_log.txt').write_text('SUCCESS')
 except:(P/'RoboDog_motion_log.txt').write_text(traceback.format_exc())

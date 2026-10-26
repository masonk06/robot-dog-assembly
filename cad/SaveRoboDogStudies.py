import adsk.core,adsk.fusion,json,traceback
from pathlib import Path
P=Path(__file__).resolve().parent
def run(context):
 try:
  app=adsk.core.Application.get();doc=app.activeDocument;design=adsk.fusion.Design.cast(app.activeProduct);products=[app.activeProduct.objectType]
  assert design,'No design product';root=design.rootComponent;rows=[]
  for j in root.asBuiltJoints:
   m=adsk.fusion.RevoluteJointMotion.cast(j.jointMotion);m.rotationValue=0
   rows.append(dict(name=j.name,min_limit_enabled=m.rotationLimits.isMinimumValueEnabled,max_limit_enabled=m.rotationLimits.isMaximumValueEnabled))
  adsk.doEvents();root.attributes.add('RobotDog','native_simulation_setup','Static Stress draft with 7.3549875N downward force on frame floor; Modal Frequencies draft. Not solved. Material/support/contact and mass details pending.')
  root.attributes.add('RobotDog','printed_material_setup','PETG assumption: hip roll 35%, other printed parts 20%; effective mechanical properties NOT assigned from infill')
  design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(P/'RoboDog.f3d')))
  app.activeViewport.saveAsImageFile(str(P/'RoboDog_preview.png'),1200,900)
  materials=[]
  for c in design.allComponents:
   if c.name.startswith('Part Studio') or c.name in ['FRAME V2','boots']:
    materials.append(dict(component=c.name,material='Not assigned: printed PETG effective properties pending'))
  (P/'RoboDog_final_state.json').write_text(json.dumps(dict(products=products,joints=rows,materials=materials,grounded_frame=root.occurrences.item(0).isGrounded,exported=str(P/'RoboDog.f3d')),indent=2))
  (P/'RoboDog_save_log.txt').write_text('SUCCESS')
 except: (P/'RoboDog_save_log.txt').write_text(traceback.format_exc())

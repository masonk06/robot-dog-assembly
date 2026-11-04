from pathlib import Path
source=(Path(__file__).parent/'route_layers.py').read_text()
exec(compile(source.split('unresolved=[]',1)[0],'route_layers.py','exec'))
requests=[('J11','2','J10','2',3),('J2','2','J5','2',3),('J5','2','J7','2',3),('J11','1','J10','3',1)]
for ar,an,cr,cn,w in requests:
 a,c=pad(ar,an),pad(cr,cn);n=a.GetNetCode();aa,cc=r.xy(a),r.xy(c)
 print('TRY',ar,cr,aa,cc,'endpoint masks',[(l,bool(r.make_mask(n,w,l)[r.idx(aa)]),bool(r.make_mask(n,w,l)[r.idx(cc)])) for l in (0,2)],flush=True)
 result=route3(aa,cc,n,w)
 if result:commit(result,aa,cc,n,w);print('COMPLETED',ar,cr,flush=True)
 else:print('UNFINISHED',ar,cr,flush=True)
p.SaveBoard(str(target),r.b)

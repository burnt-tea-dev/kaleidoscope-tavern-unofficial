from pathlib import Path
import json, hashlib, datetime
from PIL import Image
p=Path(__file__).resolve().parent.parent
out=Path(__file__).resolve().parent
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def write(name,data): (out/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
pre=json.loads((out/'preflight-integrity.json').read_text())
errors=[]
for rel,expected in pre['original_hashes'].items():
 actual=sha(p/rel)
 if actual!=expected: errors.append({'file':rel,'expected':expected,'actual':actual})
if sha(p/'artifact-sha256.json')!=pre['original_manifest_sha256']: errors.append({'file':'artifact-sha256.json','error':'manifest changed'})
assert not errors,errors
scenes=json.loads((out/'scene-identity-index.json').read_text())
by_scene={s['scene']:s for s in scenes}
def fileinfo(rel):
 f=out/rel
 with Image.open(f) as im: fmt=im.format; dims=list(im.size)
 return {'file':rel,'sha256':sha(f),'bytes':f.stat().st_size,'format':fmt,'dimensions':dims,'file_mtime_utc':datetime.datetime.fromtimestamp(f.stat().st_mtime,datetime.timezone.utc).isoformat()}
specs=[
 ('01-upright-top.jpg','01-upright-isolated.bbmodel','Top orthographic; selected all meshes, Center View on Selection, Edit > Unselect All, zoom out 500 pixels.',
  'SOURCE is screen-left, BEFORE center, AFTER screen-right in this Top view. The positive X gizmo points right.',
  'All three broad-face silhouettes are complete and unobstructed. AFTER visibly restores the source broad-face scale, while BEFORE is half the linear size. BEFORE and AFTER retain the same sprite orientation. Source uses its separate audited frame, so its mirrored projected sprite direction is not a facing defect.',
  'The exact 8×8×0.5 versus 4×4×0.25 dimensions and zero centers are source/data evidence. This screenshot supplies a common orthographic visual check, not subpixel metrology.'),
 ('02-upright-oblique.jpg','01-upright-isolated.bbmodel','True Isometric Left (30°), orthographic; selected all, centered, unselected; zoom out 250 pixels.',
  'SOURCE is upper-right, BEFORE near center, AFTER lower-left. This angle reverses the source/after screen ordering relative to Top.',
  'The oblique view retains the enlarged AFTER footprint and half-size BEFORE. Source shows a shallow generated edge profile; the native cards remain two broad-face approximations. The size candidate does not introduce the source edge strips.',
  'This 30° oblique is supplementary edge context. The image does not resolve or independently count every one of the 35 source quads, and does not establish native alpha-edge, shader, or culling behavior.'),
 ('03-helper-boundaries-oblique.jpg','02-upright-helper-boundaries.bbmodel','True Isometric Left (30°), orthographic; selected all, centered, unselected; zoom out 150 pixels.',
  'SOURCE cluster is upper-right, BEFORE center, AFTER lower-left. Each cluster contains global 0, 7, 8 and 63; exact group names and world bounds are in scene-identity-index.json.',
  'The high layer (global 63) remains separate from the low-layer representatives. BEFORE and AFTER preserve the same relative layer layout while each AFTER card expands. The 0/8 pair is close and partially overlaps in this projection, with separate layered edges visible; the existing audit, rather than the screenshot alone, establishes helper 0/local 7, helper 1/local 0 and helper 7/local 7 identities.',
  'This is representative layer/size evidence, not a visual measurement of all 64 slots or arbitrary seeds/counts. Overlap is expected and is not judged as body-clearance failure.'),
 ('04-north-tilt-south.jpg','03-north-tilt-layers.bbmodel','South orthographic; selected all, centered, unselected; zoom out 450 pixels. Chosen to expose paired faces after initial perspective was edge-on.',
  'SOURCE pair is left/upper; BEFORE pair lower-center; AFTER pair lower-right. Scene includes global 0 and 63 at tilt facing 0.',
  'Both north-tilt native representatives remain present. AFTER doubles the corresponding face size while preserving the BEFORE projected pose and relative pair arrangement. The source pair remains full sized. Source/native vertical separation reflects different prepared reference frames.',
  'No body is attached. Neither vertical placement, facing, world alignment, clearance nor native culling is accepted from this frame.'),
 ('05-east-tilt-top.jpg','04-east-tilt-layers.bbmodel','Top orthographic; selected all, centered, unselected; zoom out 700 pixels. Chosen instead of edge-on initial perspective.',
  'SOURCE pair is left, BEFORE pair center-right, AFTER pair right. Scene includes global 0 and 63 at tilt facing 1. Column offsets remain source −24, before 0, after +24, despite additional pose translations.',
  'The paired BEFORE/AFTER east-tilt sprite angles and relative separation agree visually; AFTER is doubled around the audited unchanged centers. The two AFTER surfaces partly overlap but remain distinguishable. The source faces are also visible, rather than judged from an edge-on projection.',
  'This is a tilted-plane Top projection, not an assertion that its projected width equals the unposed card edge. No body or native world/culling proof is included.'),
 ('06-ice-grape-tick1-top.jpg','05-animated-ice-grape-tick1.bbmodel','Top orthographic; selected all, centered, unselected; zoom out 400 pixels.',
  'SOURCE left, BEFORE center, AFTER right; frozen ice_grape global 0 at tick 1.',
  'The AFTER frozen ice-grape restores the large source-scale appearance and retains the BEFORE color/pixel pattern and pose. BEFORE remains half-size. All three sprites are complete and readable.',
  'Original/derived texture-byte and 24-tick pixel equality are independent data checks. This view is a frozen tick, not clock, interpolation, animation-controller, shader or ordinary-ice material execution.'),
 ('07-unchanged-barrel-stone-controls.jpg','06-unchanged-controls.bbmodel','True Isometric Left (30°), orthographic; selected all, centered, unselected; zoom out 600 pixels.',
  'For barrel grape: SOURCE upper-right, BEFORE middle-right, AFTER center. For stone: SOURCE upper-right among the cube trio, BEFORE middle-left, AFTER lower-left. Exact named group bounds are indexed; the barrel row uses +40 Y and the stone row +44 Z for separation.',
  'The two native barrel cards retain the same full size and pose. The three stone cubes retain equal size; native before/after pose and neutral stone pixels remain unchanged. The original source/native barrel-frame difference remains visible and is not altered by the pressing-card repair.',
  'Barrel remains 8×8×0.5, pressing stone 4×4×4 by the unchanged input geometry. Stone uses the explicit official Java neutral texture control, not proof of inherited native pixels.')]
captures=[]
for filename,scene,cam,caption,obs,limit in specs:
 rel='scenes/'+scene
 s=by_scene[rel]
 c=fileinfo('screenshots/'+filename)
 c.update({'scene':rel,'scene_sha256':s['sha256'],'scene_identity_index':'scene-identity-index.json','camera':cam,'visibility':'All original groups visible; no visibility filtering was used. Selection overlays cleared with Edit > Unselect All.','caption':caption,'observations':obs,'capture_specific_limits':limit,'mesh_names':[m['name'] for m in s['meshes']],'status':'accepted bounded visual observation','original_bytes':'Original app.getScreenshot Uint8Array JPEG bytes, written unchanged and the same bytes emitted for visual inspection. No editing, cropping, resizing, re-encoding or stitching.'})
 captures.append(c)
limits=[
 'Only the eight centered runtime_pressing_card cubes are proposed to change. All other data and file routes remain unchanged; no candidate or original scene was exported or saved from Blockbench.',
 'SOURCE uses Java PoseStack coordinates; native BEFORE/AFTER use raw Blockbench-decoded model-reference coordinates. The source/candidate card dimensions are basis-invariant, but world placement, projected facing, Y alignment and body clearance are not accepted from these scenes.',
 'Source grape uses 35 generated quads; source ice-grape uses 43 over its frame union. Native cards retain two broad faces. The source extrusion proof is for 1.20.1 only; this candidate fixes size, not alpha-edge geometry.',
 'Front render_sides and inherited editor shading are preview hints, not Java no-cull or Bedrock material/controller/shader/culling execution. Ordinary ice active material/shader semantics remain unproven and unchanged.',
 'Raw decoded tilted-card bounds exceed the declared visibility box before and after the size correction. This existing reference-frame advisory is not a proven engine disappearance and does not authorize expanding bounds, shifting geometry or guessing an external engine transform.',
 'No Minecraft, BDS, LIVE, deployment, game renderer, native animation, helper lifecycle, reload or reconnect test was run. These are bounded prepared built-in representatives, not acceptance of arbitrary addon models or complete addon parity.',
 'Accepted held shakers, tilted rack and its existing +6 first-person Y lift remain untouched. This is not new held-view acceptance.']
report={'scope':'Actual cloud Blockbench GUI review of the isolated pressing ingredient-card size candidate','gui_completed':True,'runtime_applied':False,'candidate_sha256':sha(p/'candidate/runtime/RP/models/entity/runtime_pressing_card.geo.json'),'canonical_preparation':json.loads((p/'manifest.json').read_text())['canonical'],'scene_count':6,'accepted_original_screenshots':len(captures),'excluded_original_diagnostics':2,'numeric_camera_original_screenshots':1,'decision':'Bounded GUI acceptance of the source-backed centered size correction. No additional runtime defect or broader parity acceptance established.','key_finding':'SOURCE and AFTER broad-face size agree in the decisive common Top view; BEFORE remains half the linear size. The same candidate enlargement is visible in helper/layer, north/east tilt and frozen ice-grape representatives, while unrelated controls remain unchanged.','captures':captures,'numeric_camera_evidence':[dict(fileinfo('camera-proof/01-upright-top-camera.jpg'),related_capture='screenshots/01-upright-top.jpg',camera_position_displayed=[0.12,513.6,-1.24],focal_point_displayed=[0.12,1.6,-1.24],zoom_displayed=0.3403,projection='Orthographic, visibly checked in context menu. Save Angle projection Unset is its save option, not current projection.',method='Read Save Angle dialog then Cancel. No values edited and no preset created.',precision='UI displayed values, not exact internal floating-point camera values.')], 'diagnostics':[], 'scope_limits':limits,'prep_integrity':{'original_artifacts_checked':pre['checked'],'all_original_artifact_hashes_unchanged':True,'original_manifest_sha256_unchanged':True,'scene_hashes_unchanged':{s['scene']:s['sha256'] for s in scenes}},'data_evidence_references':{'manifest':'../manifest.json','independent_audit':'../independent-audit.json','exact_changes':'../changed-field-proposal.json','pose_bounds_advisory':'../pose-bounds-audit.json','baseline_gui':'../../tavern-machine-content-review-20261109/gui-review/review-report.json'},'temporary_editor_changes':'Only mesh selection, centering and camera presets/zoom in owned review tabs. No visibility changes, geometry/UV/texture edits or shared settings changes. All six tabs closed without any save or discard modal. No temporary camera presets were created.','gui_final_state':'Only healthy Champagne remains in Blockbench window 29360132, no modal. Terminal 41949001 and other terminal windows preserved. GUI explicitly handed to parent before writing this report.','completion_summary_sent':True}
for name,scene in [('04-north-initial-edge-on.jpg','03-north-tilt-layers.bbmodel'),('05-east-initial-edge-on.jpg','04-east-tilt-layers.bbmodel')]:
 c=fileinfo('excluded-diagnostics/'+name); c.update({'scene':'scenes/'+scene,'status':'excluded diagnostic, not accepted observation','reason':'Inherited perspective made one or more corresponding cards near edge-on, preventing a useful complete paired surface comparison. Replaced with readable orthographic view. Not a renderer or native culling defect.'}); report['diagnostics'].append(c)
write('review-index.json',report)
write('final-integrity.json',{'checked_original_artifacts':pre['checked'],'errors':errors,'original_manifest_sha256':sha(p/'artifact-sha256.json'),'candidate_sha256':report['candidate_sha256'],'scene_sha256':report['prep_integrity']['scene_hashes_unchanged'],'all_originals_unchanged':True,'all_screenshots_original_bytes':True})
(out/'README.md').write_text('''# Pressing-card size candidate: completed Blockbench GUI review

**Bounded visual acceptance of the source-backed size correction. No runtime application or publication.**

Six self-contained scenes were inspected in the existing cloud Blockbench. The evidence contains **seven accepted original JPEGs**, **two excluded edge-on diagnostics**, and **one original numeric-camera screenshot**. Every image is 1188×848. Original screenshot bytes were written and inspected without cropping, resizing, repainting, re-encoding or stitching.

## Finding

`01-upright-top.jpg` is the decisive common orthographic comparison: SOURCE and AFTER have matching broad-face scale; BEFORE is half the linear size. The audited dimensions are **8×8×0.5**, **4×4×0.25**, **8×8×0.5**. The candidate changes eight cubes about the same zero centers, without adding animation scale.

The helper-boundary/layer, north/east tilted and frozen ice-grape tick-1 representatives retain the enlargement without a new visible native pose change. The barrel-card and pressing-stone controls remain unchanged. This supports the isolated size repair, not broader engine or addon acceptance.

Candidate SHA-256: `d93249923210a8711fa038105816380407b9d70811c23313d4ddb56d68b83eea`.

## Capture index

1. `screenshots/01-upright-top.jpg`: isolated global 0, common Top orthographic. SOURCE left, BEFORE middle, AFTER right. Camera proof records displayed position [0.12, 513.6, −1.24], focal point [0.12, 1.6, −1.24], zoom 0.3403.
2. `screenshots/02-upright-oblique.jpg`: True Isometric Left 30°, source upper-right and after lower-left. Supplementary shallow edge context; the original generated edge representation remains different.
3. `screenshots/03-helper-boundaries-oblique.jpg`: globals 0/7/8/63, including helper 0→1 and helper 7/local 7. High versus low layers are visible. The close 0/8 pair partially overlaps, so precise helper identity and unchanged transforms rely on the separately audited scene data.
4. `screenshots/04-north-tilt-south.jpg`: globals 0/63 at facing 0. South orthographic makes both face pairs readable. Source/native vertical separation is a reference-frame difference, not a clearance verdict.
5. `screenshots/05-east-tilt-top.jpg`: globals 0/63 at facing 1. Top exposes faces that were edge-on in initial perspective. No body is attached.
6. `screenshots/06-ice-grape-tick1-top.jpg`: complete frozen tick-1 source/before/after sprites. Texture pixels remain the designated exact frozen pixels; no clock is run.
7. `screenshots/07-unchanged-barrel-stone-controls.jpg`: unchanged 8×8×0.5 barrel cards and 4×4×4 pressing stone. The source/native barrel poses retain their original frame difference. Stone uses the explicit neutral official Java texture.

`review-index.json` supplies exact image hashes, dimensions, scene hashes, camera operations, named groups, captions and per-capture limits. `scene-identity-index.json` records all 36 mesh identities, bounds and original audit metadata. Source/BEFORE/AFTER columns are world X −24/0/+24; the control rows additionally use +40 Y for barrel and +44 Z for stone. Camera angle can reverse screen ordering. No image was relabelled by screen-left alone.

## Limits that travel with the evidence

- The source generated grape has 35 quads and ice-grape 43 over the frame union; native cards retain two broad faces. Size is fixed, alpha-edge extrusion is not. The original extrusion proof is 1.20.1 only. The oblique screenshot does not count every edge quad.
- All images are Front-sided Free-format previews with inherited editor shading. They do not execute native materials, shaders, animation/controllers, helper lifecycle or game culling. Ordinary ice material semantics remain unproven.
- Source Java-world and raw decoded native model-reference frames differ. Only size is basis-invariant. No body clearance, world-facing or vertical alignment conclusion is accepted.
- The raw decoded tilted AABB exceeds declared visibility bounds both before and after. Keep the documented engine-frame/culling advisory; do not infer a runtime disappearance or enlarge bounds/shift geometry from it.
- Held shakers, tilted rack and its accepted +6 first-person Y lift are untouched. No game client, BDS, LIVE, deployment, plugin, renderer/security change, publication or complete addon-parity acceptance occurred.

## Integrity and handoff

All **280 original preparation artifacts** and the original manifest itself remain byte-identical. All six original scenes and the candidate hash are unchanged. No original preparation status flags were rewritten; this folder is the completed GUI supplement.

Only temporary selection and camera/zoom were used. All groups stayed visible. Every selection was cleared with Edit → Unselect All. No preset was created, no file was saved/exported, and no discard dialog appeared. All six owned review tabs were closed. The unchanged Champagne tab remains visibly healthy in window 29360132, with no modal. Terminal 41949001 and other windows were preserved. The GUI was explicitly handed back to the parent.

`final-integrity.json` records the postflight result. `artifact-sha256.json` hashes every file in this GUI supplement except itself.
''')
write('artifact-sha256.json',{str(f.relative_to(out)):sha(f) for f in sorted(out.rglob('*')) if f.is_file() and f.name!='artifact-sha256.json'})
print(json.dumps({'accepted':len(captures),'diagnostics':2,'camera_proof':1,'original_artifacts_unchanged':pre['checked'],'candidate_sha256':report['candidate_sha256'],'all_image_dimensions':sorted({tuple(c['dimensions']) for c in captures})},indent=2))

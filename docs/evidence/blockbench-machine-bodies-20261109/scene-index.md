# Machine-body scene and capture index

Source is **negative world X**, current is **positive world X**. Screen-left/right changes with the camera. All 19 accepted and 5 excluded images are the original 1188×848 JPEG bytes. Numeric camera coordinates were not queried; recorded preset/action descriptions are retained.

Scenes are exact original members of the linked ZIPs, opened only after extraction. The archive member and SHA-256 identify each scene.

## barrel-closed.bbmodel

[Download containing ZIP](archives/original-inputs-01.zip) · member `review/scenes/barrel-closed.bbmodel` · SHA-256 `60569e4a61ef12a5e96aee1050bb212a30bc913687a32b5a925653a4d77c4b48`

- barrel-closed: source [-32, 0, 0]; current [32, 0, 0] (model pixels).

### [Accepted: 01-barrel-closed-perspective](images/screenshots/01-barrel-closed-perspective.jpg)

Camera: Initial perspective, centered all elements; zoom out net 1520 pixels. Not queried; preset name and visible interaction sequence retained.
Observation: Paired closed fronts, lid bands, body edges and feet show matching shapes and texture placement.
SHA-256: `7fa9aa37f8fc91499ca94336e796e941d07c6a7f5837959af045e40030688006`

### [Accepted: 02-barrel-closed-top](images/screenshots/02-barrel-closed-top.jpg)

Camera: Top orthographic preset; zoom out 1200 pixels. Not queried; preset name and visible interaction sequence retained.
Observation: Both lid surfaces show matching plank, band and fastener UV placement.
SHA-256: `86a88469d24fdbf3329215039242ed167d05d004139f23e95a19df18258764be`

### [Accepted: 03-barrel-closed-bottom](images/screenshots/03-barrel-closed-bottom.jpg)

Camera: Bottom orthographic preset. Not queried; preset name and visible interaction sequence retained.
Observation: Paired base planks, metal bands and foot ends match in the visible projection.
SHA-256: `32cb2f75f6d270735c4d2433130902929c0f9afdd3de7d5ff8d66a5bb7f32ec9`

## barrel-open.bbmodel

[Download containing ZIP](archives/original-inputs-01.zip) · member `review/scenes/barrel-open.bbmodel` · SHA-256 `512826dd34104dcc894a86c52dc1f7fe645835734e4983daadbd766c8323655d`

- barrel-open: source [-32, 0, 0]; current [32, 0, 0] (model pixels).

### [Accepted: 04-barrel-open-perspective](images/screenshots/04-barrel-open-perspective.jpg)

Camera: Initial perspective; centered all elements; zoom out 1520 pixels. Not queried; preset name and visible interaction sequence retained.
Observation: Raised lid, zero-width strut silhouette, body opening, shell and feet agree in the visible oblique projection.
SHA-256: `c2a7464a58add9eea60edc4a5b4691e8fd899512eda62b338d2eaea7cb61c788`

### [Accepted: 05-barrel-open-top](images/screenshots/05-barrel-open-top.jpg)

Camera: Top orthographic preset; zoom out 1200 pixels. Not queried; preset name and visible interaction sequence retained.
Observation: Matching open cavity extent, lid projection and surrounding band/plank UV placement. Dark cavity is only this Front-sided preview.
SHA-256: `e21086001146ece0a17b24cd45d259bdc1542ae5fd7753364b35b01289e36ae9`

### [Accepted: 06-barrel-open-north](images/screenshots/06-barrel-open-north.jpg)

Camera: North orthographic preset; centered all elements. Not queried; preset name and visible interaction sequence retained.
Observation: Paired raised lid and front body/feet align. This is the editor North preset, not native world-facing validation.
SHA-256: `760e37c5f872f091000d8db1718266e81cc53a0e4bec9a58e80b768bd07e913e`

### [Accepted: 07-barrel-open-south](images/screenshots/07-barrel-open-south.jpg)

Camera: South orthographic preset; centered all elements. Not queried; preset name and visible interaction sequence retained.
Observation: Opposite barrel shell and lid projection match.
SHA-256: `52fe33a9860ae5164c75e49053f43cbcb5e98703c47e630aa37ea8625ebe129a`

## pressing-tubs.bbmodel

[Download containing ZIP](archives/original-inputs-01.zip) · member `review/scenes/pressing-tubs.bbmodel` · SHA-256 `11bd907fc372f8d197f547dfadacc4ba21d659a769c46b3656959c59e678c072`

- pressing_tub-upright: source [-15, 0, 0]; current [15, 0, 0] (model pixels).
- pressing_tub-tilt: source [-15, 0, 32]; current [15, 0, 32] (model pixels).

### [Accepted: 08-pressing-tubs-perspective](images/screenshots/08-pressing-tubs-perspective.jpg)

Camera: Initial perspective; centered all elements; zoom out 600 pixels. Not queried; preset name and visible interaction sequence retained.
Observation: Both upright and tilted source/current pairs show matching rim thickness, cavity, band and tilt geometry.
SHA-256: `1ccc7309e2291e1d54fd153fb03444af4074fb2d6fa0772b340a203051461daf`

### [Accepted: 09-pressing-tubs-top](images/screenshots/09-pressing-tubs-top.jpg)

Camera: Top orthographic preset; centered all elements; zoom out total 700 pixels. Not queried; preset name and visible interaction sequence retained.
Observation: Upright at Z0 and tilted at Z32 show matching top projections and UVs.
SHA-256: `68a3b06985b06f0fbb478a51569b1381fa3ea0b60b5e0aa822e74f6ad7b829bc`

### [Accepted: 10-pressing-tubs-bottom](images/screenshots/10-pressing-tubs-bottom.jpg)

Camera: Bottom orthographic preset; centered all elements. Not queried; preset name and visible interaction sequence retained.
Observation: Upright and tilted bases show matching plank and band UV layout.
SHA-256: `818ef066babb029b1ee6d3c889fb94c590310d192fdf7f34d5ec75e90fc5b1b8`

## taps.bbmodel

[Download containing ZIP](archives/original-inputs-01.zip) · member `review/scenes/taps.bbmodel` · SHA-256 `50671fdeb7ff874b92e34c68b2842854a4e5fe719dd8a99907c23028b30198ac`

- tap-closed: source [-15, 0, 0]; current [15, 0, 0] (model pixels).
- tap-open: source [-15, 0, 32]; current [15, 0, 32] (model pixels).

### [Accepted: 11-taps-perspective](images/screenshots/11-taps-perspective.jpg)

Camera: Initial perspective; centered all elements; zoom out 300 pixels. Not queried; preset name and visible interaction sequence retained.
Observation: Open and closed handle states, spout and mount block are represented in paired geometry with no visible discrepancy.
SHA-256: `af2338dd6377ad4578b6d0b683abc7b03d7c2a5c3152f00c2e067c1e1d26f0dd`

### [Accepted: 12-taps-top](images/screenshots/12-taps-top.jpg)

Camera: Top orthographic preset; centered all elements; zoom out 500 pixels. Not queried; preset name and visible interaction sequence retained.
Observation: Closed at Z0 and open at Z32 show equal paired handle orientation and surface texture.
SHA-256: `a7586b7f84f56978071e10087d86e18b4c8c5b43a2ea467a907342ed0670df7b`

### [Accepted: 13-taps-true-isometric-left](images/screenshots/13-taps-true-isometric-left.jpg)

Camera: True Isometric Left (30 degrees) preset; centered all elements; zoom out 400 pixels. Not queried; preset name and visible interaction sequence retained.
Observation: Opposite oblique side shows matched handle, rear mount and spout edge geometry.
SHA-256: `69c1ae30535d49c66281c159a0fdf6fe0677617445644b5ce4da834f4a617638`

## stepladder-placed-assembly.bbmodel

[Download containing ZIP](archives/original-inputs-01.zip) · member `review/scenes/stepladder-placed-assembly.bbmodel` · SHA-256 `e8bdb81fd731efa184fb4ad586c85088031d8cf5b4df8433df80e992173ce884`

- stepladder-placed-assembly: source [-20, 0, 0]; current [20, 0, 0] (model pixels).

### [Accepted: 14-stepladder-perspective](images/screenshots/14-stepladder-perspective.jpg)

Camera: Initial perspective; centered all elements; zoom out 800 pixels. Not queried; preset name and visible interaction sequence retained.
Observation: Actual bottom and Y+16 top blocks form matching paired ladder silhouettes; sloping side rails and joining band remain continuous in this oblique view.
SHA-256: `039ed472e6011e687060184d3c0b0a740dd6d2c10fbd8de66ac6bdad0f0a6c12`

### [Accepted: 15-stepladder-north-join](images/screenshots/15-stepladder-north-join.jpg)

Camera: North orthographic preset; centered all elements; zoom out 300 pixels. Not queried; preset name and visible interaction sequence retained.
Observation: Step heights, rail edges and two-block join region align with matching texture bands.
SHA-256: `0f6c814bcdccdabdaa1c0f7dc83f06f3d557cdb7d65270f4fa2ec3b86be10a40`

### [Accepted: 16-stepladder-bottom](images/screenshots/16-stepladder-bottom.jpg)

Camera: Bottom orthographic preset; centered all elements. Not queried; preset name and visible interaction sequence retained.
Observation: Tread undersides, rear/front leg projections and base plank UVs match.
SHA-256: `acb831098b4049bce01bfe964ea5cd872303838834e573e318d02a6c104b0b4e`

## shaker-placed-put-keyframes.bbmodel

[Download containing ZIP](archives/original-inputs-01.zip) · member `review/scenes/shaker-placed-put-keyframes.bbmodel` · SHA-256 `ab4cc958331714026f72404624ef6ce65d58df51fafd8c3036130e29b1f9df15`

- shaker-put-0: source [-12, 0, 0]; current [12, 0, 0] (model pixels).
- shaker-put-0.0833: source [-12, 0, 26]; current [12, 0, 26] (model pixels).
- shaker-put-0.2083: source [-12, 0, 52]; current [12, 0, 52] (model pixels).

### [Accepted: 18-shaker-put-perspective](images/screenshots/18-shaker-put-perspective.jpg)

Camera: Initial perspective; centered all elements; zoom out 600 pixels. Not queried; preset name and visible interaction sequence retained.
Observation: Frozen idle, 0.0833 and 0.2083 second bodies and lid lifts are visible. Some perspective overlap is resolved by top and opposite oblique captures.
SHA-256: `591eb7f537b36a26fd8c55db5f53d28a5dfde4f17a8a26b8ff165881dd0e921e`

### [Accepted: 19-shaker-put-top](images/screenshots/19-shaker-put-top.jpg)

Camera: Top orthographic preset; centered all elements; zoom out 1000 pixels. Not queried; preset name and visible interaction sequence retained.
Observation: All three paired root-yaw/lid projections match, including the rotated 0.0833 second sample.
SHA-256: `271b4fa34bc4c85681167c92f27d5a1e74d5ac17fe20de8b9df8d154951ff2e5`

### [Accepted: 20-shaker-put-true-isometric-left](images/screenshots/20-shaker-put-true-isometric-left.jpg)

Camera: True Isometric Left (30 degrees) preset; centered all elements; zoom out 900 pixels. Not queried; preset name and visible interaction sequence retained.
Observation: Six separated visible shakers show matching lid lift and pitch at each frozen sample. No interpolation or running animation is tested.
SHA-256: `031f544e203da1b69f5db5ad0b77e8f84b9cfacf013b1cdb63220e9cf128ab99`

## Excluded framing diagnostics

These five clipped captures add no acceptance and are not asset defects. No precise camera transform beyond the original filename is claimed.

- [Excluded: 02-barrel-closed-top-clipped](images/diagnostic/02-barrel-closed-top-clipped.jpg): Framing clipped part of model at viewport boundary; preserved only as diagnostic. Not an asset defect or accepted capture. SHA-256 `9b9e1fedcdb89823d8db042efc0f0adb4fb0a98a4b0956eb281a4cb9f2594846`.
- [Excluded: 06-barrel-open-north-clipped](images/diagnostic/06-barrel-open-north-clipped.jpg): Framing clipped part of model at viewport boundary; preserved only as diagnostic. Not an asset defect or accepted capture. SHA-256 `2d07a753cb4432772d7b31be68799d0d0e46c2dacab29dc8b5322ad87f2e430e`.
- [Excluded: 09-pressing-tubs-top-clipped](images/diagnostic/09-pressing-tubs-top-clipped.jpg): Framing clipped part of model at viewport boundary; preserved only as diagnostic. Not an asset defect or accepted capture. SHA-256 `aa1a342ce0b46d801c3da25f02d8fb6ded3d531cdfff2aef8d885d36937f50cd`.
- [Excluded: 13-taps-true-isometric-left-clipped](images/diagnostic/13-taps-true-isometric-left-clipped.jpg): Framing clipped part of model at viewport boundary; preserved only as diagnostic. Not an asset defect or accepted capture. SHA-256 `258640f00ab63d6179d1c9f12c5afda41ad52203fb643ed95c8b5036148be084`.
- [Excluded: 17-stepladder-true-isometric-left-clipped](images/diagnostic/17-stepladder-true-isometric-left-clipped.jpg): Framing clipped part of model at viewport boundary; preserved only as diagnostic. Not an asset defect or accepted capture. SHA-256 `946ce5b80eedc13257d6aa7b8e9f75db4f945e5cc9c09b7fd8a263295638fcc2`.

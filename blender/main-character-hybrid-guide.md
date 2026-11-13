# Main character: hybrid texture workflow (O3)

## Goal

Make the chibi doctor look more like `blender/references/chibi-doctor-character-sheet.png`.
Keep the current rig, bone names, and the `idle` and `walk` clips, so the game code does not change.

## Starting point

- Source script: `blender/build_main_character.py`.
- Output: `client/public/game-assets/3d/doctor.glb`.
- Bones: `hips`, `torso`, `head`, `arm.L`, `arm.R`, `leg.L`, `shin.L`, `leg.R`, `shin.R`.
- Clips: `idle`, `walk`.

## Tools

| Code | Tool | Use |
| --- | --- | --- |
| T1 | Higgsfield `generate_3d` or Magnific `models3d_generate` | Make a textured reference model from the sheet. |
| T2 | Magnific `models3d_retexture` | Change textures on a model with a text or image prompt. |
| T3 | Magnific `images_pbr_maps` | Make normal and roughness maps for fabric. |
| T4 | Blender Texture Paint and Bake | Project and bake textures onto the rigged mesh. |
| T5 | Blender MCP `look` | Compare views against the sheet. |

T1, T2, and T3 cost credits.
T4 and T5 are free.

## Procedure

### Step 1: Prepare the reference images

1. Crop the front view from the character sheet.
2. Remove the background (Magnific `images_remove_background`).
3. Crop the face, the hair from the back view, and the sneakers as separate images.

### Step 2: Make the reference model

1. Send the front view to T1.
2. Import the GLB into Blender as `refModel`.
3. Scale `refModel` to the height of `doctorBody` (about 5 units) and put it on the ground.
4. Do not rig or export `refModel`.
   Use it only as a shape and texture source.

### Step 3: Improve the shapes

1. Compare the head and hair of `doctorBody` with `refModel` from the front, side, and back.
2. Change the hair blobs in `build_main_character.py` to match the silhouette.
3. Do not change the bone names or the bone positions.

### Step 4: UV unwrap the rigged mesh

1. Select `doctorBody`.
2. Run Smart UV Project.
3. Make one image of 1024 x 1024 px for the color.

### Step 5: Bake the color from the reference model

1. Set the render engine to Cycles.
2. Select `refModel`, then `doctorBody` (active).
3. Bake type: Diffuse, color only, "Selected to Active", cage extrusion about 0.05.
4. Save the image as `client/public/game-assets/3d/textures/doctor-color.png`.

### Step 6: Paint the face details

1. Use Texture Paint with the face crop in "Project from View".
2. Paint the eyes, eyebrows, mouth, and blush.
3. Make sure that the eyes stay sharp.
   If the bake is soft, keep the eye meshes from the script.

### Step 7: Add fabric detail

1. Make normal and roughness maps for the scrubs, coat, and sneakers with T3.
2. Connect them to the materials with Normal Map nodes.
3. Keep each map at 1024 px or smaller.

### Step 8: Optional retexture

1. If the baked color does not look like the sheet, send `refModel` to T2 with the sheet as the image prompt.
2. Do Step 5 again.

### Step 9: Export

1. Embed the textures in the GLB.
2. Export with animations to `client/public/game-assets/3d/doctor.glb`.
3. Make sure that the file is less than 3 MB.

## Verification

1. Open the GLB and make sure that it has 9 joints and the `idle` and `walk` clips.
2. Run the game and open the hub.
3. Make sure that the doctor faces the direction of travel.
4. Make sure that the walk cycle plays and no part comes off the body.
5. Compare a screenshot from the front with the character sheet.

## Rollback

Run `git checkout -- client/public/game-assets/3d/doctor.glb` to restore the last committed doctor.

## Risks

| Code | Risk | Control |
| --- | --- | --- |
| R1 | The reference model has a different shape, so the bake has gaps. | Increase the cage extrusion, or paint the gaps by hand. |
| R2 | Large textures make the game slow to load. | Use 1024 px maps and one atlas. |
| R3 | Rerunning `build_hospital_assets.py` overwrites the new doctor. | Remove its doctor build call. |

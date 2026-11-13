// LevelBuilder.ts — builds one long hospital-corridor level from DAS patient data.
// Style: mission-control navy/teal corridor with amber door lights and cyan monitors.
// Safety: continuous walkable floor across the entire corridor length.

import { Scene } from "@babylonjs/core/scene";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import "@babylonjs/loaders/glTF";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import type { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import type { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import type { CharacterLibrary } from "./hubCharacters";
import type { Level, Patient } from "@/lib/patients";
import { ASSETS } from "./assets";
import type { Rect } from "./Player";

export interface BuiltBed {
  patient: Patient;
  x: number;
  root: import("@babylonjs/core/Meshes/transformNode").TransformNode;
  assessed: boolean;
}

const UNIT = 12; // world units per patient room
const FLOOR_Y = -1.2;
const BG_TILE_WIDTH = 60;
// Frame lower ward section: full beds, wheels, and walkable platform stay visible.
const BED_X_IN_TILE = [7.4, 18.4, 29.15, 40.05, 51.1] as const;

export class LevelBuilder {
  private disposables: { dispose: () => void }[] = [];
  readonly beds: BuiltBed[] = [];
  readonly floors: Rect[];
  readonly width: number;
  readonly floorY = FLOOR_Y;

  private useTextures: boolean;
  private disposed = false;
  constructor(
    private scene: Scene,
    level: Level,
    opts: { tintHue?: number; useTextures?: boolean; library?: CharacterLibrary; shadows?: ShadowGenerator } = {},
  ) {
    this.useTextures = opts.useTextures ?? true;
    this.width = level.patients.length * UNIT + 14;

    // --- Blender ward bays, tiled along +X ---
    void this.loadWard(opts.tintHue, opts.shadows);

    // Solid continuous walkable hospital floor across the entire corridor length
    this.floors = [{ x: 0, y: FLOOR_Y, w: this.width, h: 4 }];

    // --- Doors + beds ---
    for (let i = 0; i < level.patients.length; i++) {
      const p = level.patients[i];
      const tile = Math.floor(i / BED_X_IN_TILE.length);
      const x = tile * BG_TILE_WIDTH + BED_X_IN_TILE[i % BED_X_IN_TILE.length];
      this.beds.push(this.placeBed(p, x, i));
    }

    // --- Lying patient in each case bed ---
    if (opts.library) {
      this.beds.forEach((bed, i) => {
        const root = new TransformNode(`bedPatient${i}`, scene);
        root.position.set(bed.x, FLOOR_Y + 1.45, 7.1);
        root.rotation.set(-Math.PI / 2, Math.PI, 0);
        root.scaling.setAll(0.85);
        this.disposables.push(root);
        opts.library!.spawn("patient", root, opts.shadows)
          .then((animator) => {
            if (!animator) return;
            if (this.disposed) return animator.dispose();
            animator.play("idle", 0.5 + (i % 3) * 0.1);
            this.disposables.push(animator);
          })
          .catch((error) => console.error("[LevelBuilder] patient load failed", error));
      });
    }
  }

  private async loadWard(tintHue: number | undefined, shadows?: ShadowGenerator) {
    try {
      const container = await LoadAssetContainerAsync(ASSETS.models.wardBay, this.scene);
      if (this.disposed) return container.dispose();
      this.disposables.push(container);
      const bays = Math.ceil(this.width / BG_TILE_WIDTH);
      // One extra bay at each end so the camera never sees past the ward.
      for (let b = -1; b <= bays; b++) {
        const entries = container.instantiateModelsToScene((name) => `ward${b}_${name}`, false);
        entries.rootNodes.forEach((node) => {
          (node as TransformNode).position.set(b * BG_TILE_WIDTH, FLOOR_Y, 0);
          node.getChildMeshes().forEach((mesh) => {
            mesh.receiveShadows = true;
            shadows?.addShadowCaster(mesh);
          });
        });
        this.disposables.push(entries);
      }
      // Per-level wall tint keeps levels distinct.
      const hue = tintHue ?? 200;
      this.scene.materials
        .filter((m) => m.name.endsWith("wardWallTint"))
        .forEach((m) => ((m as PBRMaterial).albedoColor = Color3.FromHSV(hue, 0.16, 0.9).toLinearSpace()));
    } catch (error) {
      console.error("[LevelBuilder] ward load failed", error);
    }
  }

  private placeDoor(_x: number, _flip: boolean) {
    // Doors are rendered naturally as part of the hospital-ward-v1 background artwork
  }

  private placeBed(patient: Patient, x: number, index: number): BuiltBed {
    const root = new TransformNode(`bed${index}`, this.scene);
    root.position.set(x, FLOOR_Y, 10);

    // Patients are baked into background, eliminating floating overlay seams.
    // Root remains exact interaction/question anchor for this visible bed.
    this.disposables.push(root);
    return { patient, x, root, assessed: false };
  }

  dispose() {
    this.disposed = true;
    for (const d of this.disposables) d.dispose();
  }
}

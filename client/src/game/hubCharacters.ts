// hubCharacters.ts — Blender-built GLB characters (doctor, nurse, patient) for the 3D hub.

import "@babylonjs/loaders/glTF";
import type { Scene } from "@babylonjs/core/scene";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import type { AssetContainer } from "@babylonjs/core/assetContainer";
import type { AnimationGroup } from "@babylonjs/core/Animations/animationGroup";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import { ASSETS } from "./assets";

// Staff wear coats or scrubs; patients wear gowns.
export type StaffKind = "drLara" | "drRamon" | "nurseMaria" | "nurseJames";
export type PatientKind = "patientA" | "patientB" | "patientC";
export type CharacterKind = "doctor" | "nurse" | "patient" | StaffKind | PatientKind;

const MODEL_URLS: Record<CharacterKind, string> = {
  doctor: ASSETS.models.doctor,
  nurse: ASSETS.models.nurse,
  patient: ASSETS.models.patient,
  drLara: ASSETS.models.drLara,
  drRamon: ASSETS.models.drRamon,
  nurseMaria: ASSETS.models.nurseMaria,
  nurseJames: ASSETS.models.nurseJames,
  patientA: ASSETS.models.patientA,
  patientB: ASSETS.models.patientB,
  patientC: ASSETS.models.patientC,
};

// One container per model; NPCs are instantiated from it.
export class CharacterLibrary {
  private containers = new Map<CharacterKind, Promise<AssetContainer>>();

  constructor(private scene: Scene) {}

  load(kind: CharacterKind) {
    let container = this.containers.get(kind);
    if (!container) {
      container = LoadAssetContainerAsync(MODEL_URLS[kind], this.scene).then((c) => {
        // UV islands touch edge to edge, so mip levels blend them into visible seams.
        c.textures.forEach((t) => (t as Texture).updateSamplingMode?.(Texture.BILINEAR_SAMPLINGMODE));
        return c;
      });
      this.containers.set(kind, container);
    }
    return container;
  }

  async spawn(kind: CharacterKind, root: TransformNode, shadows?: ShadowGenerator) {
    const container = await this.load(kind);
    if (root.isDisposed()) return null;
    const entries = container.instantiateModelsToScene((name) => `${root.name}_${name}`, false);
    entries.rootNodes.forEach((node) => {
      node.parent = root;
      node.getChildMeshes().forEach((mesh) => {
        mesh.receiveShadows = true;
        shadows?.addShadowCaster(mesh);
      });
    });
    return new CharacterAnimator(entries.animationGroups, () => entries.dispose());
  }

  dispose() {
    this.containers.forEach((container) => container.then((c) => c.dispose()).catch(() => undefined));
  }
}

export class CharacterAnimator {
  private current: AnimationGroup | null = null;

  constructor(private groups: AnimationGroup[], private disposeModel: () => void) {
    groups.forEach((group) => group.stop());
  }

  play(clip: "idle" | "walk", speed = 1) {
    const group = this.groups.find((g) => g.name.endsWith(clip)) ?? null;
    if (group && group !== this.current) {
      this.current?.stop();
      group.start(true, speed);
      this.current = group;
    }
    if (group) group.speedRatio = speed;
  }

  dispose() {
    this.groups.forEach((group) => group.dispose());
    this.disposeModel();
  }
}

// Player-controlled doctor: turns toward travel direction and swaps idle/walk clips.
export class HubDoctor3D {
  readonly root: TransformNode;
  private animator: CharacterAnimator | null = null;
  private heading = 0;
  private disposed = false;

  constructor(scene: Scene, start: Vector3, library: CharacterLibrary, shadows?: ShadowGenerator) {
    this.root = new TransformNode("hubDoctorRoot", scene);
    this.root.position.copyFrom(start);
    library.spawn("doctor", this.root, shadows)
      .then((animator) => {
        if (this.disposed) animator?.dispose();
        else this.animator = animator;
      })
      .catch((error) => console.error("[HubDoctor3D] model load failed", error));
  }

  update(dt: number, moving: boolean, x: number, z: number) {
    if (moving) {
      const target = Math.atan2(x, z);
      let delta = target - this.heading;
      delta = Math.atan2(Math.sin(delta), Math.cos(delta));
      this.heading += delta * Math.min(1, dt * 12);
      this.root.rotation.y = this.heading;
    }
    this.animator?.play(moving ? "walk" : "idle", moving ? 1.25 : 1);
  }

  dispose() {
    this.disposed = true;
    this.animator?.dispose();
    this.root.dispose(false, true);
  }
}

type NpcSpec =
  | { kind: StaffKind; position: Vector3; heading: number; patrol?: { from: Vector3; to: Vector3; speed: number } }
  | { kind: PatientKind; position: Vector3; heading: number; pose?: "lying" };

const NPCS: NpcSpec[] = [
  { kind: "drRamon", position: new Vector3(0, 0, 72.4), heading: Math.PI },
  { kind: "nurseMaria", position: new Vector3(-4, 0, 18), heading: 0, patrol: { from: new Vector3(-4, 0, 16), to: new Vector3(-4, 0, 56), speed: 2.2 } },
  { kind: "nurseJames", position: new Vector3(4, 0, 54), heading: Math.PI, patrol: { from: new Vector3(4, 0, 56), to: new Vector3(4, 0, 16), speed: 2 } },
  { kind: "drLara", position: new Vector3(-5.8, 0, 31.9), heading: -Math.PI / 2 },
  { kind: "patientA", position: new Vector3(7.1, 0, 10.2), heading: -Math.PI / 2 },
  { kind: "patientB", position: new Vector3(-7.1, 0, 37.8), heading: Math.PI / 2 },
  { kind: "patientC", position: new Vector3(8.3, 1.45, 5.5), heading: 0, pose: "lying" },
  { kind: "patientB", position: new Vector3(-8.3, 1.45, 31.9), heading: 0, pose: "lying" },
];

// Ambient NPCs: a nurse at the station, a nurse on rounds, patients waiting or in gurneys.
export class HubNpcs {
  private roots: TransformNode[] = [];
  private animators: CharacterAnimator[] = [];
  private patrols: { root: TransformNode; spec: { from: Vector3; to: Vector3; speed: number }; dir: 1 | -1 }[] = [];
  private disposed = false;

  constructor(scene: Scene, library: CharacterLibrary, shadows?: ShadowGenerator) {
    NPCS.forEach((spec, index) => {
      const root = new TransformNode(`npc${index}`, scene);
      root.position.copyFrom(spec.position);
      root.rotation.y = spec.heading;
      const patrol = "patrol" in spec ? spec.patrol : undefined;
      if ("pose" in spec && spec.pose === "lying") {
        root.rotation.x = -Math.PI / 2;
        root.scaling.setAll(0.85);
      }
      this.roots.push(root);
      if (patrol) this.patrols.push({ root, spec: patrol, dir: 1 });
      library.spawn(spec.kind, root, shadows)
        .then((animator) => {
          if (!animator) return;
          if (this.disposed) return animator.dispose();
          animator.play(patrol ? "walk" : "idle", patrol ? 0.9 : 0.6 + (index % 3) * 0.15);
          this.animators.push(animator);
        })
        .catch((error) => console.error("[HubNpcs] model load failed", error));
    });
  }

  update(dt: number) {
    for (const patrol of this.patrols) {
      const target = patrol.dir === 1 ? patrol.spec.to : patrol.spec.from;
      const offset = target.subtract(patrol.root.position);
      const distance = offset.length();
      if (distance < 0.2) {
        patrol.dir = patrol.dir === 1 ? -1 : 1;
        continue;
      }
      const step = offset.scale(Math.min(1, (patrol.spec.speed * dt) / distance));
      patrol.root.position.addInPlace(step);
      patrol.root.rotation.y = Math.atan2(offset.x, offset.z);
    }
  }

  dispose() {
    this.disposed = true;
    this.animators.forEach((animator) => animator.dispose());
    this.roots.forEach((root) => root.dispose(false, true));
  }
}

// HospitalHub.ts — third-person 3D hospital corridor linking every clinical level.

import { Scene } from "@babylonjs/core/scene";
import { FreeCamera } from "@babylonjs/core/Cameras/freeCamera";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { DirectionalLight } from "@babylonjs/core/Lights/directionalLight";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { levels } from "@/lib/patients";
import { ASSETS } from "./assets";
import { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import "@babylonjs/core/Lights/Shadows/shadowGeneratorSceneComponent";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { CharacterLibrary, HubDoctor3D, HubNpcs } from "./hubCharacters";

export type HubMoveDirection = "forward" | "backward" | "left" | "right";

export interface HubTouchHandlers {
  onMove?: (direction: HubMoveDirection, pressed: boolean) => void;
}

export interface HubRoom {
  levelIndex: number;
  x: number;
  z: number;
  side: -1 | 1;
  name: string;
  tint: string;
}

interface HubInputState {
  forward: boolean;
  backward: boolean;
  left: boolean;
  right: boolean;
  interact: boolean;
}

const CORRIDOR_WIDTH = 20;
const CORRIDOR_LENGTH = 76;
const PLAYER_SPEED = 6.2;
const DOOR_TRIGGER_DISTANCE = 3.15;
const CAMERA_FOLLOW_RATE = 0.1;
const CAMERA_OFFSET = new Vector3(0, 7.2, -10.5);
const DOOR_LAYOUT = [
  { side: -1 as const, z: 12, tint: "#78a98e" },
  { side: 1 as const, z: 24, tint: "#77a9c9" },
  { side: -1 as const, z: 36, tint: "#d3a55f" },
  { side: 1 as const, z: 48, tint: "#a98ab8" },
  { side: -1 as const, z: 60, tint: "#6d9f8b" },
];

class HubInput {
  readonly state: HubInputState = {
    forward: false,
    backward: false,
    left: false,
    right: false,
    interact: false,
  };

  constructor() {
    window.addEventListener("keydown", this.onKeyDown);
    window.addEventListener("keyup", this.onKeyUp);
  }

  private onKeyDown = (event: KeyboardEvent) => {
    const key = event.code;
    if (key === "KeyW" || key === "ArrowUp") this.state.forward = true;
    if (key === "KeyS" || key === "ArrowDown") this.state.backward = true;
    if (key === "KeyA" || key === "ArrowLeft") this.state.left = true;
    if (key === "KeyD" || key === "ArrowRight") this.state.right = true;
    if (key === "KeyE" || key === "Enter") this.state.interact = true;
    if (key.startsWith("Arrow") || key === "Enter") event.preventDefault();
  };

  private onKeyUp = (event: KeyboardEvent) => {
    const key = event.code;
    if (key === "KeyW" || key === "ArrowUp") this.state.forward = false;
    if (key === "KeyS" || key === "ArrowDown") this.state.backward = false;
    if (key === "KeyA" || key === "ArrowLeft") this.state.left = false;
    if (key === "KeyD" || key === "ArrowRight") this.state.right = false;
  };

  setMove(direction: HubMoveDirection, pressed: boolean) {
    this.state[direction] = pressed;
  }

  endFrame() {
    this.state.interact = false;
  }

  dispose() {
    window.removeEventListener("keydown", this.onKeyDown);
    window.removeEventListener("keyup", this.onKeyUp);
  }
}

const SIGN_FONT = '"Pixelify Sans", monospace';

export class HospitalHub {
  private camera: FreeCamera;
  private doctor: HubDoctor3D;
  private npcs: HubNpcs;
  private library: CharacterLibrary;
  private shadows: ShadowGenerator;
  private input = new HubInput();
  private nearRoom: number | null = null;
  private entered = false;
  private disposed = false;
  private disposables: { dispose: () => void }[] = [];
  readonly rooms: HubRoom[];

  private onHubMove = (event: Event) => {
    const detail = (event as CustomEvent<{ dir: HubMoveDirection; pressed: boolean }>).detail;
    if (detail) this.input.setMove(detail.dir, detail.pressed);
  };

  constructor(
    private scene: Scene,
    private onDoorChange: (room: HubRoom | null) => void,
    private onEnterRoom: (levelIndex: number) => void,
    touchHandlers?: HubTouchHandlers,
    startRoomIndex?: number,
  ) {
    this.rooms = levels.map((level, levelIndex) => {
      const layout = DOOR_LAYOUT[levelIndex];
      return {
        levelIndex,
        x: layout.side * 7.55,
        z: layout.z,
        side: layout.side,
        name: level.name,
        tint: layout.tint,
      };
    });

    scene.clearColor = new Color4(0.72, 0.83, 0.82, 1);
    scene.ambientColor = new Color3(0.55, 0.6, 0.58);

    this.camera = new FreeCamera("thirdPersonCamera", new Vector3(0, 7.2, -8), scene);
    this.camera.fov = 0.82;
    this.camera.minZ = 0.1;
    scene.activeCamera = this.camera;

    const ambient = new HemisphericLight("hospitalAmbient", new Vector3(0, 1, 0), scene);
    ambient.intensity = 1.1;
    ambient.groundColor = new Color3(0.45, 0.42, 0.38);
    const daylight = new DirectionalLight("hospitalDaylight", new Vector3(-0.35, -1, 0.45), scene);
    daylight.position = new Vector3(20, 40, 20);
    daylight.intensity = 1.6;
    this.shadows = new ShadowGenerator(1024, daylight);
    this.shadows.useBlurExponentialShadowMap = true;
    this.shadows.blurKernel = 16;
    this.shadows.darkness = 0.45;
    this.library = new CharacterLibrary(scene);

    this.buildHospital();

    const returnRoom = startRoomIndex === undefined ? undefined : this.rooms[startRoomIndex];
    const start = returnRoom
      ? new Vector3(returnRoom.side * 5.2, 0, returnRoom.z - 0.6)
      : new Vector3(0, 0, 3.5);
    this.doctor = new HubDoctor3D(scene, start, this.library, this.shadows);
    this.npcs = new HubNpcs(scene, this.library, this.shadows);
    this.camera.position.copyFrom(start.add(CAMERA_OFFSET));
    this.camera.setTarget(start.add(new Vector3(0, 2.2, 4.5)));

    if (touchHandlers) touchHandlers.onMove = (direction, pressed) => this.input.setMove(direction, pressed);
    window.addEventListener("das-hub-move", this.onHubMove);

    scene.onBeforeRenderObservable.add(() => {
      const dt = Math.min(scene.getEngine().getDeltaTime() / 1000, 0.05);
      this.update(dt);
    });
  }

  private buildHospital() {
    const darkMaterial = this.material("doorShadow", "#254353");
    const trimMaterial = this.material("doorTrim", "#d9d0bc");
    // Corridor, props and furniture are authored in Blender (blender/build_hospital_assets.py).
    LoadAssetContainerAsync(ASSETS.models.world, this.scene)
      .then((container) => {
        if (this.disposed) return container.dispose();
        container.addAllToScene();
        container.meshes.forEach((mesh) => { mesh.receiveShadows = true; });
        this.disposables.push(container);
      })
      .catch((error) => console.error("[HospitalHub] world load failed", error));
    this.rooms.forEach((room) => this.buildRoom(room, darkMaterial, trimMaterial));
  }

  private buildRoom(room: HubRoom, darkMaterial: StandardMaterial, trimMaterial: StandardMaterial) {
    const wallX = room.side * 9.42;
    const roomColor = this.material(`roomColor${room.levelIndex}`, room.tint, true);
    this.box(`door${room.levelIndex}`, { width: 0.22, height: 5, depth: 4.25 }, new Vector3(wallX, 2.5, room.z), darkMaterial);
    this.box(`doorGlow${room.levelIndex}`, { width: 0.28, height: 4.35, depth: 3.55 }, new Vector3(room.side * 9.25, 2.35, room.z), roomColor);
    this.box(`doorTop${room.levelIndex}`, { width: 0.52, height: 0.34, depth: 4.75 }, new Vector3(room.side * 9.05, 5.3, room.z), trimMaterial);
    for (const offset of [-2.2, 2.2]) {
      this.box(`doorSide${room.levelIndex}-${offset}`, { width: 0.52, height: 5.35, depth: 0.32 }, new Vector3(room.side * 9.05, 2.675, room.z + offset), trimMaterial);
    }
    this.roomSign(room);
  }

  private roomSign(room: HubRoom) {
    const texture = new DynamicTexture(`roomSign${room.levelIndex}`, { width: 768, height: 180 }, this.scene, false);
    texture.hasAlpha = true;
    const paint = () => {
      const context = texture.getContext();
      context.fillStyle = "#f4ead7";
      context.fillRect(0, 0, 768, 180);
      context.strokeStyle = room.tint;
      context.lineWidth = 12;
      context.strokeRect(8, 8, 752, 164);
      texture.drawText(`LEVEL ${room.levelIndex + 1}`, null, 77, `700 40px ${SIGN_FONT}`, "#28444c", "#f4ead7", true, true);
      texture.drawText(room.name.toUpperCase(), null, 132, `600 28px ${SIGN_FONT}`, "#28444c", null, true, true);
    };
    paint();
    // Repaint once the pixel font is ready; the first paint uses the fallback.
    void document.fonts?.load(`700 40px ${SIGN_FONT}`).then(() => !this.disposed && paint()).catch(() => undefined);
    texture.updateSamplingMode(Texture.NEAREST_SAMPLINGMODE);

    const material = new StandardMaterial(`roomSignMaterial${room.levelIndex}`, this.scene);
    material.diffuseTexture = texture;
    material.emissiveTexture = texture;
    material.emissiveColor.setAll(1);
    material.specularColor.setAll(0);
    material.disableLighting = true;
    material.backFaceCulling = false;

    const sign = CreatePlane(`roomSignPlane${room.levelIndex}`, { width: 4.3, height: 1 }, this.scene);
    sign.position.set(room.side * 9.0, 6.05, room.z);
    sign.rotation.y = room.side === -1 ? Math.PI / 2 : -Math.PI / 2;
    sign.material = material;
    this.disposables.push(texture, material, sign);
  }

  private material(name: string, hex: string, emissive = false) {
    const material = new StandardMaterial(name, this.scene);
    const color = Color3.FromHexString(hex);
    material.diffuseColor = color;
    material.specularColor = new Color3(0.08, 0.08, 0.08);
    if (emissive) material.emissiveColor = color.scale(0.65);
    this.disposables.push(material);
    return material;
  }

  private box(name: string, dimensions: { width: number; height: number; depth: number }, position: Vector3, material: StandardMaterial) {
    const mesh = CreateBox(name, dimensions, this.scene);
    mesh.position.copyFrom(position);
    mesh.material = material;
    this.disposables.push(mesh);
    return mesh;
  }

  private update(dt: number) {
    const state = this.input.state;
    const x = Number(state.right) - Number(state.left);
    const z = Number(state.forward) - Number(state.backward);
    const moving = x !== 0 || z !== 0;
    if (moving) {
      const length = Math.hypot(x, z) || 1;
      this.doctor.root.position.x += (x / length) * PLAYER_SPEED * dt;
      this.doctor.root.position.z += (z / length) * PLAYER_SPEED * dt;
      this.doctor.root.position.x = Math.min(Math.max(this.doctor.root.position.x, -8.25), 8.25);
      this.doctor.root.position.z = Math.min(Math.max(this.doctor.root.position.z, 1.5), CORRIDOR_LENGTH - 2.5);
    }
    this.doctor.update(dt, moving, x, z);
    this.npcs.update(dt);

    const playerPosition = this.doctor.root.position;
    const closest = this.rooms.find((room) => {
      const dx = playerPosition.x - room.x;
      const dz = playerPosition.z - room.z;
      return Math.hypot(dx, dz) < DOOR_TRIGGER_DISTANCE;
    }) ?? null;
    const closestIndex = closest?.levelIndex ?? null;
    if (closestIndex !== this.nearRoom) {
      this.nearRoom = closestIndex;
      this.onDoorChange(closest);
    }
    if (closest && state.interact && !this.entered) {
      this.entered = true;
      this.onEnterRoom(closest.levelIndex);
    }
    this.input.endFrame();

    const desiredCamera = playerPosition.add(CAMERA_OFFSET);
    this.camera.position = Vector3.Lerp(this.camera.position, desiredCamera, CAMERA_FOLLOW_RATE);
    this.camera.setTarget(playerPosition.add(new Vector3(0, 2.05, 4.4)));
  }

  dispose() {
    this.disposed = true;
    window.removeEventListener("das-hub-move", this.onHubMove);
    this.input.dispose();
    this.doctor.dispose();
    this.npcs.dispose();
    this.library.dispose();
    this.shadows.dispose();
    this.disposables.forEach((item) => item.dispose());
  }
}

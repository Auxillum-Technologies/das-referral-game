// Player.ts — kinematic doctor character for the 2D hospital platformer.
// Features a smooth 7-frame walking animation cycle using Dr. Luna sprite frames.

import { Scene } from "@babylonjs/core/scene";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { ShadowGenerator } from "@babylonjs/core/Lights/Shadows/shadowGenerator";
import type { InputState } from "./InputManager";
import type { CharacterAnimator, CharacterLibrary } from "./hubCharacters";

export const PLAYER_W = 2.4; // world units
export const PLAYER_H = 4.2;

const SPEED = 6.8;
const GRAVITY = -26;
const JUMP_V = 12.0;

const TURN_RATE = 14;

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export class Player {
  root: TransformNode;
  private model: TransformNode;
  private animator: CharacterAnimator | null = null;
  private disposed = false;
  private facing = 1; // 1 = right, -1 = left
  private heading = Math.PI / 2;
  private vx = 0;
  private vy = 0;
  private onGround = false;
  readonly yFloor: number;

  constructor(
    scene: Scene,
    private floors: Rect[],
    startX: number,
    yFloor: number,
    library?: CharacterLibrary,
    shadows?: ShadowGenerator,
  ) {
    this.yFloor = yFloor;
    this.root = new TransformNode("playerRoot", scene);
    this.root.position.set(startX, yFloor + PLAYER_H / 2, 5);

    // Model origin sits at the feet; physics root sits at body center.
    this.model = new TransformNode("playerModel", scene);
    this.model.parent = this.root;
    this.model.position.y = -PLAYER_H / 2;
    this.model.rotation.y = this.heading;
    if (library) {
      library.spawn("doctor", this.model, shadows)
        .then((animator) => {
          if (this.disposed) animator?.dispose();
          else this.animator = animator;
        })
        .catch((error) => console.error("[Player] doctor load failed", error));
    }
  }

  get rect(): Rect {
    return {
      x: this.root.position.x - PLAYER_W / 2,
      y: this.root.position.y - PLAYER_H / 2,
      w: PLAYER_W,
      h: PLAYER_H,
    };
  }

  reset(x: number) {
    this.root.position.x = x;
    this.root.position.y = this.yFloor + PLAYER_H / 2;
    this.vx = 0;
    this.vy = 0;
    this.onGround = true;
    this.facing = 1;
    this.heading = Math.PI / 2;
    this.model.rotation.y = this.heading;
    this.animator?.play("idle");
  }

  update(dt: number, input: InputState, worldMaxX: number, dialogOpen: () => boolean) {
    if (dialogOpen()) {
      this.vx = 0;
      this.animator?.play("idle");
      return;
    }

    const moving = input.left !== input.right;

    // Horizontal movement
    if (input.left) {
      this.vx = -SPEED;
      this.facing = -1;
    } else if (input.right) {
      this.vx = SPEED;
      this.facing = 1;
    } else {
      this.vx = 0;
    }

    // Jump
    if (input.jump && this.onGround) {
      this.vy = JUMP_V;
      this.onGround = false;
    }

    // Gravity
    this.vy += GRAVITY * dt;
    if (this.vy < -20) this.vy = -20;

    // Integration
    const ny = this.root.position.y + this.vy * dt;
    this.root.position.x += this.vx * dt;
    this.root.position.y = ny;
    this.onGround = false;

    const feetY = this.root.position.y - PLAYER_H / 2;
    const r = this.rect;

    // Check collision with floors
    for (const f of this.floors) {
      if (r.x + r.w > f.x && r.x < f.x + f.w) {
        const floorTop = f.y;
        if (this.vy <= 0 && feetY <= floorTop + 0.4) {
          this.root.position.y = floorTop + PLAYER_H / 2;
          this.vy = 0;
          this.onGround = true;
          break;
        }
      }
    }

    // Safety Floor Clamp: Character can NEVER drop below the hospital floor level
    const minCenterY = this.yFloor + PLAYER_H / 2;
    if (this.root.position.y < minCenterY) {
      this.root.position.y = minCenterY;
      this.vy = 0;
      this.onGround = true;
    }

    // World bounds
    const maxX = worldMaxX - PLAYER_W / 2;
    if (this.root.position.x < PLAYER_W / 2) this.root.position.x = PLAYER_W / 2;
    if (this.root.position.x > maxX) this.root.position.x = maxX;

    // Turn toward travel direction; walk clip only while grounded and moving.
    const target = this.facing > 0 ? Math.PI / 2 : -Math.PI / 2;
    this.heading += (target - this.heading) * Math.min(1, dt * TURN_RATE);
    this.model.rotation.y = this.heading;
    this.animator?.play(moving && this.onGround ? "walk" : "idle", moving ? 1.4 : 1);
  }

  dispose() {
    this.disposed = true;
    this.animator?.dispose();
    this.root.dispose(false, true);
  }
}

// PS2-era text: stepped (low frame rate) wipe-in on every text element that appears, via anime.js.
import { animate, steps } from "animejs";

const TEXT_SELECTOR = "h1, h2, h3, p, button, label, kbd, span, li, a, [data-ps2]";
const MAX_MS = 900;
const MS_PER_CHAR = 22;

function ownText(el: Element) {
  let text = "";
  el.childNodes.forEach((node) => {
    if (node.nodeType === Node.TEXT_NODE) text += node.textContent ?? "";
  });
  return text.trim();
}

function reveal(el: HTMLElement, order: number) {
  if (el.dataset.ps2Done) return;
  const text = ownText(el);
  if (!text) return;
  el.dataset.ps2Done = "1";
  const frames = Math.min(Math.max(text.length, 4), 40);
  const duration = Math.min(text.length * MS_PER_CHAR, MAX_MS);
  animate(el, {
    clipPath: ["inset(0 100% 0 0)", "inset(0 0% 0 0)"],
    opacity: [0.2, 1],
    duration,
    delay: Math.min(order * 40, 400),
    ease: steps(frames),
    onComplete: () => {
      el.style.clipPath = "";
      el.style.opacity = "";
    },
  });
}

function collect(node: Node, out: HTMLElement[]) {
  if (!(node instanceof HTMLElement)) return;
  if (node.matches(TEXT_SELECTOR)) out.push(node);
  node.querySelectorAll<HTMLElement>(TEXT_SELECTOR).forEach((el) => out.push(el));
}

export function startPs2TextEffects() {
  if (typeof window === "undefined") return;
  if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
  const run = (nodes: Node[]) => {
    const found: HTMLElement[] = [];
    nodes.forEach((n) => collect(n, found));
    found.forEach((el, i) => reveal(el, i));
  };
  run([document.body]);
  new MutationObserver((records) => {
    const added: Node[] = [];
    records.forEach((r) => r.addedNodes.forEach((n) => added.push(n)));
    if (added.length) run(added);
  }).observe(document.body, { childList: true, subtree: true });
}

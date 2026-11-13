import { createRoot } from "react-dom/client";
import App from "./App";
import "@fontsource/pixelify-sans/400.css";
import "@fontsource/pixelify-sans/600.css";
import "@fontsource/pixelify-sans/700.css";
import "./index.css";
import { startPs2TextEffects } from "./lib/ps2-text";

try {
  createRoot(document.getElementById("root")!).render(<App />);
} catch (err) {
  console.error("Failed to mount app:", err);
}

// Dismiss the loading overlay once the app has mounted (index.html shows a
// visible spinner + retry button if this never fires, avoiding a blank page)
try {
  (window as any).__dasReady?.();
} catch {
  /* overlay not present */
}

startPs2TextEffects();

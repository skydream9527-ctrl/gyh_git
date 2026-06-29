/**
 * Visual Viewport hook for mobile keyboard-aware layouts.
 *
 * On mobile, the virtual keyboard shrinks the visual viewport without changing
 * the layout viewport. This hook tracks `window.visualViewport` geometry so
 * components (especially the chat input) can shift up when the keyboard appears.
 *
 * Returns:
 *  - `keyboardVisible`: true when the visual viewport height is significantly
 *    less than the window inner height (heuristic: >100px difference)
 *  - `keyboardHeight`: estimated keyboard height in px (0 when hidden)
 *  - `viewportHeight`: current visual viewport height
 */
import { useEffect, useState } from "react";

export interface VisualViewportState {
  keyboardVisible: boolean;
  keyboardHeight: number;
  viewportHeight: number;
}

const KEYBOARD_THRESHOLD = 100; // px difference to consider keyboard open

export function useVisualViewport(): VisualViewportState {
  const [state, setState] = useState<VisualViewportState>(() => ({
    keyboardVisible: false,
    keyboardHeight: 0,
    viewportHeight: typeof window !== "undefined" ? window.innerHeight : 0,
  }));

  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return; // Desktop browsers without visualViewport API

    const initialHeight = window.innerHeight;

    const update = () => {
      const currentHeight = vv.height;
      const diff = initialHeight - currentHeight;
      const keyboardVisible = diff > KEYBOARD_THRESHOLD;
      setState({
        keyboardVisible,
        keyboardHeight: keyboardVisible ? diff : 0,
        viewportHeight: currentHeight,
      });
    };

    vv.addEventListener("resize", update);
    vv.addEventListener("scroll", update);
    update();

    return () => {
      vv.removeEventListener("resize", update);
      vv.removeEventListener("scroll", update);
    };
  }, []);

  return state;
}

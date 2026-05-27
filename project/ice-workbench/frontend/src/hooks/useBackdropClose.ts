import { useEffect, useRef } from "react";
import type { MouseEvent } from "react";

// 让弹窗遮罩只在「按下和松开都直接发生在遮罩本身」时才关闭，并统一监听 ESC。
// 修掉常见 bug：在 input 里拖选文字、鼠标拖出弹窗外松开 → click 落在共同祖先（遮罩） → 弹窗误关。
//
// enabled：默认 true。当弹窗组件被父级条件挂载（{open && <Modal/>}）时无须传；
// 当 hook 在父组件顶层、弹窗 JSX 是条件渲染时，传 enabled 让 ESC 仅在弹窗可见时生效。
export function useBackdropClose(
  onClose: (() => void) | null | undefined,
  enabled: boolean = true,
) {
  const downOnBackdrop = useRef(false);

  useEffect(() => {
    if (!enabled || !onClose) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled, onClose]);

  return {
    onMouseDown: (e: MouseEvent) => {
      downOnBackdrop.current = e.target === e.currentTarget;
    },
    onClick: (e: MouseEvent) => {
      const started = downOnBackdrop.current;
      downOnBackdrop.current = false;
      if (started && e.target === e.currentTarget) onClose?.();
    },
  };
}

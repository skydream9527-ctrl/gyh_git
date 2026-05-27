// 包装 click 处理器：如果用户当前正在拖选文字（getSelection 非空），就忽略此次 click。
// 用于「整张卡片可点击 → 进入详情」的场景：避免拖选卡片标题想复制时被当作点击误导航。
export function clickIgnoreSelection(handler: () => void) {
  return () => {
    if (window.getSelection()?.toString()) return;
    handler();
  };
}

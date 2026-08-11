import { useEffect, useRef, useState } from "react";

export function useViewportHeight() {
  const [height, setHeight] = useState(
    () => _read()
  );

  const rafRef = useRef(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  useEffect(() => {
    function update() {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        if (mountedRef.current) setHeight(_read());
      });
    }

    const vv = window.visualViewport;
    if (vv) {
      vv.addEventListener("resize", update);
      vv.addEventListener("scroll", update);
    }
    window.addEventListener("resize", update);

    // Fallback for WebViews where visualViewport events are unreliable
    // after the first keyboard show — poll at 3 points during keyboard animation
    function onFocusChange(e) {
      if (!e.target.matches("input, textarea, [contenteditable]")) return;
      setTimeout(update, 100);
      setTimeout(update, 300);
      setTimeout(update, 600);
    }
    document.addEventListener("focusin", onFocusChange);
    document.addEventListener("focusout", onFocusChange);

    update();

    return () => {
      if (vv) {
        vv.removeEventListener("resize", update);
        vv.removeEventListener("scroll", update);
      }
      window.removeEventListener("resize", update);
      document.removeEventListener("focusin", onFocusChange);
      document.removeEventListener("focusout", onFocusChange);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return height;
}

function _read() {
  // Use the smaller of visualViewport.height and window.innerHeight.
  //   Android adjustResize: both shrink together → min = shrunken value ✓
  //   iOS WebView:          visualViewport shrinks, innerHeight stays → min = visualViewport ✓
  //   Android adjustPan:    visualViewport shrinks, innerHeight stays → min = visualViewport ✓
  // Never use offsetTop / translateY — translating the app down pushes the
  // input *below* the keyboard edge instead of above it.
  const vvh = window.visualViewport?.height ?? window.innerHeight;
  return Math.min(vvh, window.innerHeight);
}

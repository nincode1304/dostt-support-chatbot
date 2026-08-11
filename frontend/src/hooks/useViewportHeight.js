import { useEffect, useRef, useState } from "react";

export function useViewportHeight() {
  const [height, setHeight] = useState(() => _read());

  const rafRef = useRef(null);
  const mountedRef = useRef(true);
  const pollRef = useRef(null);

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

    // Poll every 50ms for up to 2s after any input focus/blur.
    // Needed because on Android WebViews visualViewport.resize fires only on
    // first keypress, not when the keyboard opens — fixed timeouts miss it.
    function startPoll() {
      if (pollRef.current) clearInterval(pollRef.current);
      let ticks = 0;
      let lastH = _read();
      pollRef.current = setInterval(() => {
        const h = _read();
        if (h !== lastH) {
          lastH = h;
          update();
        }
        if (++ticks >= 40) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }, 50);
    }

    const vv = window.visualViewport;
    if (vv) {
      vv.addEventListener("resize", update);
      vv.addEventListener("scroll", update);
    }
    window.addEventListener("resize", update);

    function onFocusChange(e) {
      if (!e.target.matches("input, textarea, [contenteditable]")) return;
      startPoll();
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
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, []);

  return height;
}

function _read() {
  const vvh = window.visualViewport?.height ?? window.innerHeight;
  return Math.min(vvh, window.innerHeight);
}

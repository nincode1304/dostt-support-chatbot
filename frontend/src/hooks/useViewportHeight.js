import { useEffect, useRef, useState } from "react";

export function useViewportHeight() {
  const [viewport, setViewport] = useState(() => ({
    height: window.visualViewport?.height ?? window.innerHeight,
    offsetTop: window.visualViewport?.offsetTop ?? 0,
  }));

  const rafRef = useRef(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  useEffect(() => {
    function read() {
      if (!mountedRef.current) return;
      const vv = window.visualViewport;
      setViewport({
        height: vv?.height ?? window.innerHeight,
        offsetTop: vv?.offsetTop ?? 0,
      });
    }

    function update() {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      // rAF ensures we read AFTER the browser has finished layout
      rafRef.current = requestAnimationFrame(read);
    }

    // visualViewport is the primary signal (fires during keyboard animation)
    const vv = window.visualViewport;
    if (vv) {
      vv.addEventListener("resize", update);
      vv.addEventListener("scroll", update);
    }
    // window.resize is a fallback for WebViews that don't fire visualViewport events
    window.addEventListener("resize", update);

    // iOS WebView: visualViewport events become unreliable after first keyboard show.
    // Listening to focusin/focusout on inputs gives us a reliable second trigger.
    // Two delayed reads cover the keyboard slide-in animation (~250–300 ms on iOS).
    function onFocusChange(e) {
      if (!e.target.matches("input, textarea, [contenteditable]")) return;
      // Three reads: catches mid-animation, post-animation, and slow Android keyboards
      setTimeout(update, 100);
      setTimeout(update, 300);
      setTimeout(update, 600);
    }
    document.addEventListener("focusin", onFocusChange);
    document.addEventListener("focusout", onFocusChange);

    read(); // sync with current state on mount

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

  return viewport;
}

/**
 * WebView bridge: reads auth context passed by the Dostt mobile app.
 *
 * All context (token, userType, language, platform, app_version_code) comes
 * via postMessage({ type: "INIT", ... }) sent by the native app after webviewReady.
 */
import { useCallback, useEffect, useState } from "react";

export function useBridge() {
  const isInWebView = !!window.ReactNativeWebView;

  const [bridgeData, setBridgeData] = useState(() =>
    isInWebView
      ? { token: null, userType: null, initLanguage: null, platform: null, appVersionCode: null }
      : { token: "dev", userType: "USER", initLanguage: null, platform: "web", appVersionCode: null }
  );

  const send = useCallback((name, payload = null) => {
    if (!window.ReactNativeWebView) {
      console.warn(`not in WebView, dropped: ${name}`);
      return;
    }
    window.ReactNativeWebView.postMessage(JSON.stringify({ name, payload }));
  }, []);

  useEffect(() => {
    // Tell native the page is ready to receive INIT
    send("webviewReady");

    const handler = (event) => {
      try {
        const msg =
          typeof event.data === "string" ? JSON.parse(event.data) : event.data;
        if (msg?.type === "INIT" && msg.token) {
          // Only accept the token once — ignore any attempt to override it
          setBridgeData((prev) => {
            if (prev.token) return prev;
            return {
              token: msg.token,
              userType: msg.user_type || "USER",
              initLanguage: msg.language || null,
              platform: msg.platform || null,
              appVersionCode: msg.app_version_code || null,
            };
          });
        }
      } catch {
        // Ignore non-JSON messages
      }
    };

    window.addEventListener("message", handler);
    document.addEventListener("message", handler); // Android WebView fix
    return () => {
      window.removeEventListener("message", handler);
      document.removeEventListener("message", handler);
    };
  }, []);

  return { ...bridgeData, send };
}

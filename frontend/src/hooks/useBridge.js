/**
 * WebView bridge: reads auth context passed by the Dostt mobile app.
 *
 * userType  → from URL path (/user or /listener), set by the app when opening the WebView
 * token     → NEVER in the URL; comes only via postMessage({ type: "INIT", token: "..." })
 *             sent by the native app after the WebView loads
 */
import { useEffect, useState } from "react";

export function useBridge() {
  const [bridgeData, setBridgeData] = useState(() => ({
    token: null,
    userType: readUserTypeFromPath(),
  }));

  useEffect(() => {
    const handler = (event) => {
      try {
        const msg =
          typeof event.data === "string" ? JSON.parse(event.data) : event.data;
        if (msg?.type === "INIT" && msg.token) {
          // Only accept the token once — ignore any attempt to override it
          setBridgeData((prev) => {
            if (prev.token) return prev;
            return { ...prev, token: msg.token };
          });
        }
      } catch {
        // Ignore non-JSON messages
      }
    };

    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, []);

  return bridgeData;
}

function readUserTypeFromPath() {
  const path = window.location.pathname.toLowerCase();
  if (path.startsWith("/listener")) return "LISTENER";
  return "USER"; // /user or any other path defaults to USER
}

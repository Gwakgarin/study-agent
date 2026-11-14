import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { STYLE, MARKUP, init } from "./landingStory.js";

// The intro is one long scroll story (a mark that travels between scenes, tone shifts, pinned
// scenes). It lives in a shadow root so its many generic class names cannot clash with the app's CSS.
export default function Landing() {
  const hostRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    const host = hostRef.current;
    const root = host.shadowRoot || host.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${STYLE}</style><div class="root">${MARKUP}</div>`;
    const stop = init(root, host, navigate);
    return () => {
      stop();
      root.innerHTML = "";
    };
  }, [navigate]);

  return <div ref={hostRef} />;
}

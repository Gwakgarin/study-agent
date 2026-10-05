import { useState } from "react";

export default function Sources({ sources }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="sources">
      <button type="button" className="sources-toggle" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span>참고한 노트 {sources.length}개</span>
        <span className="sources-names">{sources.map((s) => s.source).join(" · ")}</span>
        <span className="sources-caret" aria-hidden="true">{open ? "▴" : "▾"}</span>
      </button>
      {open && (
        <ul className="sources-list">
          {sources.map((s) => (
            <li key={s.source}>
              <div className="sources-file">{s.source}</div>
              <p>{s.snippet}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

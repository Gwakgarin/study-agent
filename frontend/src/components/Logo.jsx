export function LogoMark({ size }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" className="logo-mark" aria-hidden="true">
      <path
        d="M15 15H60A25 25 0 0 1 69 63.4L85 85H61L42 60V85H15Z"
        fill="var(--accent)"
        stroke="var(--accent)"
        strokeWidth="10"
        strokeLinejoin="round"
      />
      <path
        d="M42 37.5L56 28.5V46.5Z"
        fill="var(--accent-ink)"
        stroke="var(--accent-ink)"
        strokeWidth="5"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function Logo({ size = 28 }) {
  return (
    <span className="logo" style={{ fontSize: size }}>
      <LogoMark size={Math.round(size * 0.95)} />
      recap
    </span>
  );
}

function LogoMark({ size }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 28 28"
      fill="none"
      className="logo-mark"
      aria-hidden="true"
    >
      <rect width="28" height="28" rx="8" fill="var(--accent)" />
      <g
        transform="translate(4,4) scale(0.83)"
        stroke="var(--accent-ink)"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      >
        <polyline points="23 4 23 10 17 10" />
        <polyline points="1 20 1 14 7 14" />
        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
      </g>
    </svg>
  );
}

export default function Logo({ size = 28 }) {
  return (
    <span className="logo" style={{ fontSize: size }}>
      <LogoMark size={Math.round(size * 1.1)} />
      Recap
    </span>
  );
}

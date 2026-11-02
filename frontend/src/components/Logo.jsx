function LogoMark({ size }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="20 20 60 60"
      fill="var(--accent)"
      className="logo-mark"
      aria-hidden="true"
    >
      <rect x="23" y="27" width="18" height="46" rx="9" />
      <rect x="47" y="27" width="8" height="46" rx="4" />
      <circle cx="70" cy="40" r="8.5" />
      <circle cx="70" cy="60" r="8.5" />
    </svg>
  );
}

export default function Logo({ size = 28 }) {
  return (
    <span className="logo" style={{ fontSize: size }}>
      <LogoMark size={Math.round(size * 0.92)} />
      recap
    </span>
  );
}

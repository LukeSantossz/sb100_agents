import { useId } from "react";

/**
 * The assistant's avatar: a matte head with a dark face, two green eyes and a
 * sprout on top. Its state comes only from the request flow, never from a timer.
 */
export type AgentState = "idle" | "processing" | "done" | "error";

export default function AgentHead({ state }: { state: AgentState }) {
  // Gradient and filter ids must be unique per instance on one page.
  const id = useId();
  const shell = `${id}-shell`;
  const face = `${id}-face`;
  const glow = `${id}-glow`;

  return (
    <svg
      className="agent-head"
      data-state={state}
      viewBox="0 0 48 48"
      width="44"
      height="44"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <radialGradient id={shell} cx="35%" cy="28%" r="80%">
          <stop offset="0" stopColor="#FFFFFF" />
          <stop offset="0.55" stopColor="#E3E6E1" />
          <stop offset="1" stopColor="#B4BCB6" />
        </radialGradient>
        <linearGradient id={face} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#28322D" />
          <stop offset="1" stopColor="#0F1412" />
        </linearGradient>
        <filter id={glow} x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur stdDeviation="1.4" />
        </filter>
      </defs>

      <g className="agent-sprout">
        <path d="M24 12V6" stroke="#1F7A47" strokeWidth="1.6" strokeLinecap="round" />
        <path d="M24 8C20.5 8 18.2 5.8 18 3C21.2 3 23.6 4.9 24 8Z" fill="#2E9D5E" />
        <path d="M24 7C27.2 7 29.6 4.9 30 2.2C26.9 2.2 24.4 4 24 7Z" fill="#1F7A47" />
      </g>

      <rect x="5" y="11" width="38" height="34" rx="15" fill={`url(#${shell})`} />
      <rect x="10.5" y="18" width="27" height="19.5" rx="9.5" fill={`url(#${face})`} />
      <rect
        x="11"
        y="18.5"
        width="26"
        height="18.5"
        rx="9"
        fill="none"
        stroke="#FFFFFF"
        strokeOpacity="0.08"
      />

      <g className="agent-eyes">
        <g filter={`url(#${glow})`} opacity="0.7">
          <ellipse className="agent-eye" cx="19" cy="27.5" rx="2.6" ry="3.1" />
          <ellipse className="agent-eye" cx="29" cy="27.5" rx="2.6" ry="3.1" />
        </g>
        <ellipse className="agent-eye" cx="19" cy="27.5" rx="2.2" ry="2.7" />
        <ellipse className="agent-eye" cx="29" cy="27.5" rx="2.2" ry="2.7" />
      </g>
    </svg>
  );
}

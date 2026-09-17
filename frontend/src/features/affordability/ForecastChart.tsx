interface ChartProps {
  minBalance: number;
  plan: { date: string; amount: string }[];
}

/**
 * Compact SVG chart. The engine returns plan points, not a full series; we render
 * the plan's payment events on a simple baseline so the user sees *when* money
 * leaves relative to today and the 90-day horizon. (The full balance trajectory
 * lives server-side in the engine; the summary endpoint exposes the verdict.)
 */
export function ForecastChart({ minBalance, plan }: ChartProps) {
  const W = 320;
  const H = 140;
  const pad = 8;

  const today = new Date();
  const horizon = new Date(today.getTime() + 90 * 86400000);
  const total = horizon.getTime() - today.getTime();

  const xOf = (iso: string) => {
    const d = new Date(`${iso}T00:00:00`);
    const clamped = Math.min(Math.max(d.getTime(), today.getTime()), horizon.getTime());
    return pad + ((clamped - today.getTime()) / total) * (W - 2 * pad);
  };

  const maxAmt = Math.max(...plan.map((p) => parseFloat(p.amount.replace(/[^0-9.\-]/g, ''))), 1);
  const barW = Math.max(6, (W - 2 * pad) / 30);

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="mt-4 w-full"
      role="img"
      aria-label="Payment plan timeline over 90 days"
    >
      {/* baseline */}
      <line x1={pad} y1={H - 24} x2={W - pad} y2={H - 24} stroke="#d5d9dd" strokeWidth="1" />
      {/* horizon label */}
      <text x={W - pad} y={H - 8} textAnchor="end" fontSize="9" fill="#87929c">
        day 90
      </text>
      <text x={pad} y={H - 8} fontSize="9" fill="#87929c">
        today
      </text>

      {plan.map((p, i) => {
        const raw = parseFloat(p.amount.replace(/[^0-9.\-]/g, ''));
        const h = Math.max(4, (raw / maxAmt) * (H - 48));
        return (
          <g key={i}>
            <rect
              x={xOf(p.date) - barW / 2}
              y={H - 24 - h}
              width={barW}
              height={h}
              rx="2"
              fill="#578c67"
            />
            <text
              x={xOf(p.date)}
              y={H - 28 - h}
              textAnchor="middle"
              fontSize="8"
              fill="#68757f"
            >
              {p.amount.length > 9 ? `${p.amount.slice(0, 8)}…` : p.amount}
            </text>
          </g>
        );
      })}

      {plan.length === 0 && (
        <text x={W / 2} y={H / 2} textAnchor="middle" fontSize="10" fill="#87929c">
          Single payment today — nothing due later.
        </text>
      )}
      {minBalance > 0 && (
        <text x={pad} y={12} fontSize="9" fill="#87929c">
          Minimum kept: {minBalance.toLocaleString()}
        </text>
      )}
    </svg>
  );
}

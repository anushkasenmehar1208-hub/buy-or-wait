import { useEffect, useState } from 'react';

interface ChartProps {
  minBalance: number;
  plan: { date: string; amount: string }[];
}

/*
 * Chart colors read the same theme tokens as the rest of the UI. Applied to
 * SVG attributes on mount (and on theme change) via the `dark` class, since
 * SVG presentation attributes can't use Tailwind opacity-variant utilities.
 */
function chartColors(): { line: string; label: string; bar: string } {
  const dark = document.documentElement.classList.contains('dark');
  return dark
    ? { line: '#3c444b', label: '#949fa9', bar: '#7aa985' } // ink-300 / ink-500 / sage-500 (dark)
    : { line: '#d5d9dd', label: '#87929c', bar: '#578c67' }; // ink-200 / ink-400 / sage-500 (light)
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

  const [colors, setColors] = useState(chartColors);
  useEffect(() => {
    const observer = new MutationObserver(() => setColors(chartColors()));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

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
      <line x1={pad} y1={H - 24} x2={W - pad} y2={H - 24} stroke={colors.line} strokeWidth="1" />
      {/* horizon label */}
      <text x={W - pad} y={H - 8} textAnchor="end" fontSize="9" fill={colors.label}>
        day 90
      </text>
      <text x={pad} y={H - 8} fontSize="9" fill={colors.label}>
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
              fill={colors.bar}
            />
            <text
              x={xOf(p.date)}
              y={H - 28 - h}
              textAnchor="middle"
              fontSize="8"
              fill={colors.label}
            >
              {p.amount.length > 9 ? `${p.amount.slice(0, 8)}…` : p.amount}
            </text>
          </g>
        );
      })}

      {plan.length === 0 && (
        <text x={W / 2} y={H / 2} textAnchor="middle" fontSize="10" fill={colors.label}>
          Single payment today — nothing due later.
        </text>
      )}
      {minBalance > 0 && (
        <text x={pad} y={12} fontSize="9" fill={colors.label}>
          Minimum kept: {minBalance.toLocaleString()}
        </text>
      )}
    </svg>
  );
}

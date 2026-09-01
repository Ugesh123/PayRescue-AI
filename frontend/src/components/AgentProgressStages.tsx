import { useEffect, useState } from "react";

const STAGES = [
  "Loading Transaction",
  "Diagnosing Failure",
  "Evaluating Strategies",
  "Safety Check",
  "Executing Recovery",
];

export default function AgentProgressStages({ isRunning }: { isRunning: boolean }) {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (!isRunning) {
      setActiveIndex(0);
      return;
    }
    const interval = setInterval(() => {
      setActiveIndex((prev) => (prev < STAGES.length - 1 ? prev + 1 : prev));
    }, 600);
    return () => clearInterval(interval);
  }, [isRunning]);

  if (!isRunning) return null;

  return (
    <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
      <ul className="space-y-2 text-sm">
        {STAGES.map((stage, index) => (
          <li key={stage} className="flex items-center gap-2">
            {index < activeIndex && <span className="text-emerald-600">✓</span>}
            {index === activeIndex && (
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
            )}
            {index > activeIndex && <span className="h-3 w-3 rounded-full border border-slate-300" />}
            <span className={index <= activeIndex ? "text-slate-800" : "text-slate-400"}>{stage}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

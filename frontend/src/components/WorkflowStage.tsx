import type { ReactNode } from "react";

export default function WorkflowStage({
  icon,
  title,
  children,
  showConnector = true,
}: {
  icon?: string;
  title: string;
  children: ReactNode;
  showConnector?: boolean;
}) {
  return (
    <div>
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900">
          {icon ? `${icon} ` : ""}
          {title}
        </h3>
        <div className="mt-3">{children}</div>
      </div>
      {showConnector && (
        <div className="flex justify-center py-1 text-slate-300">
          <span className="text-lg leading-none">↓</span>
        </div>
      )}
    </div>
  );
}

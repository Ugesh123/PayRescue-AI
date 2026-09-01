import { Routes, Route, NavLink } from "react-router-dom";
import DashboardPage from "./pages/DashboardPage";
import TransactionsPage from "./pages/TransactionsPage";
import TransactionRecoveryPage from "./pages/TransactionRecoveryPage";

const NAV_LINKS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/transactions", label: "Transactions", end: false },
];

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold text-slate-900">PayRescue AI</span>
            <span className="rounded-full bg-slate-900 px-2 py-0.5 text-[10px] font-medium text-white">BETA</span>
          </div>
          <nav className="flex gap-4 text-sm">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  `font-medium ${isActive ? "text-slate-900" : "text-slate-500 hover:text-slate-800"}`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="/transactions/:id" element={<TransactionRecoveryPage />} />
        </Routes>
      </main>
    </div>
  );
}

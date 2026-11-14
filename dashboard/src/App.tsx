import { NavLink, Route, Routes } from "react-router-dom";
import Overview from "./pages/Overview";
import BuoyMap from "./pages/BuoyMap";
import LiveData from "./pages/LiveData";
import AiDetection from "./pages/AiDetection";
import AttackConsole from "./pages/AttackConsole";
import Comparison from "./pages/Comparison";
import Incidents from "./pages/Incidents";
import SystemHealth from "./pages/SystemHealth";

const PAGES = [
  { path: "/", label: "Overview", element: <Overview /> },
  { path: "/map", label: "Buoy Map", element: <BuoyMap /> },
  { path: "/live", label: "Live Ocean Data", element: <LiveData /> },
  { path: "/ai", label: "AI Detection", element: <AiDetection /> },
  { path: "/attacks", label: "Attack Console", element: <AttackConsole /> },
  { path: "/compare", label: "Unprotected vs SeaShield", element: <Comparison /> },
  { path: "/incidents", label: "Incidents & Alerts", element: <Incidents /> },
  { path: "/system", label: "System Health", element: <SystemHealth /> },
];

export default function App() {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          SeaShield <span>AI</span>
        </div>
        <nav>
          {PAGES.map((p) => (
            <NavLink key={p.path} to={p.path} end>
              {p.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">
        <Routes>
          {PAGES.map((p) => (
            <Route key={p.path} path={p.path} element={p.element} />
          ))}
        </Routes>
      </main>
    </div>
  );
}

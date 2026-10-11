import { lazy, Suspense } from "react";

// Each page loads only its own code and styles.
const PatientPage = lazy(() => import("./pages/PatientPage.jsx"));
const DashboardPage = lazy(() => import("./dashboard/DashboardPage.jsx"));

export default function App() {
  const path = window.location.pathname.replace(/\/+$/, "");
  return (
    <Suspense fallback={null}>
      {path.startsWith("/dashboard") ? <DashboardPage /> : <PatientPage />}
    </Suspense>
  );
}

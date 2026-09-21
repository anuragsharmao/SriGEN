import { BrowserRouter, Routes, Route } from "react-router-dom";
import LoginPage from "./pages/LoginPage.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import GeneratePage from "./pages/GeneratePage.jsx";
import RefinePage from "./pages/RefinePage.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/generate" element={<GeneratePage />} />
        <Route path="/refine" element={<RefinePage />} />

        {/*
          To add a new page:
          1. Create src/pages/YourPage.jsx (+ YourPage.css if it needs its own styles)
          2. Import it above: import YourPage from "./pages/YourPage.jsx";
          3. Add a route below: <Route path="/your-path" element={<YourPage />} />
        */}
      </Routes>
    </BrowserRouter>
  );
}

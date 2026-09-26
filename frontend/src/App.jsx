import { BrowserRouter, Routes, Route } from "react-router-dom";
import LoginPage from "./pages/LoginPage.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import GeneratePage from "./pages/GeneratePage.jsx";
import RefinePage from "./pages/RefinePage.jsx";
import ResultPage from "./pages/ResultPage.jsx";
import VerifyReviewPage from "./pages/VerifyReviewPage.jsx";
import ApprovalPage from "./pages/ApprovalPage.jsx";
import ProvenancePage from "./pages/ProvenancePage.jsx";

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>

        <Route path="/" element={<LoginPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/generate" element={<GeneratePage />} />
        <Route path="/refine" element={<RefinePage />} />
        <Route path="/result" element={<ResultPage />} />
        <Route path="/verify-review" element={<VerifyReviewPage />} />
        <Route path="/approval" element={<ApprovalPage />} />
        <Route path="/provenance" element={<ProvenancePage />} />
      </Routes>
    </BrowserRouter>
  );
}


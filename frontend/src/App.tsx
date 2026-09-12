import { Navigate, Route, Routes } from "react-router-dom";
import JobEditor from "./pages/JobEditor";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/jobs/new/editor" replace />} />
      <Route path="/jobs/:jobId/editor" element={<JobEditor />} />
    </Routes>
  );
}

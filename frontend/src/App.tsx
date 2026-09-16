import { Route, Routes } from "react-router-dom";
import JobDetail from "./pages/JobDetail";
import JobEditor from "./pages/JobEditor";
import JobsList from "./pages/JobsList";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import NewJob from "./pages/NewJob";
import Onboarding from "./pages/Onboarding";
import Profile from "./pages/Profile";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="/profile" element={<Profile />} />
      <Route path="/jobs" element={<JobsList />} />
      <Route path="/jobs/new" element={<NewJob />} />
      <Route path="/jobs/:jobId" element={<JobDetail />} />
      <Route path="/jobs/:jobId/editor" element={<JobEditor />} />
    </Routes>
  );
}

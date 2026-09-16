import { Link, useNavigate } from "react-router-dom";
import { logout } from "../api/client";

export default function NavBar() {
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <header className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3">
      <div className="flex items-center gap-5">
        <span className="text-sm font-semibold text-gray-800">Resume Tailor</span>
        <Link to="/jobs" className="text-sm text-gray-500 hover:text-gray-800">
          Jobs
        </Link>
        <Link to="/profile" className="text-sm text-gray-500 hover:text-gray-800">
          Profile
        </Link>
        <Link to="/onboarding" className="text-sm text-gray-500 hover:text-gray-800">
          Settings
        </Link>
      </div>
      <button onClick={handleLogout} className="text-sm text-gray-500 hover:text-gray-800">
        Log out
      </button>
    </header>
  );
}

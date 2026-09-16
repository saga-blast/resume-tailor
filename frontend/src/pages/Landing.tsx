import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getMe, getOnboardingStatus } from "../api/client";

export default function Landing() {
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;

    async function resolve() {
      try {
        await getMe();
      } catch {
        if (!cancelled) navigate("/login", { replace: true });
        return;
      }

      try {
        const status = await getOnboardingStatus();
        if (!cancelled) {
          if (!status.has_llm_config || !status.has_profile) {
            navigate("/onboarding", { replace: true });
          } else {
            navigate("/jobs", { replace: true });
          }
        }
      } catch {
        if (!cancelled) navigate("/onboarding", { replace: true });
      }
    }

    resolve();
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  return <div className="p-6 text-sm text-gray-400">Loading…</div>;
}

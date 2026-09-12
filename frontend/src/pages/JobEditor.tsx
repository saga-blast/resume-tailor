import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { compileResume, createJob, getResume, saveResume } from "../api/client";
import LatexEditor from "../components/editor/LatexEditor";
import PdfPreview from "../components/editor/PdfPreview";
import SplitPane from "../components/editor/SplitPane";
import { SAMPLE_TEX } from "../sampleResume";

type CompileState = "idle" | "compiling" | "success" | "error";

function base64ToBlobUrl(base64: string, mimeType: string): string {
  const byteChars = atob(base64);
  const byteNumbers = new Array(byteChars.length);
  for (let i = 0; i < byteChars.length; i++) {
    byteNumbers[i] = byteChars.charCodeAt(i);
  }
  const blob = new Blob([new Uint8Array(byteNumbers)], { type: mimeType });
  return URL.createObjectURL(blob);
}

export default function JobEditor() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [numericJobId, setNumericJobId] = useState<number | null>(null);
  const [texSource, setTexSource] = useState("");
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [compileState, setCompileState] = useState<CompileState>("idle");
  const [compileLog, setCompileLog] = useState("");
  const [compileMessage, setCompileMessage] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      if (jobId === "new") {
        const job = await createJob("Demo Resume", SAMPLE_TEX);
        if (!cancelled) navigate(`/jobs/${job.id}/editor`, { replace: true });
        return;
      }
      const id = Number(jobId);
      const resume = await getResume(id);
      if (!cancelled) {
        setNumericJobId(id);
        setTexSource(resume.tex_source);
      }
    }

    bootstrap().catch((err) => console.error(err));
    return () => {
      cancelled = true;
    };
  }, [jobId, navigate]);

  const handleCompile = useCallback(async () => {
    if (numericJobId === null) return;
    setCompileState("compiling");
    try {
      const result = await compileResume(numericJobId, texSource);
      setCompileLog(result.log);
      setCompileMessage(result.message);
      if (result.status === "success" && result.pdf_base64) {
        const url = base64ToBlobUrl(result.pdf_base64, "application/pdf");
        setPdfUrl((prev) => {
          if (prev) URL.revokeObjectURL(prev);
          return url;
        });
        setCompileState("success");
      } else {
        setCompileState("error");
      }
    } catch (err) {
      setCompileState("error");
      setCompileMessage(err instanceof Error ? err.message : "Compile failed");
    }
  }, [numericJobId, texSource]);

  const handleSave = useCallback(async () => {
    if (numericJobId === null) return;
    setSaveState("saving");
    await saveResume(numericJobId, texSource);
    setSaveState("saved");
  }, [numericJobId, texSource]);

  if (numericJobId === null) {
    return <div className="p-6 text-sm text-gray-500">Loading...</div>;
  }

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-gray-200 px-4 py-2">
        <h1 className="text-sm font-semibold text-gray-800">Resume Tailor</h1>
        <div className="flex items-center gap-3">
          <CompileStatusBadge state={compileState} />
          <button
            onClick={handleSave}
            className="rounded border border-gray-300 px-3 py-1 text-sm hover:bg-gray-50"
          >
            {saveState === "saving" ? "Saving…" : "Save"}
          </button>
          <button
            onClick={handleCompile}
            disabled={compileState === "compiling"}
            className="rounded bg-indigo-600 px-3 py-1 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {compileState === "compiling" ? "Compiling…" : "Compile"}
          </button>
          <a
            href={pdfUrl ?? undefined}
            download="resume.pdf"
            className={`rounded border border-gray-300 px-3 py-1 text-sm ${
              pdfUrl ? "hover:bg-gray-50" : "pointer-events-none opacity-40"
            }`}
          >
            Download PDF
          </a>
        </div>
      </header>

      <SplitPane
        left={<LatexEditor value={texSource} onChange={setTexSource} />}
        right={
          <PdfPreview
            pdfUrl={pdfUrl}
            compileState={compileState}
            compileLog={compileLog}
            compileMessage={compileMessage}
          />
        }
      />
    </div>
  );
}

function CompileStatusBadge({ state }: { state: CompileState }) {
  const styles: Record<CompileState, string> = {
    idle: "text-gray-400",
    compiling: "text-amber-500",
    success: "text-emerald-600",
    error: "text-red-600",
  };
  const labels: Record<CompileState, string> = {
    idle: "Not compiled yet",
    compiling: "Compiling…",
    success: "Compiled",
    error: "Compile failed",
  };
  return <span className={`text-xs font-medium ${styles[state]}`}>{labels[state]}</span>;
}

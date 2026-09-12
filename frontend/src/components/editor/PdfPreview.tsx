type CompileState = "idle" | "compiling" | "success" | "error";

interface PdfPreviewProps {
  pdfUrl: string | null;
  compileState: CompileState;
  compileLog: string;
  compileMessage: string | null;
}

export default function PdfPreview({ pdfUrl, compileState, compileLog, compileMessage }: PdfPreviewProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 bg-gray-100">
        {pdfUrl ? (
          <iframe title="Resume PDF preview" src={pdfUrl} className="h-full w-full border-0" />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-gray-400">
            No PDF yet — click Compile
          </div>
        )}
      </div>
      {compileState === "error" && (
        <div className="max-h-56 overflow-auto border-t border-red-200 bg-red-50 p-3 text-xs">
          <p className="mb-1 font-semibold text-red-700">{compileMessage ?? "Compile failed"}</p>
          <pre className="whitespace-pre-wrap text-red-800">{compileLog}</pre>
        </div>
      )}
    </div>
  );
}

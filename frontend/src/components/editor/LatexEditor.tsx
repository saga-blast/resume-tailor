import Editor from "@monaco-editor/react";

interface LatexEditorProps {
  value: string;
  onChange: (value: string) => void;
}

export default function LatexEditor({ value, onChange }: LatexEditorProps) {
  return (
    <Editor
      height="100%"
      language="latex"
      value={value}
      onChange={(v) => onChange(v ?? "")}
      options={{
        minimap: { enabled: false },
        fontSize: 13,
        wordWrap: "on",
        scrollBeyondLastLine: false,
      }}
    />
  );
}

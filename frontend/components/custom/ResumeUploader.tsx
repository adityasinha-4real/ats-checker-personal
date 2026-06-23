"use client";
import { useState, useCallback } from "react";
import { Upload, FileText, X, CheckCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { resumeApi, type Resume } from "@/lib/api";
import { toast } from "@/components/ui/use-toast";

interface ResumeUploaderProps {
  onUploaded?: (resumes: Resume[]) => void;
  className?: string;
}

export function ResumeUploader({ onUploaded, className }: ResumeUploaderProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);

  const addFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    const valid = Array.from(incoming).filter(
      (f) => f.name.endsWith(".pdf") || f.name.endsWith(".docx")
    );
    if (valid.length < incoming.length) {
      toast({ title: "Invalid files", description: "Only PDF and DOCX files are accepted.", variant: "destructive" });
    }
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      return [...prev, ...valid.filter((f) => !existing.has(f.name))];
    });
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  }, []);

  const removeFile = (name: string) => setFiles((p) => p.filter((f) => f.name !== name));

  const handleUpload = async () => {
    if (!files.length) return;
    setUploading(true);
    try {
      const resumes = await resumeApi.upload(files);
      toast({ title: "Upload successful", description: `${resumes.length} resume(s) uploaded and parsed.` });
      setFiles([]);
      onUploaded?.(resumes);
    } catch (err: unknown) {
      toast({ title: "Upload failed", description: err instanceof Error ? err.message : "Unknown error", variant: "destructive" });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className={cn("space-y-4", className)}>
      <div
        onDrop={onDrop}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        className={cn(
          "border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer",
          dragging ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
        )}
        onClick={() => document.getElementById("file-input")?.click()}
      >
        <Upload className="mx-auto h-10 w-10 text-gray-400 mb-3" />
        <p className="text-sm font-medium text-gray-700">Drag & drop resumes here</p>
        <p className="text-xs text-gray-500 mt-1">PDF, DOCX — up to 10MB each — multiple files supported</p>
        <input
          id="file-input"
          type="file"
          multiple
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => addFiles(e.target.files)}
        />
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((f) => (
            <div key={f.name} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border">
              <FileText className="h-4 w-4 text-blue-600 shrink-0" />
              <span className="text-sm text-gray-700 flex-1 truncate">{f.name}</span>
              <span className="text-xs text-gray-400">{(f.size / 1024).toFixed(0)} KB</span>
              <button onClick={() => removeFile(f.name)} className="text-gray-400 hover:text-red-500">
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
          <Button onClick={handleUpload} disabled={uploading} className="w-full">
            {uploading ? (
              <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Uploading & Parsing...</>
            ) : (
              <><CheckCircle className="h-4 w-4 mr-2" /> Upload {files.length} Resume{files.length > 1 ? "s" : ""}</>
            )}
          </Button>
        </div>
      )}
    </div>
  );
}

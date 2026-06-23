"use client";
import { useState } from "react";
import { Save, FolderOpen, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { jdApi, type JobDescriptionListItem } from "@/lib/api";
import { toast } from "@/components/ui/use-toast";

interface JobDescriptionInputProps {
  savedJDs: JobDescriptionListItem[];
  onJDSelected?: (jdId: number | null, jdText: string, title: string, company: string) => void;
  onSaved?: () => void;
}

export function JobDescriptionInput({ savedJDs, onJDSelected, onSaved }: JobDescriptionInputProps) {
  const [mode, setMode] = useState<"new" | "saved">("new");
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [description, setDescription] = useState("");
  const [selectedJdId, setSelectedJdId] = useState<string>("");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!title.trim() || !description.trim()) {
      toast({ title: "Missing fields", description: "Title and description are required.", variant: "destructive" });
      return;
    }
    setSaving(true);
    try {
      await jdApi.create({ title, company, description });
      toast({ title: "Saved!", description: "Job description saved to history." });
      onSaved?.();
    } catch (err: unknown) {
      toast({ title: "Save failed", description: err instanceof Error ? err.message : "Error", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleSelectSaved = (id: string) => {
    setSelectedJdId(id);
    const jd = savedJDs.find((j) => j.id === parseInt(id));
    if (jd) onJDSelected?.(jd.id, "", jd.title, jd.company);
  };

  const handleDescriptionChange = (val: string) => {
    setDescription(val);
    onJDSelected?.(null, val, title, company);
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <button
          onClick={() => setMode("new")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${mode === "new" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
        >
          Paste New JD
        </button>
        <button
          onClick={() => setMode("saved")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${mode === "saved" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
        >
          Load Saved JD ({savedJDs.length})
        </button>
      </div>

      {mode === "new" ? (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="jd-title">Job Title *</Label>
              <Input
                id="jd-title"
                placeholder="e.g. Senior Python Developer"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="jd-company">Company (optional)</Label>
              <Input
                id="jd-company"
                placeholder="e.g. TechCorp"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
              />
            </div>
          </div>
          <div>
            <Label htmlFor="jd-text">Job Description *</Label>
            <Textarea
              id="jd-text"
              placeholder="Paste the full job description here..."
              value={description}
              onChange={(e) => handleDescriptionChange(e.target.value)}
              className="min-h-[200px] font-mono text-xs"
            />
            <p className="text-xs text-muted-foreground mt-1">
              {description.split(/\s+/).filter(Boolean).length} words
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={handleSave} disabled={saving || !title || !description}>
            <Save className="h-4 w-4 mr-2" />
            {saving ? "Saving..." : "Save for Later"}
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {savedJDs.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No saved job descriptions yet. Paste a new one to get started.
            </p>
          ) : (
            <div>
              <Label>Select a saved job description</Label>
              <Select value={selectedJdId} onValueChange={handleSelectSaved}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a job description..." />
                </SelectTrigger>
                <SelectContent>
                  {savedJDs.map((jd) => (
                    <SelectItem key={jd.id} value={String(jd.id)}>
                      {jd.title} {jd.company ? `@ ${jd.company}` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

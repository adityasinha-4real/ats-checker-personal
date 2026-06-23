"use client";
import { useEffect, useState } from "react";
import {
  variantsApi, jdApi,
  type ResumeVariant, type VariantType, type JobDescriptionListItem,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "@/components/ui/use-toast";
import { Loader2, Plus, Copy, Trash2, Star, Files, ChevronDown, ChevronRight } from "lucide-react";

const VARIANT_TYPES: VariantType[] = ["master", "backend", "fullstack", "ai", "custom"];

const TYPE_COLORS: Record<VariantType, string> = {
  master: "bg-gray-700 text-white",
  backend: "bg-blue-600 text-white",
  fullstack: "bg-purple-600 text-white",
  ai: "bg-orange-500 text-white",
  custom: "bg-green-600 text-white",
};

function VariantCard({
  variant,
  onDuplicate,
  onDelete,
  onRename,
  recommended,
}: {
  variant: ResumeVariant;
  onDuplicate: () => void;
  onDelete: () => void;
  onRename: (name: string) => void;
  recommended?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(variant.name);
  const [expanded, setExpanded] = useState(false);

  const skills = (() => {
    const s = (variant.content as Record<string, unknown>)?.skills;
    if (!s) return [];
    if (typeof s === "object" && s !== null && "all" in s) return (s as { all: string[] }).all.slice(0, 10);
    if (Array.isArray(s)) return (s as string[]).slice(0, 10);
    return [];
  })();

  const saveRename = () => {
    if (name.trim() && name !== variant.name) onRename(name.trim());
    setEditing(false);
  };

  return (
    <Card className={`relative ${recommended ? "ring-2 ring-blue-500" : ""}`}>
      {recommended && (
        <div className="absolute -top-2 -right-2 bg-blue-500 text-white text-xs font-bold px-2 py-0.5 rounded-full flex items-center gap-1">
          <Star className="h-3 w-3" /> Best Match
        </div>
      )}
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <Badge className={TYPE_COLORS[variant.variant_type]}>{variant.variant_type}</Badge>
            {editing ? (
              <Input
                value={name}
                onChange={e => setName(e.target.value)}
                onBlur={saveRename}
                onKeyDown={e => { if (e.key === "Enter") saveRename(); if (e.key === "Escape") setEditing(false); }}
                className="h-6 text-sm"
                autoFocus
              />
            ) : (
              <span
                className="font-semibold truncate cursor-pointer hover:text-blue-600"
                onDoubleClick={() => setEditing(true)}
                title="Double-click to rename"
              >
                {variant.name}
              </span>
            )}
          </div>
          <div className="flex gap-1 ml-2 shrink-0">
            <Button size="sm" variant="ghost" onClick={onDuplicate} className="h-7 w-7 p-0">
              <Copy className="h-3.5 w-3.5" />
            </Button>
            <Button size="sm" variant="ghost" onClick={onDelete} className="h-7 w-7 p-0 text-red-500 hover:text-red-700">
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {variant.description && (
          <p className="text-xs text-muted-foreground mb-2">{variant.description}</p>
        )}
        {skills.length > 0 && (
          <div>
            <button
              className="flex items-center gap-1 text-xs text-muted-foreground mb-1"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
              {skills.length} skills
            </button>
            {expanded && (
              <div className="flex flex-wrap gap-1 mt-1">
                {skills.map(s => (
                  <Badge key={s} variant="outline" className="text-xs">{s}</Badge>
                ))}
              </div>
            )}
          </div>
        )}
        {variant.created_at && (
          <p className="text-xs text-muted-foreground mt-2">
            Created {new Date(variant.created_at).toLocaleDateString()}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default function VariantsPage() {
  const [variants, setVariants] = useState<ResumeVariant[]>([]);
  const [savedJDs, setSavedJDs] = useState<JobDescriptionListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState<VariantType>("custom");
  const [newDesc, setNewDesc] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  // Recommend state
  const [recommendJdId, setRecommendJdId] = useState("");
  const [recommendText, setRecommendText] = useState("");
  const [recommendResult, setRecommendResult] = useState<{ id: number; name: string; score: number }[] | null>(null);
  const [recommendedId, setRecommendedId] = useState<number | null>(null);
  const [recommending, setRecommending] = useState(false);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [v, j] = await Promise.all([variantsApi.list(), jdApi.list()]);
      setVariants(v);
      setSavedJDs(j);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };
  useEffect(() => { loadAll(); }, []);

  const handleCreate = async () => {
    if (!newName.trim()) { toast({ title: "Name required", variant: "destructive" }); return; }
    setCreating(true);
    try {
      await variantsApi.create({ name: newName.trim(), variant_type: newType, description: newDesc });
      toast({ title: "Variant created" });
      setNewName(""); setNewDesc(""); setShowCreate(false);
      await loadAll();
    } catch (err: unknown) {
      toast({ title: "Failed to create", description: err instanceof Error ? err.message : "", variant: "destructive" });
    } finally { setCreating(false); }
  };

  const handleDuplicate = async (id: number) => {
    try {
      await variantsApi.duplicate(id);
      toast({ title: "Variant duplicated" });
      await loadAll();
    } catch { toast({ title: "Duplication failed", variant: "destructive" }); }
  };

  const handleDelete = async (id: number) => {
    try {
      await variantsApi.delete(id);
      toast({ title: "Variant deleted" });
      await loadAll();
    } catch { toast({ title: "Delete failed", variant: "destructive" }); }
  };

  const handleRename = async (id: number, name: string) => {
    try {
      await variantsApi.update(id, { name });
      await loadAll();
    } catch { toast({ title: "Rename failed", variant: "destructive" }); }
  };

  const handleRecommend = async () => {
    if (!recommendJdId && !recommendText.trim()) {
      toast({ title: "Select or paste a JD", variant: "destructive" }); return;
    }
    setRecommending(true);
    setRecommendResult(null);
    setRecommendedId(null);
    try {
      const result = await variantsApi.recommend({
        jd_id: recommendJdId ? parseInt(recommendJdId) : undefined,
        jd_text: recommendJdId ? undefined : recommendText,
      });
      setRecommendResult(result.all_scores);
      setRecommendedId(result.recommended.id);
      toast({ title: `Best match: ${result.recommended.name} (${result.match_score.toFixed(0)}%)` });
    } catch (err: unknown) {
      toast({ title: "Recommendation failed", description: err instanceof Error ? err.message : "", variant: "destructive" });
    } finally { setRecommending(false); }
  };

  return (
    <div className="p-8 space-y-8 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Resume Variants</h1>
          <p className="text-muted-foreground mt-1">Manage multiple resume versions for different roles</p>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)}>
          <Plus className="h-4 w-4 mr-2" /> New Variant
        </Button>
      </div>

      {showCreate && (
        <Card>
          <CardHeader><CardTitle className="text-base">Create New Variant</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label>Variant Name</Label>
                <Input placeholder="e.g. Backend Resume 2024" value={newName} onChange={e => setNewName(e.target.value)} />
              </div>
              <div>
                <Label>Type</Label>
                <Select value={newType} onValueChange={v => setNewType(v as VariantType)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {VARIANT_TYPES.map(t => (
                      <SelectItem key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label>Description (optional)</Label>
              <Input placeholder="e.g. Tailored for fintech backend roles" value={newDesc} onChange={e => setNewDesc(e.target.value)} />
            </div>
            <div className="flex gap-2">
              <Button onClick={handleCreate} disabled={creating}>
                {creating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Plus className="h-4 w-4 mr-2" />}
                Create
              </Button>
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle className="text-base">Find Best Variant for a JD</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label>Select saved JD</Label>
              <Select value={recommendJdId} onValueChange={setRecommendJdId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a job description..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">None (use pasted text)</SelectItem>
                  {savedJDs.map(j => (
                    <SelectItem key={j.id} value={String(j.id)}>{j.title} — {j.company}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Or paste JD text</Label>
              <textarea
                className="w-full border rounded-md px-3 py-2 text-sm min-h-[70px] resize-none"
                placeholder="Paste job description here..."
                value={recommendText}
                onChange={e => setRecommendText(e.target.value)}
              />
            </div>
          </div>
          <Button onClick={handleRecommend} disabled={recommending || variants.length === 0}>
            {recommending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Star className="h-4 w-4 mr-2" />}
            Recommend Best Variant
          </Button>
          {recommendResult && (
            <div className="mt-2 space-y-2">
              {recommendResult.map(r => (
                <div key={r.id} className={`flex items-center justify-between p-2 rounded-lg border ${r.id === recommendedId ? "bg-blue-50 border-blue-300" : "bg-gray-50"}`}>
                  <span className="text-sm font-medium">{r.name}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-20 bg-gray-200 rounded-full h-2">
                      <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${r.score}%` }} />
                    </div>
                    <span className="text-sm font-bold text-blue-700">{r.score.toFixed(0)}%</span>
                    {r.id === recommendedId && <Star className="h-4 w-4 text-blue-500" />}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading variants...
        </div>
      ) : variants.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Files className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p>No variants yet. Create one to get started.</p>
          <p className="text-xs mt-1">Tip: Run the Optimizer first, then save the result as a variant.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {variants.map(v => (
            <VariantCard
              key={v.id}
              variant={v}
              recommended={v.id === recommendedId}
              onDuplicate={() => handleDuplicate(v.id)}
              onDelete={() => handleDelete(v.id)}
              onRename={name => handleRename(v.id, name)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

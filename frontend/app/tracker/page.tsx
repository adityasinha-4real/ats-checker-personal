"use client";
import { useEffect, useState } from "react";
import { applicationsApi, variantsApi, jdApi } from "@/lib/api";
import type { Application, ApplicationStatus, ApplicationAnalytics, ResumeVariant, JobDescriptionListItem } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Pencil, Trash2, BarChart2, List } from "lucide-react";

const STATUS_LABELS: Record<ApplicationStatus, string> = {
  applied: "Applied",
  phone_screen: "Phone Screen",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

const STATUS_COLORS: Record<ApplicationStatus, string> = {
  applied: "bg-blue-100 text-blue-800",
  phone_screen: "bg-yellow-100 text-yellow-800",
  interview: "bg-purple-100 text-purple-800",
  offer: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  withdrawn: "bg-slate-100 text-slate-600",
};

const ALL_STATUSES: ApplicationStatus[] = [
  "applied", "phone_screen", "interview", "offer", "rejected", "withdrawn",
];

const EMPTY_FORM = {
  company: "",
  role: "",
  date_applied: "",
  status: "applied" as ApplicationStatus,
  notes: "",
  variant_id: undefined as number | undefined,
  jd_id: undefined as number | undefined,
};

type Tab = "list" | "analytics";

export default function TrackerPage() {
  const [apps, setApps] = useState<Application[]>([]);
  const [analytics, setAnalytics] = useState<ApplicationAnalytics | null>(null);
  const [variants, setVariants] = useState<ResumeVariant[]>([]);
  const [jds, setJds] = useState<JobDescriptionListItem[]>([]);
  const [tab, setTab] = useState<Tab>("list");
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | "all">("all");
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const [appsData, analyticsData, variantsData, jdsData] = await Promise.all([
        applicationsApi.list(),
        applicationsApi.analytics(),
        variantsApi.list(),
        jdApi.list(),
      ]);
      setApps(appsData);
      setAnalytics(analyticsData);
      setVariants(variantsData);
      setJds(jdsData);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  };

  useEffect(() => { load(); }, []);

  const filtered = statusFilter === "all" ? apps : apps.filter((a) => a.status === statusFilter);

  const openCreate = () => {
    setEditId(null);
    setForm({ ...EMPTY_FORM });
    setModalOpen(true);
  };

  const openEdit = (a: Application) => {
    setEditId(a.id);
    setForm({
      company: a.company,
      role: a.role,
      date_applied: a.date_applied,
      status: a.status,
      notes: a.notes,
      variant_id: a.variant_id ?? undefined,
      jd_id: a.jd_id ?? undefined,
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    if (!form.company || !form.role) return;
    setLoading(true);
    try {
      if (editId) {
        await applicationsApi.update(editId, {
          ...form,
          variant_id: form.variant_id,
          jd_id: form.jd_id,
        });
      } else {
        await applicationsApi.create({
          ...form,
          variant_id: form.variant_id,
          jd_id: form.jd_id,
        });
      }
      setModalOpen(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this application?")) return;
    try {
      await applicationsApi.delete(id);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Application Tracker</h1>
          <p className="text-slate-500 text-sm mt-0.5">Track every application, status, and resume used</p>
        </div>
        <Button onClick={openCreate} className="gap-2">
          <Plus className="h-4 w-4" /> Add Application
        </Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded text-sm">
          {error}
        </div>
      )}

      {/* Tab bar */}
      <div className="flex gap-2 border-b border-slate-200 pb-0">
        {(["list", "analytics"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {t === "list" ? <List className="h-3.5 w-3.5" /> : <BarChart2 className="h-3.5 w-3.5" />}
            {t === "list" ? "Applications" : "Analytics"}
            {t === "list" && (
              <span className="ml-1 bg-slate-100 text-slate-600 rounded-full px-1.5 py-0.5 text-xs">
                {apps.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {tab === "list" && (
        <div className="space-y-4">
          {/* Status filter */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setStatusFilter("all")}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                statusFilter === "all" ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              All ({apps.length})
            </button>
            {ALL_STATUSES.map((s) => {
              const count = apps.filter((a) => a.status === s).length;
              if (count === 0) return null;
              return (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    statusFilter === s
                      ? "bg-slate-800 text-white"
                      : `${STATUS_COLORS[s]} hover:opacity-80`
                  }`}
                >
                  {STATUS_LABELS[s]} ({count})
                </button>
              );
            })}
          </div>

          {/* Table */}
          {filtered.length === 0 ? (
            <div className="text-center py-16 text-slate-400">
              <p className="text-lg">No applications yet</p>
              <p className="text-sm mt-1">Click "Add Application" to start tracking</p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-slate-600 uppercase text-xs">
                  <tr>
                    <th className="px-4 py-3 text-left">Company</th>
                    <th className="px-4 py-3 text-left">Role</th>
                    <th className="px-4 py-3 text-left">Date Applied</th>
                    <th className="px-4 py-3 text-left">Status</th>
                    <th className="px-4 py-3 text-left">Resume Variant</th>
                    <th className="px-4 py-3 text-left">Notes</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filtered.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3 font-medium">{a.company}</td>
                      <td className="px-4 py-3 text-slate-700">{a.role}</td>
                      <td className="px-4 py-3 text-slate-500">{a.date_applied || "—"}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[a.status]}`}>
                          {STATUS_LABELS[a.status]}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-500 text-xs">{a.variant_name || "—"}</td>
                      <td className="px-4 py-3 text-slate-400 text-xs max-w-xs truncate" title={a.notes}>
                        {a.notes || "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => openEdit(a)}
                            className="p-1.5 text-slate-400 hover:text-blue-600 transition-colors"
                            title="Edit"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => handleDelete(a.id)}
                            className="p-1.5 text-slate-400 hover:text-red-600 transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === "analytics" && analytics && (
        <div className="space-y-6">
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-xs text-slate-500 uppercase tracking-wide">Total</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{analytics.total_applications}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-xs text-slate-500 uppercase tracking-wide">Response Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{analytics.conversion_rates.response_rate}%</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-xs text-slate-500 uppercase tracking-wide">Interview Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{analytics.conversion_rates.interview_rate}%</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-xs text-slate-500 uppercase tracking-wide">Offer Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-green-600">{analytics.conversion_rates.offer_rate}%</p>
              </CardContent>
            </Card>
          </div>

          {/* By status breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold">Applications by Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {ALL_STATUSES.map((s) => {
                const count = analytics.by_status[s] || 0;
                const pct = analytics.total_applications > 0
                  ? Math.round((count / analytics.total_applications) * 100)
                  : 0;
                return (
                  <div key={s} className="flex items-center gap-3">
                    <span className="w-28 text-xs text-slate-600">{STATUS_LABELS[s]}</span>
                    <div className="flex-1 bg-slate-100 rounded-full h-2">
                      <div
                        className="h-2 rounded-full bg-blue-500 transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-8 text-xs text-slate-500 text-right">{count}</span>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* Variant performance */}
          {analytics.variant_performance.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold">Resume Performance</CardTitle>
              </CardHeader>
              <CardContent>
                <table className="w-full text-sm">
                  <thead className="text-xs text-slate-500 uppercase">
                    <tr>
                      <th className="text-left pb-2">Resume Variant</th>
                      <th className="text-right pb-2">Applications</th>
                      <th className="text-right pb-2">Interviews</th>
                      <th className="text-right pb-2">Offers</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {analytics.variant_performance.map((vp) => (
                      <tr key={vp.variant_id}>
                        <td className="py-2 text-slate-700">{vp.variant_name || `Variant #${vp.variant_id}`}</td>
                        <td className="py-2 text-right">{vp.applications}</td>
                        <td className="py-2 text-right text-purple-600">{vp.interviews}</td>
                        <td className="py-2 text-right text-green-600">{vp.offers}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}

          {/* Monthly trend */}
          {analytics.monthly_trend.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-semibold">Monthly Applications</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {analytics.monthly_trend.map((m) => (
                  <div key={m.month} className="flex flex-col items-center bg-slate-50 rounded px-3 py-2 min-w-[64px]">
                    <span className="text-lg font-bold text-blue-600">{m.count}</span>
                    <span className="text-xs text-slate-400">{m.month}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Add/Edit Modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editId ? "Edit Application" : "Add Application"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">Company *</label>
                <Input
                  value={form.company}
                  onChange={(e) => setForm({ ...form, company: e.target.value })}
                  placeholder="Google"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">Role *</label>
                <Input
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                  placeholder="Software Engineer"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">Date Applied</label>
                <Input
                  type="date"
                  value={form.date_applied}
                  onChange={(e) => setForm({ ...form, date_applied: e.target.value })}
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">Status</label>
                <Select
                  value={form.status}
                  onValueChange={(v) => setForm({ ...form, status: v as ApplicationStatus })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ALL_STATUSES.map((s) => (
                      <SelectItem key={s} value={s}>{STATUS_LABELS[s]}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">Resume Variant Used</label>
                <Select
                  value={form.variant_id?.toString() ?? "none"}
                  onValueChange={(v) => setForm({ ...form, variant_id: v === "none" ? undefined : parseInt(v) })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="None" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    {variants.map((v) => (
                      <SelectItem key={v.id} value={v.id.toString()}>{v.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">Job Description</label>
                <Select
                  value={form.jd_id?.toString() ?? "none"}
                  onValueChange={(v) => setForm({ ...form, jd_id: v === "none" ? undefined : parseInt(v) })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="None" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    {jds.map((jd) => (
                      <SelectItem key={jd.id} value={jd.id.toString()}>
                        {jd.company ? `${jd.company} — ${jd.title}` : jd.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-600">Notes</label>
              <Textarea
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                placeholder="Referral from John, online application, recruiter reached out..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={loading || !form.company || !form.role}>
              {loading ? "Saving…" : editId ? "Update" : "Add"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

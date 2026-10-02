import { useRef, useState } from "react";
import { api } from "../api/client";
import { Badge, Button, Modal } from "./ui";

/**
 * Generic "Bulk import" button + modal: download a blank template, upload
 * a filled-in .xlsx, see per-row results (created/skipped/error). Used
 * alongside every one-by-one create flow, never instead of it — see
 * backend/modules/bulk.py for what each `kind` actually does.
 */
export function BulkImportButton({ kind, label, onDone }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="secondary" onClick={() => setOpen(true)}>
        ⇪ {label || "Bulk import"}
      </Button>
      <BulkImportModal
        open={open}
        kind={kind}
        label={label}
        onClose={() => setOpen(false)}
        onDone={() => {
          onDone?.();
        }}
      />
    </>
  );
}

// A short, kind-specific tip shown above the generic instructions — only
// where the column headers alone don't make the expected convention
// obvious (the Password column is the main case: it's easy to misread as
// optional).
const KIND_HINTS = {
  enrollments:
    "Tip: set a real password for each student here — many clients just use the student's own phone number. They'll log in with your company code + their email + this password.",
};

function BulkImportModal({ open, kind, label, onClose, onDone }) {
  const fileRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  async function downloadTemplate() {
    setError("");
    try {
      const res = await api.get(`/bulk/${kind}/template`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${kind}_template.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message);
    }
  }

  async function upload(e) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Choose a filled-in .xlsx file first.");
      return;
    }
    setError("");
    setResult(null);
    setBusy(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post(`/bulk/${kind}`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(res.data);
      onDone?.();
    } catch (e2) {
      setError(e2.message);
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={`Bulk import — ${label || kind}`} wide>
      <div className="space-y-4">
        <div className="rounded-lg bg-ink-50 px-3.5 py-3 text-sm text-ink-600">
          1. Download the template below and fill it in (one row per item — the
          template's first two rows show the expected format).
          <br />
          2. Upload it here. Every row is applied; rows that fail are reported
          individually so you can fix just those and re-upload.
        </div>

        {KIND_HINTS[kind] && (
          <div className="rounded-lg bg-brand-50 px-3.5 py-3 text-sm text-brand-700">{KIND_HINTS[kind]}</div>
        )}

        <Button type="button" variant="secondary" onClick={downloadTemplate}>
          ⇩ Download template
        </Button>

        <form onSubmit={upload} className="flex items-center gap-2">
          <input
            ref={fileRef}
            type="file"
            accept=".xlsx"
            className="flex-1 rounded-lg border border-ink-200 px-3 py-2 text-sm"
          />
          <Button type="submit" disabled={busy}>
            {busy ? "Importing…" : "Import"}
          </Button>
        </form>

        {error && <div className="rounded-lg bg-danger-50 px-3.5 py-2.5 text-sm text-danger-700">{error}</div>}

        {result && (
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-ink-800">
              {result.total} row{result.total === 1 ? "" : "s"} processed
              <Badge variant="success">{result.ok} ok</Badge>
              {result.skipped > 0 && <Badge variant="neutral">{result.skipped} skipped</Badge>}
              {result.errors > 0 && <Badge variant="danger">{result.errors} error{result.errors === 1 ? "" : "s"}</Badge>}
            </div>
            <div className="mt-2 max-h-64 overflow-y-auto rounded-lg border border-ink-100">
              <table className="w-full text-xs">
                <tbody>
                  {result.rows.map((r) => (
                    <tr key={r.row} className="border-t border-ink-100 first:border-0">
                      <td className="whitespace-nowrap px-2.5 py-1.5 text-ink-400">Row {r.row}</td>
                      <td className="px-2.5 py-1.5">
                        <Badge variant={r.status === "ok" ? "success" : r.status === "skipped" ? "neutral" : "danger"}>
                          {r.status}
                        </Badge>
                      </td>
                      <td className="px-2.5 py-1.5 text-ink-700">{r.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div className="flex justify-end pt-1">
          <Button type="button" variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
}

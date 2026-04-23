/**
 * Download a generated exam as PDF or Word (teacher-only API).
 * @param {string} apiUrl
 * @param {number|string} examId
 * @param {"pdf"|"docx"} format
 * @param {string} token Bearer JWT
 * @returns {Promise<{ ok: true } | { ok: false, message: string }>}
 */
export async function downloadExamExport(apiUrl, examId, format, token) {
  if (!token || examId == null || examId === "") {
    return { ok: false, message: "Not signed in or no exam id." };
  }
  const fmt = format === "docx" ? "docx" : "pdf";
  const res = await fetch(
    `${apiUrl.replace(/\/$/, "")}/api/exams/${examId}/export?format=${fmt}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.ok) {
    let msg = `Download failed (${res.status})`;
    try {
      const data = await res.json();
      if (data.detail) {
        msg =
          typeof data.detail === "string"
            ? data.detail
            : Array.isArray(data.detail)
              ? data.detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
              : JSON.stringify(data.detail);
      }
    } catch {
      /* ignore */
    }
    return { ok: false, message: msg };
  }
  const blob = await res.blob();
  const cd = res.headers.get("Content-Disposition") || "";
  const match = cd.match(/filename="([^"]+)"/);
  const filename = match ? match[1] : `exam-${examId}.${fmt}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
  return { ok: true };
}

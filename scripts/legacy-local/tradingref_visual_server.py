import json
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
  import pikepdf  # type: ignore
  PIKEPDF_AVAILABLE = True
except Exception:
  pikepdf = None
  PIKEPDF_AVAILABLE = False

HOST = "127.0.0.1"
PORT = 8787
DATA_ENDPOINT = "https://data.tradingref.com/{date}.json"
DOWNLOAD_ROOT = Path("downloads")

ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/"
REVERSED_ALPHABET = ALPHABET[::-1]
TRANSLATION_TABLE = str.maketrans(REVERSED_ALPHABET, ALPHABET)

CACHE_LOCK = threading.Lock()
DATE_CACHE = {}

HTML_PAGE = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>TradingRef Visual Tester</title>
  <style>
    :root {
      --bg: #f2efe8;
      --panel: #fffaf0;
      --ink: #1e1a16;
      --muted: #6a5f56;
      --line: #d8ccb7;
      --accent: #0b6e4f;
      --accent-2: #f4b942;
      --danger: #9f2d2d;
      --mono: "JetBrains Mono", "Consolas", monospace;
      --serif: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Palatino, serif;
      --sans: "Trebuchet MS", "Segoe UI", Tahoma, sans-serif;
      --shadow: 0 10px 30px rgba(18, 12, 6, 0.12);
      --radius: 14px;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      color: var(--ink);
      font-family: var(--sans);
      background:
        radial-gradient(circle at 20% 10%, rgba(244, 185, 66, 0.2), transparent 40%),
        radial-gradient(circle at 80% 0%, rgba(11, 110, 79, 0.15), transparent 45%),
        linear-gradient(170deg, #f8f4ed, #ede6d9);
      min-height: 100vh;
    }

    .wrap {
      max-width: 1180px;
      margin: 24px auto;
      padding: 0 16px 30px;
    }

    .hero {
      border: 2px solid var(--line);
      border-radius: var(--radius);
      background: linear-gradient(120deg, rgba(255, 250, 240, 0.96), rgba(247, 240, 228, 0.96));
      box-shadow: var(--shadow);
      padding: 18px 20px;
      margin-bottom: 16px;
      animation: rise 380ms ease-out;
    }

    .hero h1 {
      margin: 0;
      font-family: var(--serif);
      font-size: clamp(1.4rem, 2.6vw, 2.1rem);
      letter-spacing: 0.02em;
      font-weight: 600;
    }

    .hero p {
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 0.98rem;
      line-height: 1.45;
    }

    .grid {
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 16px;
    }

    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      animation: rise 460ms ease-out;
    }

    .controls {
      padding: 14px;
      position: sticky;
      top: 12px;
      align-self: start;
    }

    .field {
      display: grid;
      gap: 6px;
      margin-bottom: 12px;
    }

    label {
      font-size: 0.85rem;
      color: var(--muted);
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    input, select, button, textarea {
      width: 100%;
      border-radius: 10px;
      border: 1px solid #cabaa1;
      padding: 10px 12px;
      font: inherit;
      background: #fffdf8;
      color: var(--ink);
    }

    input:focus, select:focus, textarea:focus {
      outline: 2px solid rgba(11, 110, 79, 0.2);
      border-color: var(--accent);
    }

    .btn-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 4px;
    }

    button {
      cursor: pointer;
      font-weight: 700;
      transition: transform 120ms ease, background-color 120ms ease;
    }

    button:hover {
      transform: translateY(-1px);
    }

    .btn-primary {
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
    }

    .btn-secondary {
      background: #f8efdb;
      color: #453522;
    }

    .btn-danger {
      background: #fce4e4;
      border-color: #e4b6b6;
      color: var(--danger);
    }

    .status {
      margin-top: 10px;
      border: 1px dashed #cdbfa8;
      border-radius: 10px;
      padding: 10px;
      background: #fffcf4;
      color: #53473a;
      min-height: 54px;
      white-space: pre-wrap;
      font-size: 0.9rem;
      line-height: 1.4;
    }

    .status.busy {
      border-style: solid;
      border-color: #9db9ad;
      background: #eef8f2;
      color: #1f5e44;
      position: relative;
      padding-left: 38px;
    }

    .status.busy::before {
      content: "";
      width: 14px;
      height: 14px;
      border: 2px solid #8ab8a1;
      border-top-color: #0b6e4f;
      border-radius: 50%;
      position: absolute;
      left: 12px;
      top: 50%;
      transform: translateY(-50%);
      animation: spin 0.85s linear infinite;
    }

    .content {
      padding: 14px;
      display: grid;
      gap: 10px;
    }

    .meta {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
    }

    .pill {
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fffbf1;
      padding: 10px;
    }

    .pill small {
      display: block;
      color: var(--muted);
      font-size: 0.73rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 5px;
    }

    .pill div {
      font-family: var(--mono);
      font-size: 0.83rem;
      word-break: break-word;
    }

    .lists {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }

    .panel {
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fffdf8;
      min-height: 260px;
      display: grid;
      grid-template-rows: auto 1fr;
    }

    .panel h3 {
      margin: 0;
      padding: 10px;
      border-bottom: 1px solid var(--line);
      font-size: 0.92rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #584d42;
    }

    .url-list {
      margin: 0;
      padding: 8px 10px 12px;
      list-style: none;
      overflow: auto;
      max-height: 460px;
      font-family: var(--mono);
      font-size: 0.76rem;
      line-height: 1.38;
    }

    .url-list li { margin-bottom: 8px; }

    .url-list a {
      color: #0c4f8a;
      text-decoration: none;
      word-break: break-all;
    }

    .url-list a:hover { text-decoration: underline; }

    .download-report {
      font-family: var(--mono);
      font-size: 0.82rem;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fffdf8;
      padding: 10px;
      min-height: 68px;
      white-space: pre-wrap;
    }

    .hint-box {
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fffdf8;
      padding: 10px;
      min-height: 68px;
      font-family: var(--mono);
      font-size: 0.8rem;
      white-space: pre-wrap;
      line-height: 1.4;
    }

    .footer-note {
      margin-top: 8px;
      color: var(--muted);
      font-size: 0.82rem;
    }

    @keyframes rise {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @keyframes spin {
      from { transform: translateY(-50%) rotate(0deg); }
      to { transform: translateY(-50%) rotate(360deg); }
    }

    @media (max-width: 980px) {
      .grid { grid-template-columns: 1fr; }
      .controls { position: static; }
      .meta { grid-template-columns: 1fr 1fr; }
      .lists { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"hero\">
      <h1>TradingRef Visual Workflow Tester</h1>
      <p>Pick a date, load the dataset from TradingRef, then select language/newspaper/edition. The server performs download, deobfuscation, URL resolution, and optional local fetch of files.</p>
    </section>

    <div class=\"grid\">
      <section class=\"card controls\">
        <div class=\"field\">
          <label for=\"dateInput\">Date (YYYYMMDD)</label>
          <input id=\"dateInput\" type=\"text\" placeholder=\"20260330\" maxlength=\"8\">
        </div>
        <div class=\"btn-row\">
          <button id=\"loadDateBtn\" class=\"btn-primary\">Load Date</button>
          <button id=\"refreshBtn\" class=\"btn-secondary\">Refresh Entry</button>
        </div>

        <div class=\"field\" style=\"margin-top:12px;\">
          <label for=\"languageSelect\">Language</label>
          <select id=\"languageSelect\" disabled>
            <option value=\"\">Load a date first</option>
          </select>
        </div>

        <div class=\"field\">
          <label for=\"newspaperSelect\">Newspaper</label>
          <select id=\"newspaperSelect\" disabled>
            <option value=\"\">Choose language first</option>
          </select>
        </div>

        <div class=\"field\">
          <label for=\"editionSelect\">Edition</label>
          <select id=\"editionSelect\" disabled>
            <option value=\"\">Choose newspaper first</option>
          </select>
        </div>

        <div class=\"btn-row\">
          <button id=\"fetchEntryBtn\" class=\"btn-primary\" disabled>Fetch Entry Data</button>
          <button id=\"downloadAssetsBtn\" class=\"btn-danger\" disabled>Fetch All Files</button>
        </div>

        <div class=\"status\" id=\"statusBox\">Waiting for input.</div>
      </section>

      <section class=\"card content\">
        <div class=\"meta\">
          <div class=\"pill\"><small>Date</small><div id=\"metaDate\">-</div></div>
          <div class=\"pill\"><small>Type</small><div id=\"metaType\">-</div></div>
          <div class=\"pill\"><small>Pages</small><div id=\"metaPages\">-</div></div>
          <div class=\"pill\"><small>Prefix</small><div id=\"metaPrefix\">-</div></div>
        </div>

        <div class=\"lists\">
          <div class=\"panel\">
            <h3>Direct URLs</h3>
            <ul class=\"url-list\" id=\"directList\"></ul>
          </div>
          <div class=\"panel\">
            <h3>Proxy URLs</h3>
            <ul class=\"url-list\" id=\"proxyList\"></ul>
          </div>
        </div>

        <div class=\"hint-box\" id=\"passwordHints\">Password hints will appear here for pdfl/dfl entries.</div>

        <div class=\"download-report\" id=\"downloadReport\">No download activity yet.</div>
        <div class=\"footer-note\">Files are saved under the local downloads folder created by the server script.</div>
      </section>
    </div>
  </div>

  <script>
    const state = {
      date: "",
      language: "",
      newspaper: "",
      edition: "",
      entry: null,
      busyTimer: null,
      busyLabel: "",
    };

    const el = {
      dateInput: document.getElementById("dateInput"),
      loadDateBtn: document.getElementById("loadDateBtn"),
      refreshBtn: document.getElementById("refreshBtn"),
      languageSelect: document.getElementById("languageSelect"),
      newspaperSelect: document.getElementById("newspaperSelect"),
      editionSelect: document.getElementById("editionSelect"),
      fetchEntryBtn: document.getElementById("fetchEntryBtn"),
      downloadAssetsBtn: document.getElementById("downloadAssetsBtn"),
      statusBox: document.getElementById("statusBox"),
      metaDate: document.getElementById("metaDate"),
      metaType: document.getElementById("metaType"),
      metaPages: document.getElementById("metaPages"),
      metaPrefix: document.getElementById("metaPrefix"),
      directList: document.getElementById("directList"),
      proxyList: document.getElementById("proxyList"),
      passwordHints: document.getElementById("passwordHints"),
      downloadReport: document.getElementById("downloadReport"),
    };

    function setStatus(text) {
      el.statusBox.textContent = text;
    }

    function syncControls() {
      const hasDate = Boolean(state.date);
      const hasLanguage = Boolean(state.language);
      const hasNewspaper = Boolean(state.newspaper);
      const hasEdition = Boolean(state.edition);
      const canFetchEntry = hasDate && hasLanguage && hasNewspaper && hasEdition;
      const canDownload = Boolean(state.entry && state.entry.direct_urls && state.entry.direct_urls.length);

      el.dateInput.disabled = false;
      el.loadDateBtn.disabled = false;
      el.refreshBtn.disabled = !canFetchEntry;
      el.languageSelect.disabled = !hasDate;
      el.newspaperSelect.disabled = !hasLanguage;
      el.editionSelect.disabled = !hasNewspaper;
      el.fetchEntryBtn.disabled = !canFetchEntry;
      el.downloadAssetsBtn.disabled = !canDownload;
    }

    function lockControls() {
      el.dateInput.disabled = true;
      el.loadDateBtn.disabled = true;
      el.refreshBtn.disabled = true;
      el.languageSelect.disabled = true;
      el.newspaperSelect.disabled = true;
      el.editionSelect.disabled = true;
      el.fetchEntryBtn.disabled = true;
      el.downloadAssetsBtn.disabled = true;
    }

    function startBusy(label) {
      lockControls();
      state.busyLabel = label;
      el.statusBox.classList.add("busy");
      if (state.busyTimer) {
        clearInterval(state.busyTimer);
      }
      let tick = 0;
      setStatus(`${label}...`);
      state.busyTimer = setInterval(() => {
        tick = (tick + 1) % 4;
        setStatus(`${label}${".".repeat(tick + 1)}`);
      }, 350);
    }

    function stopBusy(finalMessage) {
      if (state.busyTimer) {
        clearInterval(state.busyTimer);
        state.busyTimer = null;
      }
      el.statusBox.classList.remove("busy");
      syncControls();
      setStatus(finalMessage);
    }

    function setSelectOptions(select, values, emptyText) {
      select.innerHTML = "";
      const first = document.createElement("option");
      first.value = "";
      first.textContent = emptyText;
      select.appendChild(first);
      for (const value of values) {
        const o = document.createElement("option");
        o.value = value;
        o.textContent = value;
        select.appendChild(o);
      }
    }

    function clearEntryPanels() {
      state.entry = null;
      el.metaType.textContent = "-";
      el.metaPages.textContent = "-";
      el.metaPrefix.textContent = "-";
      el.directList.innerHTML = "";
      el.proxyList.innerHTML = "";
      el.passwordHints.textContent = "Password hints will appear here for pdfl/dfl entries.";
      syncControls();
    }

    function renderPasswordHints(entry) {
      const hints = entry.password_hints || [];
      if (!entry.requires_password) {
        el.passwordHints.textContent = "This entry does not require PDF password hints.";
        return;
      }

      if (!hints.length) {
        el.passwordHints.textContent = "Locked PDF entry detected, but no filename-based password hints were generated.";
        return;
      }

      const lines = [
        `Locked PDF mode (${entry.type_original || entry.type} -> ${entry.type}).`,
        `Hints found: ${hints.length}`,
        "",
      ];

      hints.slice(0, 20).forEach((item, idx) => {
        lines.push(`${idx + 1}. ${item.file}  |  password: ${item.password}`);
      });
      if (hints.length > 20) {
        lines.push(`... and ${hints.length - 20} more`);
      }

      el.passwordHints.textContent = lines.join("\\n");
    }

    function renderUrlList(target, urls) {
      target.innerHTML = "";
      if (!urls || urls.length === 0) {
        const li = document.createElement("li");
        li.textContent = "No URLs available.";
        target.appendChild(li);
        return;
      }
      urls.forEach((url, idx) => {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = url;
        a.target = "_blank";
        a.rel = "noreferrer";
        a.textContent = `${idx + 1}. ${url}`;
        li.appendChild(a);
        target.appendChild(li);
      });
    }

    async function api(path, options = {}) {
      const res = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options,
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        throw new Error(data.error || `HTTP ${res.status}`);
      }
      return data;
    }

    async function loadDate() {
      const rawDate = el.dateInput.value.trim();
      if (!/^\\d{8}$/.test(rawDate)) {
        setStatus("Date must be 8 digits in YYYYMMDD format.");
        return;
      }

      startBusy(`Loading ${rawDate} from TradingRef`);
      clearEntryPanels();

      try {
        const data = await api("/api/load-date", {
          method: "POST",
          body: JSON.stringify({ date: rawDate }),
        });

        state.date = rawDate;
        state.language = "";
        state.newspaper = "";
        state.edition = "";

        el.metaDate.textContent = rawDate;

        setSelectOptions(el.languageSelect, data.languages, "Choose language");
        el.languageSelect.disabled = false;

        setSelectOptions(el.newspaperSelect, [], "Choose language first");
        setSelectOptions(el.editionSelect, [], "Choose newspaper first");
        el.newspaperSelect.disabled = true;
        el.editionSelect.disabled = true;

        stopBusy(`Loaded ${rawDate}. Languages: ${data.languages.length}.`);
      } catch (err) {
        stopBusy(`Load failed: ${err.message}`);
      }
    }

    async function onLanguageChange() {
      state.language = el.languageSelect.value;
      state.newspaper = "";
      state.edition = "";
      clearEntryPanels();

      if (!state.language) {
        setSelectOptions(el.newspaperSelect, [], "Choose language first");
        setSelectOptions(el.editionSelect, [], "Choose newspaper first");
        el.newspaperSelect.disabled = true;
        el.editionSelect.disabled = true;
        return;
      }

      startBusy("Loading newspapers");
      try {
        const q = new URLSearchParams({ date: state.date, language: state.language });
        const data = await api(`/api/newspapers?${q.toString()}`);
        setSelectOptions(el.newspaperSelect, data.newspapers, "Choose newspaper");
        el.newspaperSelect.disabled = false;
        setSelectOptions(el.editionSelect, [], "Choose newspaper first");
        el.editionSelect.disabled = true;
        stopBusy(`Loaded newspapers for ${state.language}.`);
      } catch (err) {
        stopBusy(`Failed loading newspapers: ${err.message}`);
      }
    }

    async function onNewspaperChange() {
      state.newspaper = el.newspaperSelect.value;
      state.edition = "";
      clearEntryPanels();

      if (!state.newspaper) {
        setSelectOptions(el.editionSelect, [], "Choose newspaper first");
        el.editionSelect.disabled = true;
        return;
      }

      startBusy("Loading editions");
      try {
        const q = new URLSearchParams({
          date: state.date,
          language: state.language,
          newspaper: state.newspaper,
        });
        const data = await api(`/api/editions?${q.toString()}`);
        setSelectOptions(el.editionSelect, data.editions, "Choose edition");
        el.editionSelect.disabled = false;
        stopBusy(`Loaded editions for ${state.newspaper}.`);
      } catch (err) {
        stopBusy(`Failed loading editions: ${err.message}`);
      }
    }

    function onEditionChange() {
      state.edition = el.editionSelect.value;
      clearEntryPanels();
      if (state.edition) {
        setStatus("Edition selected. Click Fetch Entry Data.");
      }
    }

    async function fetchEntry() {
      if (!(state.date && state.language && state.newspaper && state.edition)) {
        setStatus("Select date, language, newspaper, and edition first.");
        return;
      }

      startBusy("Fetching entry data");
      try {
        const q = new URLSearchParams({
          date: state.date,
          language: state.language,
          newspaper: state.newspaper,
          edition: state.edition,
        });
        const data = await api(`/api/entry?${q.toString()}`);
        state.entry = data.entry;

        el.metaType.textContent = data.entry.type || "-";
        el.metaPages.textContent = String(data.entry.pages_count ?? 0);
        el.metaPrefix.textContent = data.entry.prefix || "-";

        renderUrlList(el.directList, data.entry.direct_urls || []);
        renderUrlList(el.proxyList, data.entry.proxy_urls || []);
        renderPasswordHints(data.entry);

        if (data.entry.requires_password) {
          const hintCount = (data.entry.password_hints || []).length;
          stopBusy(`Entry loaded: ${data.entry.type} with ${data.entry.pages_count} page(s). Locked PDF mode. Password hints: ${hintCount}.`);
        } else {
          stopBusy(`Entry loaded: ${data.entry.type} with ${data.entry.pages_count} page(s).`);
        }
      } catch (err) {
        stopBusy(`Entry fetch failed: ${err.message}`);
      }
    }

    async function fetchAllFiles() {
      if (!state.entry) {
        setStatus("Load an entry first.");
        return;
      }

      startBusy("Downloading files to local folder");
      el.downloadReport.textContent = "Downloading...";

      try {
        const data = await api("/api/fetch-assets", {
          method: "POST",
          body: JSON.stringify({
            date: state.date,
            language: state.language,
            newspaper: state.newspaper,
            edition: state.edition,
          }),
        });

        const lines = [
          `Saved folder: ${data.output_dir}`,
          `Attempted: ${data.total_urls}`,
          `Saved: ${data.saved_count}`,
          `Failed: ${data.failed_count}`,
        ];
        if (state.entry && state.entry.requires_password) {
          lines.push(`pikepdf installed: ${data.pikepdf_available ? "yes" : "no"}`);
          lines.push(`Unlock attempts: ${data.unlock_attempts}`);
          lines.push(`Unlocked PDFs: ${data.unlocked_pdf_count}`);
          if (data.unlock_failures && data.unlock_failures.length) {
            lines.push("Unlock failures:");
            data.unlock_failures.slice(0, 10).forEach((item) => lines.push(`- ${item}`));
            if (data.unlock_failures.length > 10) {
              lines.push(`... and ${data.unlock_failures.length - 10} more`);
            }
          }
        }
        if (data.failures && data.failures.length) {
          lines.push("Failed URLs:");
          data.failures.slice(0, 10).forEach((item) => lines.push(`- ${item}`));
          if (data.failures.length > 10) {
            lines.push(`... and ${data.failures.length - 10} more`);
          }
        }

        el.downloadReport.textContent = lines.join("\\n");
        stopBusy("Download job complete.");
      } catch (err) {
        el.downloadReport.textContent = "Download failed.";
        stopBusy(`Download failed: ${err.message}`);
      }
    }

    function prefillToday() {
      const d = new Date();
      const yyyy = d.getFullYear();
      const mm = String(d.getMonth() + 1).padStart(2, "0");
      const dd = String(d.getDate()).padStart(2, "0");
      el.dateInput.value = `${yyyy}${mm}${dd}`;
    }

    el.loadDateBtn.addEventListener("click", loadDate);
    el.refreshBtn.addEventListener("click", fetchEntry);
    el.languageSelect.addEventListener("change", onLanguageChange);
    el.newspaperSelect.addEventListener("change", onNewspaperChange);
    el.editionSelect.addEventListener("change", onEditionChange);
    el.fetchEntryBtn.addEventListener("click", fetchEntry);
    el.downloadAssetsBtn.addEventListener("click", fetchAllFiles);

    prefillToday();
    syncControls();
  </script>
</body>
</html>
"""


def sanitize_path_component(value: str) -> str:
    clean = re.sub(r"[\\/:*?\"<>|]", "_", value.strip())
    clean = re.sub(r"\s+", " ", clean)
    return clean[:120] if clean else "unknown"


def deobfuscate(value: str) -> str:
    return value.translate(TRANSLATION_TABLE)


def parse_decoded(decoded: str) -> dict:
    parts = decoded.split("q!", 2)
    if len(parts) < 3:
        return {
            "raw_decoded": decoded,
            "type": "",
            "prefix": "",
            "pages": [],
            "pages_count": 0,
        }

    content_type, prefix, suffix = parts
    pages = [p.strip() for p in suffix.split("m%") if p.strip()]

    return {
        "raw_decoded": decoded,
        "type": content_type,
        "prefix": prefix,
        "pages": pages,
        "pages_count": len(pages),
    }


def join_prefix_and_page(prefix: str, page: str) -> str:
    prefix = (prefix or "").strip()
    page = (page or "").strip()

    if not page:
        return prefix
    if page.startswith("http://") or page.startswith("https://"):
        return page
    if prefix.endswith("/"):
        return f"{prefix}{page}"
    return f"{prefix}/{page}"


def to_image_proxy(url: str) -> str:
    return (
        "https://images.weserv.nl/?url="
        + urllib.parse.quote(url, safe="")
        + "&maxage=1d&output=jpg&q=50"
    )


def infer_pdf_password_hints(pages: list[str]) -> list[dict]:
    hints = []
    for page in pages:
        name = os.path.basename((page or "").strip())
        if not name:
            continue
        if name.lower().endswith(".pdf") and len(name) >= 10:
            hints.append({
                "file": name,
                "password": name[:10],
            })
    return hints


def resolve_entry(entry: dict) -> dict:
    content_type_raw = (entry.get("type") or "").strip().lower()
    content_type = "pdfl" if content_type_raw == "dfl" else content_type_raw
    prefix = (entry.get("prefix") or "").strip()
    pages = entry.get("pages") or []

    direct_urls = [join_prefix_and_page(prefix, p) for p in pages]
    proxy_urls = [to_image_proxy(u) for u in direct_urls] if content_type in {"image", "pdf"} else []
    requires_password = content_type == "pdfl"
    password_hints = infer_pdf_password_hints(pages) if requires_password else []

    out = dict(entry)
    out["type_original"] = (entry.get("type") or "").strip()
    out["type"] = content_type
    out["direct_urls"] = direct_urls
    out["proxy_urls"] = proxy_urls
    out["requires_password"] = requires_password
    out["password_hints"] = password_hints
    return out


def build_resolved_for_date(raw_data: dict) -> dict:
    result = {}
    for language, newspapers in raw_data.items():
        result[language] = {}
        for newspaper, editions in newspapers.items():
            result[language][newspaper] = {}
            for edition, obfuscated in editions.items():
                decoded = deobfuscate(obfuscated)
                parsed = parse_decoded(decoded)
                resolved = resolve_entry(parsed)
                result[language][newspaper][edition] = resolved
    return result


def fetch_raw_json(date_str: str) -> dict:
    url = DATA_ENDPOINT.format(date=date_str)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        body = resp.read()
    return json.loads(body.decode("utf-8"))


def ensure_date_loaded(date_str: str) -> dict:
    with CACHE_LOCK:
        if date_str in DATE_CACHE:
            return DATE_CACHE[date_str]

    raw_data = fetch_raw_json(date_str)
    resolved = build_resolved_for_date(raw_data)

    payload = {
        "date": date_str,
        "raw": raw_data,
        "resolved": resolved,
        "loaded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    with CACHE_LOCK:
        DATE_CACHE[date_str] = payload

    return payload


def get_entry(date: str, language: str, newspaper: str, edition: str) -> dict:
    payload = ensure_date_loaded(date)
    return payload["resolved"][language][newspaper][edition]


def write_json(handler: BaseHTTPRequestHandler, status: int, payload: dict):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def download_to_file(url: str, out_path: Path):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = resp.read()
    out_path.write_bytes(data)


def try_unlock_pdf(input_path: Path, password: str, output_path: Path) -> tuple[bool, str]:
    if not PIKEPDF_AVAILABLE:
      return False, "pikepdf not installed"
    if not password:
      return False, "missing password"
    try:
      with pikepdf.open(str(input_path), password=password) as pdf:
        pdf.save(str(output_path))
      return True, "ok"
    except Exception as exc:
      return False, str(exc)


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        q = urllib.parse.parse_qs(parsed.query)

        try:
            if path == "/":
                html = HTML_PAGE.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
                return

            if path == "/api/newspapers":
                date = q.get("date", [""])[0]
                language = q.get("language", [""])[0]
                if not date or not language:
                    write_json(self, 400, {"ok": False, "error": "date and language are required"})
                    return

                payload = ensure_date_loaded(date)
                newspapers = sorted(payload["resolved"][language].keys())
                write_json(self, 200, {"ok": True, "newspapers": newspapers})
                return

            if path == "/api/editions":
                date = q.get("date", [""])[0]
                language = q.get("language", [""])[0]
                newspaper = q.get("newspaper", [""])[0]
                if not date or not language or not newspaper:
                    write_json(self, 400, {"ok": False, "error": "date, language, newspaper are required"})
                    return

                payload = ensure_date_loaded(date)
                editions = sorted(payload["resolved"][language][newspaper].keys())
                write_json(self, 200, {"ok": True, "editions": editions})
                return

            if path == "/api/entry":
                date = q.get("date", [""])[0]
                language = q.get("language", [""])[0]
                newspaper = q.get("newspaper", [""])[0]
                edition = q.get("edition", [""])[0]
                if not date or not language or not newspaper or not edition:
                    write_json(self, 400, {"ok": False, "error": "date, language, newspaper, edition are required"})
                    return

                entry = get_entry(date, language, newspaper, edition)
                write_json(self, 200, {"ok": True, "entry": entry})
                return

            if path == "/api/ping":
                write_json(self, 200, {"ok": True, "status": "alive"})
                return

            write_json(self, 404, {"ok": False, "error": "not found"})
        except KeyError as exc:
            write_json(self, 404, {"ok": False, "error": f"not found in dataset: {exc}"})
        except urllib.error.HTTPError as exc:
            write_json(self, 502, {"ok": False, "error": f"upstream error: {exc.code}"})
        except Exception as exc:
            write_json(self, 500, {"ok": False, "error": str(exc)})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            body = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
            data = json.loads(body.decode("utf-8") or "{}")

            if path == "/api/load-date":
                date = str(data.get("date", "")).strip()
                if not re.fullmatch(r"\d{8}", date):
                    write_json(self, 400, {"ok": False, "error": "date must be YYYYMMDD"})
                    return

                payload = ensure_date_loaded(date)
                languages = sorted(payload["resolved"].keys())
                write_json(
                    self,
                    200,
                    {
                        "ok": True,
                        "date": date,
                        "languages": languages,
                        "language_count": len(languages),
                    },
                )
                return

            if path == "/api/fetch-assets":
                date = str(data.get("date", "")).strip()
                language = str(data.get("language", "")).strip()
                newspaper = str(data.get("newspaper", "")).strip()
                edition = str(data.get("edition", "")).strip()

                if not (date and language and newspaper and edition):
                    write_json(self, 400, {"ok": False, "error": "date, language, newspaper, edition are required"})
                    return

                entry = get_entry(date, language, newspaper, edition)
                urls = entry.get("direct_urls") or []
                if not urls:
                    write_json(self, 400, {"ok": False, "error": "entry has no direct_urls to download"})
                    return

                folder = DOWNLOAD_ROOT / sanitize_path_component(date) / sanitize_path_component(language) / sanitize_path_component(newspaper) / sanitize_path_component(edition)
                folder.mkdir(parents=True, exist_ok=True)

                failures = []
                saved_count = 0
                unlock_attempts = 0
                unlocked_pdf_count = 0
                unlock_failures = []
                password_map = {
                    item.get("file", ""): item.get("password", "")
                    for item in (entry.get("password_hints") or [])
                    if item.get("file")
                }

                for idx, url in enumerate(urls, start=1):
                    parsed_url = urllib.parse.urlparse(url)
                    name = os.path.basename(parsed_url.path) or f"file_{idx}"
                    safe_name = sanitize_path_component(name)
                    out_path = folder / safe_name
                    try:
                        download_to_file(url, out_path)
                        saved_count += 1
                    except Exception:
                        proxy_urls = entry.get("proxy_urls") or []
                        fallback = proxy_urls[idx - 1] if idx - 1 < len(proxy_urls) else None
                        if fallback:
                            try:
                                download_to_file(fallback, out_path)
                                saved_count += 1
                            except Exception:
                              failures.append(url)
                              continue
                        else:
                            failures.append(url)
                            continue

                    if entry.get("requires_password") and safe_name.lower().endswith(".pdf"):
                        password = password_map.get(safe_name, "")
                        if password:
                            unlock_attempts += 1
                            unlocked_path = out_path.with_name(out_path.stem + "_unlocked.pdf")
                            ok, reason = try_unlock_pdf(out_path, password, unlocked_path)
                            if ok:
                                unlocked_pdf_count += 1
                            else:
                                unlock_failures.append(f"{safe_name}: {reason}")

                # Save metadata for repeatable post-processing (e.g., unlocking locked PDFs).
                manifest = {
                    "date": date,
                    "language": language,
                    "newspaper": newspaper,
                    "edition": edition,
                    "type": entry.get("type"),
                    "type_original": entry.get("type_original"),
                    "requires_password": entry.get("requires_password", False),
                    "password_hints": entry.get("password_hints", []),
                    "direct_urls": urls,
                    "pikepdf_available": PIKEPDF_AVAILABLE,
                    "unlock_attempts": unlock_attempts,
                    "unlocked_pdf_count": unlocked_pdf_count,
                    "unlock_failures": unlock_failures,
                }
                (folder / "_entry_manifest.json").write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                write_json(
                    self,
                    200,
                    {
                        "ok": True,
                        "output_dir": str(folder.resolve()),
                        "total_urls": len(urls),
                        "saved_count": saved_count,
                        "failed_count": len(failures),
                        "failures": failures,
                        "pikepdf_available": PIKEPDF_AVAILABLE,
                        "unlock_attempts": unlock_attempts,
                        "unlocked_pdf_count": unlocked_pdf_count,
                        "unlock_failures": unlock_failures,
                    },
                )
                return

            write_json(self, 404, {"ok": False, "error": "not found"})
        except json.JSONDecodeError:
            write_json(self, 400, {"ok": False, "error": "invalid JSON body"})
        except KeyError as exc:
            write_json(self, 404, {"ok": False, "error": f"not found in dataset: {exc}"})
        except urllib.error.HTTPError as exc:
            write_json(self, 502, {"ok": False, "error": f"upstream error: {exc.code}"})
        except Exception as exc:
            write_json(self, 500, {"ok": False, "error": str(exc)})

    def log_message(self, format_str, *args):
        return


def main():
    DOWNLOAD_ROOT.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Server running on http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop")
    server.serve_forever()


if __name__ == "__main__":
    main()

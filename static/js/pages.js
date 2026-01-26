(function () {
  const $ = (id) => document.getElementById(id);
  const esc = (s) => ParsePro.escapeHtml(s);
  const fmtDate = (s) => (s ? new Date(s).toLocaleString() : "—");

  function root() {
    const el = $("pageRoot");
    if (!el) return null;
    return {
      el,
      page: el.dataset.page || "",
      runId: el.dataset.runId || "",
      candidateId: el.dataset.candidateId || "",
    };
  }

  function card(title, bodyHtml, footerHtml) {
    return `
      <div class="card shadow-sm mb-3">
        <div class="card-header bg-white"><div class="fw-semibold">${esc(title)}</div></div>
        <div class="card-body">${bodyHtml}</div>
        ${footerHtml ? `<div class="card-footer bg-white">${footerHtml}</div>` : ""}
      </div>
    `;
  }

  function badge(status) {
    const cls =
      status === "success" ? "text-bg-success" :
      status === "partial" ? "text-bg-warning" :
      status === "failed" ? "text-bg-danger" :
      status === "processing" ? "text-bg-info" : "text-bg-secondary";
    return `<span class="badge ${cls}">${esc(status || "—")}</span>`;
  }

  // ---------------- Dashboard
  async function renderDashboard(r) {
    r.el.innerHTML = `
      <div class="d-flex align-items-center justify-content-between mb-3">
        <div>
          <h1 class="h3 mb-1">Dashboard</h1>
          <div class="text-muted">Overview of resume parsing activity.</div>
        </div>
        <div class="d-flex gap-2">
          <a class="btn btn-outline-dark" href="/resumes/upload/"><i class="bi bi-upload me-2"></i>Upload</a>
          <a class="btn btn-dark" href="/candidates/"><i class="bi bi-people me-2"></i>Candidates</a>
          <a class="btn btn-outline-secondary" href="/"><i class="bi bi-house me-2"></i>Home</a>
        </div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-12 col-md-6 col-xl-3"><div class="card shadow-sm"><div class="card-body"><div class="text-muted small">Documents</div><div class="display-6 fw-semibold" id="statDocs">—</div></div></div></div>
        <div class="col-12 col-md-6 col-xl-3"><div class="card shadow-sm"><div class="card-body"><div class="text-muted small">Parse Runs</div><div class="display-6 fw-semibold" id="statRuns">—</div></div></div></div>
        <div class="col-12 col-md-6 col-xl-3"><div class="card shadow-sm"><div class="card-body"><div class="text-muted small">Candidates</div><div class="display-6 fw-semibold" id="statCandidates">—</div></div></div></div>
        <div class="col-12 col-md-6 col-xl-3"><div class="card shadow-sm"><div class="card-body"><div class="text-muted small">Successful (top page)</div><div class="display-6 fw-semibold" id="statSuccess">—</div></div></div></div>
      </div>

      <div class="row g-3">
        <div class="col-12 col-xl-6">
          ${card("Recent Parse Runs", `
            <div class="table-responsive">
              <table class="table table-sm align-middle">
                <thead><tr><th>ID</th><th>Status</th><th>Model</th><th>Created</th><th></th></tr></thead>
                <tbody id="recentRunsBody"></tbody>
              </table>
            </div>
            <div class="text-muted d-none" id="recentRunsEmpty">No parse runs yet.</div>
          `, `<div class="text-end"><a class="btn btn-outline-dark btn-sm" href="/resumes/parse-runs/">View all</a></div>`)}
        </div>

        <div class="col-12 col-xl-6">
          ${card("Recent Candidates", `
            <div class="table-responsive">
              <table class="table table-sm align-middle">
                <thead><tr><th>Name</th><th>Role</th><th>Confidence</th><th>Created</th><th></th></tr></thead>
                <tbody id="recentCandidatesBody"></tbody>
              </table>
            </div>
            <div class="text-muted d-none" id="recentCandidatesEmpty">No candidates yet.</div>
          `, `<div class="text-end"><a class="btn btn-outline-dark btn-sm" href="/candidates/">View all</a></div>`)}
        </div>
      </div>
    `;

    const docsResp = await ParsePro.apiFetch("/resume-documents/?page_size=1", { method: "GET" });
    const runsResp = await ParsePro.apiFetch("/parse-runs/?page_size=5", { method: "GET" });
    const candResp = await ParsePro.apiFetch("/candidates/?page_size=5", { method: "GET" });

    const docs = await docsResp.json().catch(() => null);
    const runs = await runsResp.json().catch(() => null);
    const cands = await candResp.json().catch(() => null);

    $("statDocs").textContent = docs?.data?.count ?? "0";
    $("statRuns").textContent = runs?.data?.count ?? "0";
    $("statCandidates").textContent = cands?.data?.count ?? "0";

    const runList = runs?.data?.results || [];
    $("statSuccess").textContent = runList.filter(x => x.status === "success").length;

    const runsBody = $("recentRunsBody");
    runsBody.innerHTML = "";
    $("recentRunsEmpty").classList.toggle("d-none", runList.length > 0);
    for (const x of runList) {
      runsBody.insertAdjacentHTML("beforeend", `
        <tr>
          <td class="mono">${x.id}</td>
          <td>${badge(x.status)}</td>
          <td class="small">${esc(x.model_name || "—")}</td>
          <td class="small">${fmtDate(x.created_at)}</td>
          <td class="text-end"><a class="btn btn-outline-dark btn-sm" href="/resumes/parse-runs/${x.id}/">Open</a></td>
        </tr>
      `);
    }

    const candList = cands?.data?.results || [];
    const candBody = $("recentCandidatesBody");
    candBody.innerHTML = "";
    $("recentCandidatesEmpty").classList.toggle("d-none", candList.length > 0);
    for (const c of candList) {
      candBody.insertAdjacentHTML("beforeend", `
        <tr>
          <td>${esc(c.full_name || "—")}</td>
          <td class="small">${esc(c.primary_role || "—")}</td>
          <td class="small">${typeof c.overall_confidence === "number" ? c.overall_confidence.toFixed(2) : "—"}</td>
          <td class="small">${fmtDate(c.created_at)}</td>
          <td class="text-end"><a class="btn btn-outline-dark btn-sm" href="/candidates/${c.id}/">Open</a></td>
        </tr>
      `);
    }
  }

  // ---------------- Upload
  async function renderUpload(r) {
    r.el.innerHTML = `
      <div class="mb-3">
        <h1 class="h3 mb-1">Upload Resume</h1>
        <div class="text-muted">Upload PDF/DOCX. The system extracts, normalizes, validates schema, classifies, and summarizes.</div>
      </div>

      <div class="row g-3">
        <div class="col-12 col-xl-6">
          ${card("Upload", `
            <div id="uploadAlert"></div>
            <form id="uploadForm">
              <div class="mb-3">
                <label class="form-label">Resume file(s) (PDF/DOCX)</label>
                <input type="file" class="form-control" name="file" id="fileInput" accept=".pdf,.doc,.docx" required>
                <div class="form-text">Select one or multiple files (hold Ctrl/Cmd to select multiple)</div>
              </div>

              <div class="form-check mb-3">
                <input class="form-check-input" type="checkbox" id="bulkMode">
                <label class="form-check-label" for="bulkMode">Bulk upload mode (process multiple files)</label>
                <div class="form-text">When enabled, uploads multiple files in one request. Max 100 files.</div>
              </div>

              <div class="form-check mb-3">
                <input class="form-check-input" type="checkbox" id="syncMode">
                <label class="form-check-label" for="syncMode">Run synchronously (demo/testing)</label>
                <div class="form-text">Default is async (Celery). Sync provides immediate results. Requirements work in both modes.</div>
              </div>

              <div class="mb-3">
                <button class="btn btn-outline-secondary btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#requirementsCollapse" aria-expanded="false" aria-controls="requirementsCollapse">
                  <i class="bi bi-funnel me-1"></i>Set Requirements (Optional)
                </button>
                <div class="collapse mt-2" id="requirementsCollapse">
                  <div class="card card-body bg-light">
                    <small class="text-muted mb-2 d-block">Only candidates meeting these requirements will be kept. Others will be discarded.</small>
                    <div class="mb-2">
                      <label class="form-label small">Required Skills (comma-separated)</label>
                      <input type="text" class="form-control form-control-sm" id="requiredSkills" placeholder="e.g., Python, JavaScript, React">
                      <small class="text-muted">All listed skills must be present</small>
                    </div>
                    <div class="mb-2">
                      <label class="form-label small">Any Skills (comma-separated)</label>
                      <input type="text" class="form-control form-control-sm" id="anySkills" placeholder="e.g., Docker, Kubernetes">
                      <small class="text-muted">At least one skill must be present</small>
                    </div>
                    <div class="mb-2">
                      <label class="form-label small">Minimum Years of Experience</label>
                      <input type="number" class="form-control form-control-sm" id="minYearsExperience" placeholder="e.g., 3" min="0" step="0.5">
                    </div>
                    <div class="mb-2">
                      <label class="form-label small">Required Education Degree</label>
                      <input type="text" class="form-control form-control-sm" id="requiredDegree" placeholder="e.g., Bachelor, Master">
                    </div>
                    <div class="mb-2">
                      <label class="form-label small">Required Primary Role</label>
                      <input type="text" class="form-control form-control-sm" id="requiredRole" placeholder="e.g., Software Engineer, Developer">
                    </div>
                    <div class="mb-2">
                      <label class="form-label small">Required Seniority</label>
                      <input type="text" class="form-control form-control-sm" id="requiredSeniority" placeholder="e.g., Senior, Lead">
                    </div>
                    <div class="mb-2">
                      <label class="form-label small">Location Must Contain</label>
                      <input type="text" class="form-control form-control-sm" id="locationContains" placeholder="e.g., New York, Remote">
                    </div>
                    <div class="mb-2">
                      <label class="form-label small">Minimum Confidence (0-1)</label>
                      <input type="number" class="form-control form-control-sm" id="minConfidence" placeholder="e.g., 0.7" min="0" max="1" step="0.1">
                    </div>
                    <hr class="my-2">
                    <div class="form-check">
                      <input class="form-check-input" type="checkbox" id="useLlmValidation" checked>
                      <label class="form-check-label small" for="useLlmValidation">
                        <strong>Use LLM Validation</strong> (Recommended)
                      </label>
                      <div class="form-text small">Uses AI for semantic matching (e.g., "Software Developer" matches "Software Engineer"). Disable for faster but less accurate string matching.</div>
                    </div>
                  </div>
                </div>
              </div>

              <button class="btn btn-dark" type="submit" id="uploadBtn">
                <i class="bi bi-upload me-2"></i>Upload and Parse
              </button>
            </form>
          `)}
        </div>

        <div class="col-12 col-xl-6">
          ${card("Processing Status", `
            <div class="small text-muted mb-2">This panel updates as the parse run progresses.</div>

            <div class="d-flex align-items-center gap-2 mb-2">
              <span class="text-muted">Parse Run ID:</span>
              <span class="fw-semibold" id="runId">—</span>
            </div>

            <div class="d-flex align-items-center gap-2 mb-3">
              <span class="text-muted">Status:</span>
              <span class="badge text-bg-secondary" id="runStatus">—</span>
            </div>

            <div class="progress mb-3 d-none" id="runProgressWrap">
              <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%"></div>
            </div>

            <div class="d-flex gap-2">
              <a class="btn btn-outline-dark btn-sm disabled" href="#" id="openRunBtn">Open Parse Run</a>
              <a class="btn btn-dark btn-sm disabled" href="#" id="openCandidateBtn">Open Candidate</a>
            </div>

            <hr class="my-3">
            <ul class="small mb-0">
              <li>Duplicate detection links to existing results.</li>
              <li>For async runs, the page polls parse-run status automatically.</li>
            </ul>
          `)}
        </div>
      </div>
    `;

    function setRunPanel(runId, status, candidateId) {
      $("runId").textContent = runId || "—";
      const st = $("runStatus");
      st.textContent = status || "—";
      st.className = "badge " + (
        status === "success" ? "text-bg-success" :
        status === "partial" ? "text-bg-warning" :
        status === "failed" ? "text-bg-danger" :
        status === "processing" ? "text-bg-info" : "text-bg-secondary"
      );

      const openRun = $("openRunBtn");
      openRun.classList.remove("disabled");
      openRun.href = `/resumes/parse-runs/${runId}/`;

      const openCand = $("openCandidateBtn");
      if (candidateId) {
        openCand.classList.remove("disabled");
        openCand.href = `/candidates/${candidateId}/`;
      } else {
        openCand.classList.add("disabled");
        openCand.href = "#";
      }
    }

    async function fetchRun(runId) {
      const resp = await ParsePro.apiFetch(`/parse-runs/${runId}/`, { method: "GET" });
      if (!resp.ok) return null;
      const data = await resp.json().catch(() => null);
      return data?.data ? data.data : data;
    }

    async function findCandidateIdByParseRun(runId) {
      try {
        const resp = await ParsePro.apiFetch(`/candidates/?parse_run=${encodeURIComponent(runId)}&page_size=1`, { method: "GET" });
        const data = await resp.json().catch(() => null);
        const results = data?.data?.results || [];
        return results.length ? results[0].id : null;
      } catch { return null; }
    }

    async function poll(runId) {
      const prog = $("runProgressWrap");
      prog.classList.remove("d-none");

      const start = Date.now();
      while (Date.now() - start < 120000) {
        const run = await fetchRun(runId);
        if (!run) break;

        setRunPanel(runId, run.status, null);

        if (["success", "partial", "failed"].includes(run.status)) {
          prog.classList.add("d-none");
          
          // Check if candidate was rejected due to requirements (async mode)
          if (run.warnings && Array.isArray(run.warnings)) {
            const reqFailed = run.warnings.find(w => typeof w === "string" && w.startsWith("REQUIREMENTS_FAILED:"));
            if (reqFailed) {
              const reasons = reqFailed.replace("REQUIREMENTS_FAILED: ", "").split(", ");
              ParsePro.renderAlert($("uploadAlert"), `Candidate rejected: ${reasons.join(", ")}`, "danger");
              setRunPanel(runId, run.status, null);
              return;
            }
          }
          
          const cid = await findCandidateIdByParseRun(runId);
          if (cid) {
            setRunPanel(runId, run.status, cid);
            // Check if requirements were applied
            if (run.requirements) {
              ParsePro.renderAlert($("uploadAlert"), "Candidate accepted and meets all requirements!", "success");
            }
          } else {
            setRunPanel(runId, run.status, null);
          }
          return;
        }
        await new Promise(res => setTimeout(res, 2500));
      }
      prog.classList.add("d-none");
      ParsePro.toast("Upload", "Polling timed out. Open the parse run to refresh.", "warning");
    }

    // Enable multiple file selection
    const fileInput = $("fileInput");
    fileInput.setAttribute("multiple", "multiple");

    $("uploadForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const alert = $("uploadAlert");
      alert.innerHTML = "";

      const btn = $("uploadBtn");
      btn.disabled = true;

      const sync = $("syncMode").checked;
      const bulkMode = $("bulkMode").checked;
      const fd = new FormData($("uploadForm"));
      const files = fileInput.files;

      // Validate file selection
      if (!files || files.length === 0) {
        ParsePro.renderAlert(alert, "Please select at least one file.", "danger");
        btn.disabled = false;
        return;
      }

      if (bulkMode && files.length > 100) {
        ParsePro.renderAlert(alert, "Maximum 100 files allowed for bulk upload.", "danger");
        btn.disabled = false;
        return;
      }

      // For bulk upload, append all files to FormData
      if (bulkMode && files.length > 1) {
        fd.delete("file"); // Remove single file entry
        for (let i = 0; i < files.length; i++) {
          fd.append("files", files[i]);
        }
      }

      // Collect requirements if any are specified
      const requirements = {};
      const requiredSkills = $("requiredSkills").value.trim();
      if (requiredSkills) {
        requirements.required_skills = requiredSkills.split(",").map(s => s.trim()).filter(s => s);
      }
      
      const anySkills = $("anySkills").value.trim();
      if (anySkills) {
        requirements.any_skills = anySkills.split(",").map(s => s.trim()).filter(s => s);
      }
      
      const minYears = $("minYearsExperience").value.trim();
      if (minYears) {
        requirements.min_years_experience = parseFloat(minYears);
      }
      
      const requiredDegree = $("requiredDegree").value.trim();
      if (requiredDegree) {
        requirements.required_education_degree = [requiredDegree.trim()];
      }
      
      const requiredRole = $("requiredRole").value.trim();
      if (requiredRole) {
        requirements.required_primary_role = [requiredRole.trim()];
      }
      
      const requiredSeniority = $("requiredSeniority").value.trim();
      if (requiredSeniority) {
        requirements.required_seniority = [requiredSeniority.trim()];
      }
      
      const locationContains = $("locationContains").value.trim();
      if (locationContains) {
        requirements.location_contains = locationContains.trim();
      }
      
      const minConfidence = $("minConfidence").value.trim();
      if (minConfidence) {
        requirements.min_confidence = parseFloat(minConfidence);
      }
      
      // LLM validation setting (default: true)
      const useLlmValidation = $("useLlmValidation").checked;
      requirements.use_llm_validation = useLlmValidation;
      
      // Add requirements to FormData if any are specified
      if (Object.keys(requirements).length > 1 || !useLlmValidation) {  // >1 because use_llm_validation is always added
        fd.append("requirements", JSON.stringify(requirements));
      }

      try {
        const endpoint = bulkMode && files.length > 1 
          ? `/resumes/bulk-upload/${sync ? "?sync=1" : ""}`
          : `/resumes/upload/${sync ? "?sync=1" : ""}`;
        
        const resp = await ParsePro.apiFetch(endpoint, { method: "POST", body: fd });
        const data = await resp.json().catch(() => null);

        if (!resp.ok || !data?.success) {
          ParsePro.renderAlert(alert, data?.error?.message || "Upload failed", "danger");
          return;
        }

        const payload = data.data || {};

        // Handle bulk upload response
        if (bulkMode && files.length > 1) {
          const summary = payload;
          const acceptedCount = summary.accepted?.length || summary.matching || 0;
          const rejectedCount = summary.rejected?.length || summary.discarded || 0;
          const errorCount = summary.errors?.length || 0;
          const total = summary.total || files.length;

          let message = `Bulk upload completed: ${acceptedCount} accepted, ${rejectedCount} rejected`;
          if (errorCount > 0) {
            message += `, ${errorCount} errors`;
          }

          ParsePro.renderAlert(alert, message, errorCount > 0 ? "warning" : "success");

          // Show requirements info if applied
          if (summary.requirements_applied) {
            alert.innerHTML += `<div class="mt-2 small text-info"><strong>Requirements applied:</strong> ${JSON.stringify(summary.requirements_applied)}</div>`;
          }

          // Show detailed breakdown of accepted vs rejected
          if (summary.results && summary.results.length > 0) {
            let resultsHtml = `<div class="mt-3"><strong>Detailed Results:</strong></div>`;
            
            // Accepted candidates
            if (summary.accepted && summary.accepted.length > 0) {
              resultsHtml += `<div class="mt-2"><strong class="text-success">✓ Accepted (${summary.accepted.length}):</strong><ul class="small mb-0 mt-1">`;
              summary.accepted.forEach(r => {
                const candidateLink = r.candidate_id 
                  ? ` <a href="/candidates/${r.candidate_id}/" target="_blank">View Candidate</a>`
                  : "";
                resultsHtml += `<li class="text-success">${r.filename}${candidateLink}</li>`;
              });
              resultsHtml += `</ul></div>`;
            }
            
            // Rejected candidates
            if (summary.rejected && summary.rejected.length > 0) {
              resultsHtml += `<div class="mt-2"><strong class="text-danger">✗ Rejected (${summary.rejected.length}):</strong><ul class="small mb-0 mt-1">`;
              summary.rejected.forEach(r => {
                const reasons = r.discard_reasons?.join("; ") || "Does not meet requirements";
                resultsHtml += `<li class="text-danger">${r.filename} - ${reasons}</li>`;
              });
              resultsHtml += `</ul></div>`;
            }
            
            // Errors
            if (summary.errors && summary.errors.length > 0) {
              resultsHtml += `<div class="mt-2"><strong class="text-warning">⚠ Errors (${summary.errors.length}):</strong><ul class="small mb-0 mt-1">`;
              summary.errors.forEach(e => {
                resultsHtml += `<li class="text-warning">${e.filename} - ${e.error}</li>`;
              });
              resultsHtml += `</ul></div>`;
            }
            
            alert.innerHTML += resultsHtml;
          }

          // If only one file was successfully uploaded, show its status
          if (acceptedCount === 1 && summary.accepted && summary.accepted.length === 1) {
            const result = summary.accepted[0];
            if (result.parse_run_id && !result.duplicate && !result.discarded) {
              setRunPanel(result.parse_run_id, result.status, result.candidate_id || null);
              if (resp.status === 202 || ["queued", "processing"].includes(result.status)) {
                await poll(result.parse_run_id);
              }
            }
          }
          return;
        }

        // Handle single file upload response
        if (payload.duplicate) {
          // Check if duplicate was rejected due to requirements
          if (payload.requirements_check === "failed" && payload.rejection_reasons) {
            ParsePro.renderAlert(alert, `Duplicate detected but rejected: ${payload.rejection_reasons.join(", ")}`, "danger");
            return;
          }
          ParsePro.renderAlert(alert, "Duplicate detected. Redirecting to existing results.", "warning");
          if (payload.parse_run_id) window.location.href = `/resumes/parse-runs/${payload.parse_run_id}/`;
          return;
        }

        // Check if candidate was rejected due to requirements
        if (payload.rejected && payload.rejection_reasons) {
          ParsePro.renderAlert(alert, `Candidate rejected: ${payload.rejection_reasons.join(", ")}`, "danger");
          if (payload.requirements_applied) {
            alert.innerHTML += `<div class="mt-2 small text-info"><strong>Requirements applied:</strong> ${JSON.stringify(payload.requirements_applied)}</div>`;
          }
          return;
        }

        // Show requirements info if applied and accepted
        if (payload.requirements_applied && payload.accepted) {
          ParsePro.renderAlert(alert, "Candidate accepted and meets all requirements!", "success");
          alert.innerHTML += `<div class="mt-2 small text-info"><strong>Requirements applied:</strong> ${JSON.stringify(payload.requirements_applied)}</div>`;
        }

        setRunPanel(payload.parse_run_id, payload.status, payload.candidate_id || null);

        if (resp.status === 202 || ["queued", "processing"].includes(payload.status)) {
          const reqMsg = payload.requirements_applied 
            ? " Upload accepted. Requirements will be checked after processing completes."
            : " Upload accepted. Parsing queued in background.";
          ParsePro.renderAlert(alert, reqMsg, "success");
          await poll(payload.parse_run_id);
        } else {
          ParsePro.renderAlert(alert, `Parsing finished with status: ${payload.status}`, payload.status === "success" ? "success" : "warning");
        }
      } catch (err) {
        ParsePro.renderAlert(alert, err.message || "Upload failed", "danger");
      } finally {
        btn.disabled = false;
      }
    });
  }

  // ---------------- Documents
  async function renderDocuments(r) {
    r.el.innerHTML = `
      <div class="d-flex align-items-center justify-content-between mb-3">
        <div>
          <h1 class="h3 mb-1">Documents</h1>
          <div class="text-muted">Your uploaded resume documents.</div>
        </div>
        <a class="btn btn-dark" href="/resumes/upload/"><i class="bi bi-upload me-2"></i>Upload</a>
      </div>

      ${card("Resume Documents", `
        <div class="table-responsive">
          <table class="table align-middle">
            <thead>
              <tr><th>ID</th><th>Filename</th><th>MIME</th><th>Size</th><th>Hash</th><th>Extract</th><th>Created</th></tr>
            </thead>
            <tbody id="docsBody"></tbody>
          </table>
        </div>
        <div class="text-muted d-none" id="docsEmpty">No documents uploaded yet.</div>
      `)}
    `;

    const resp = await ParsePro.apiFetch("/resume-documents/?page_size=50", { method: "GET" });
    const data = await resp.json().catch(() => null);
    const docs = data?.data?.results || [];

    const body = $("docsBody");
    body.innerHTML = "";
    $("docsEmpty").classList.toggle("d-none", docs.length > 0);

    const fmtBytes = (n) => {
      if (!n && n !== 0) return "—";
      const units = ["B","KB","MB","GB"];
      let x = Number(n), i = 0;
      while (x >= 1024 && i < units.length - 1) { x /= 1024; i++; }
      return `${x.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
    };

    for (const d of docs) {
      body.insertAdjacentHTML("beforeend", `
        <tr>
          <td class="mono">${d.id}</td>
          <td>${esc(d.original_filename || "—")}</td>
          <td class="small">${esc(d.mime_type || "—")}</td>
          <td class="small">${fmtBytes(d.file_size)}</td>
          <td class="small mono">${esc((d.file_hash || "").slice(0, 12) || "—")}</td>
          <td class="small">${esc(d.extraction_method || "—")}</td>
          <td class="small">${fmtDate(d.created_at)}</td>
        </tr>
      `);
    }
  }

  // ---------------- Parse Runs list + detail
  async function renderParseRuns(r) {
    r.el.innerHTML = `
      <div class="d-flex align-items-center justify-content-between mb-3">
        <div>
          <h1 class="h3 mb-1">Parse Runs</h1>
          <div class="text-muted">History of parsing runs.</div>
        </div>
        <a class="btn btn-dark" href="/resumes/upload/"><i class="bi bi-upload me-2"></i>Upload</a>
      </div>

      ${card("Filters", `
        <form class="row g-2 align-items-end" id="runsFilterForm">
          <div class="col-12 col-md-3">
            <label class="form-label">Status</label>
            <select class="form-select" id="statusFilter">
              <option value="">All</option>
              <option value="queued">Queued</option>
              <option value="processing">Processing</option>
              <option value="success">Success</option>
              <option value="partial">Partial</option>
              <option value="failed">Failed</option>
            </select>
          </div>
          <div class="col-12 col-md-3">
            <label class="form-label">Created after (YYYY-MM-DD)</label>
            <input class="form-control" id="afterFilter" placeholder="2026-01-01">
          </div>
          <div class="col-12 col-md-3">
            <label class="form-label">Created before (YYYY-MM-DD)</label>
            <input class="form-control" id="beforeFilter" placeholder="2026-01-31">
          </div>
          <div class="col-12 col-md-3 d-flex gap-2">
            <button class="btn btn-outline-dark w-100" type="submit"><i class="bi bi-funnel me-2"></i>Apply</button>
            <button class="btn btn-dark w-100" type="button" id="resetRuns"><i class="bi bi-x-circle me-2"></i>Reset</button>
          </div>
        </form>
      `)}

      ${card("Results", `
        <div class="table-responsive">
          <table class="table align-middle">
            <thead><tr><th>ID</th><th>Status</th><th>Model</th><th>Latency</th><th>Created</th><th></th></tr></thead>
            <tbody id="runsBody"></tbody>
          </table>
        </div>
        <div class="text-muted d-none" id="runsEmpty">No parse runs found.</div>
        <div class="d-flex justify-content-between align-items-center mt-3">
          <div class="small text-muted" id="runsMeta"></div>
          <div class="btn-group">
            <button class="btn btn-outline-dark btn-sm" id="runsPrev">Prev</button>
            <button class="btn btn-outline-dark btn-sm" id="runsNext">Next</button>
          </div>
        </div>
      `)}
    `;

    let nextUrl = null, prevUrl = null;

    function toRel(url) {
      if (!url) return null;
      const u = new URL(url);
      return u.pathname.replace("/api/v1", "") + u.search;
    }

    async function load(path) {
      const resp = await ParsePro.apiFetch(path, { method: "GET" });
      const data = await resp.json().catch(() => null);

      const payload = data?.data || {};
      const results = payload.results || [];
      nextUrl = payload.next;
      prevUrl = payload.previous;

      const body = $("runsBody");
      body.innerHTML = "";
      $("runsEmpty").classList.toggle("d-none", results.length > 0);
      $("runsMeta").textContent = `Showing ${results.length} of ${payload.count ?? results.length}`;

      for (const x of results) {
        body.insertAdjacentHTML("beforeend", `
          <tr>
            <td class="mono">${x.id}</td>
            <td>${badge(x.status)}</td>
            <td class="small">${esc(x.model_name || "—")}</td>
            <td class="small">${x.latency_ms ? x.latency_ms + " ms" : "—"}</td>
            <td class="small">${fmtDate(x.created_at)}</td>
            <td class="text-end"><a class="btn btn-outline-dark btn-sm" href="/resumes/parse-runs/${x.id}/">Open</a></td>
          </tr>
        `);
      }
    }

    // initial from URL params
    const params = new URLSearchParams(window.location.search);
    const status = params.get("status") || "";
    const after = params.get("after") || "";
    const before = params.get("before") || "";

    $("statusFilter").value = status;
    $("afterFilter").value = after;
    $("beforeFilter").value = before;

    const base = new URL("/api/v1/parse-runs/", window.location.origin);
    base.searchParams.set("page_size", "20");
    if (status) base.searchParams.set("status", status);
    if (after) base.searchParams.set("after", after);
    if (before) base.searchParams.set("before", before);

    await load(base.pathname.replace("/api/v1","") + base.search);

    $("runsFilterForm").addEventListener("submit", (e) => {
      e.preventDefault();
      const p = new URLSearchParams();
      const s = $("statusFilter").value;
      const a = $("afterFilter").value.trim();
      const b = $("beforeFilter").value.trim();
      if (s) p.set("status", s);
      if (a) p.set("after", a);
      if (b) p.set("before", b);
      window.location.search = p.toString();
    });

    $("resetRuns").addEventListener("click", () => window.location.search = "");

    $("runsPrev").addEventListener("click", async () => { if (prevUrl) await load(toRel(prevUrl)); });
    $("runsNext").addEventListener("click", async () => { if (nextUrl) await load(toRel(nextUrl)); });
  }

  async function renderParseRunDetail(r) {
    const runId = r.runId;
    r.el.innerHTML = `
      <div class="d-flex align-items-center justify-content-between mb-3">
        <div>
          <h1 class="h3 mb-1">Parse Run <span class="text-muted">#</span>${esc(runId)}</h1>
          <div class="text-muted">Inspect status, warnings, errors and JSON outputs.</div>
        </div>
        <div class="d-flex gap-2">
          <button class="btn btn-outline-dark" id="retryBtn"><i class="bi bi-arrow-repeat me-2"></i>Retry</button>
          <a class="btn btn-dark" href="/resumes/parse-runs/"><i class="bi bi-arrow-left me-2"></i>Back</a>
        </div>
      </div>

      <div class="row g-3">
        <div class="col-12 col-xl-4">
          ${card("Status", `
            <div class="d-flex align-items-center justify-content-between mb-2">
              <div class="fw-semibold">Status</div>
              <span class="badge" id="statusBadge">—</span>
            </div>

            <dl class="row small mb-0">
              <dt class="col-5 text-muted">Model</dt><dd class="col-7" id="modelName">—</dd>
              <dt class="col-5 text-muted">Latency</dt><dd class="col-7" id="latency">—</dd>
              <dt class="col-5 text-muted">Created</dt><dd class="col-7" id="createdAt">—</dd>
              <dt class="col-5 text-muted">Error</dt><dd class="col-7" id="errorInfo">—</dd>
            </dl>

            <hr class="my-3">
            <div class="d-flex gap-2">
              <a class="btn btn-outline-dark btn-sm disabled" href="#" id="openCandidateBtn">Open Candidate</a>
              <button class="btn btn-dark btn-sm" id="refreshBtn"><i class="bi bi-arrow-clockwise me-2"></i>Refresh</button>
            </div>
          `)}

          ${card("Warnings", `
            <ul class="small mb-0" id="warningsList"></ul>
            <div class="text-muted small d-none" id="warningsEmpty">No warnings.</div>
          `)}
        </div>

        <div class="col-12 col-xl-8">
          ${card("Normalized JSON", `
            <div class="d-flex justify-content-end mb-2">
              <button class="btn btn-outline-dark btn-sm" id="copyNormalized"><i class="bi bi-clipboard me-2"></i>Copy</button>
            </div>
            <pre class="json-pre" id="normalizedPre">{}</pre>
          `)}

          ${card("Raw LLM JSON", `
            <div class="d-flex justify-content-end mb-2">
              <button class="btn btn-outline-dark btn-sm" id="copyRaw"><i class="bi bi-clipboard me-2"></i>Copy</button>
            </div>
            <pre class="json-pre" id="rawPre">{}</pre>
          `)}
        </div>
      </div>
    `;

    async function findCandidateIdByParseRun(id) {
      try {
        const resp = await ParsePro.apiFetch(`/candidates/?parse_run=${encodeURIComponent(id)}&page_size=1`, { method: "GET" });
        const data = await resp.json().catch(() => null);
        const results = data?.data?.results || [];
        return results.length ? results[0].id : null;
      } catch { return null; }
    }

    async function render() {
      const resp = await ParsePro.apiFetch(`/parse-runs/${runId}/`, { method: "GET" });
      const data = await resp.json().catch(() => null);
      const run = data?.data ? data.data : data;

      const cls =
        run.status === "success" ? "text-bg-success" :
        run.status === "partial" ? "text-bg-warning" :
        run.status === "failed" ? "text-bg-danger" :
        run.status === "processing" ? "text-bg-info" : "text-bg-secondary";

      $("statusBadge").className = `badge ${cls}`;
      $("statusBadge").textContent = run.status;

      $("modelName").textContent = run.model_name || "—";
      $("latency").textContent = run.latency_ms ? `${run.latency_ms} ms` : "—";
      $("createdAt").textContent = fmtDate(run.created_at);
      $("errorInfo").textContent = run.error_code ? `${run.error_code}: ${run.error_message || ""}` : "—";

      const warnings = run.warnings || [];
      const wl = $("warningsList");
      wl.innerHTML = "";
      $("warningsEmpty").classList.toggle("d-none", warnings.length > 0);
      warnings.forEach(w => wl.insertAdjacentHTML("beforeend", `<li>${esc(w)}</li>`));

      $("normalizedPre").textContent = JSON.stringify(run.normalized_json || {}, null, 2);
      $("rawPre").textContent = JSON.stringify(run.llm_raw_json || {}, null, 2);

      const cid = await findCandidateIdByParseRun(runId);
      const openCandidateBtn = $("openCandidateBtn");
      if (cid) {
        openCandidateBtn.classList.remove("disabled");
        openCandidateBtn.href = `/candidates/${cid}/`;
      } else {
        openCandidateBtn.classList.add("disabled");
        openCandidateBtn.href = "#";
      }
    }

    $("refreshBtn").addEventListener("click", () => render().catch(err => ParsePro.toast("Parse Run", err.message, "danger")));

    $("copyNormalized").addEventListener("click", async () => {
      await navigator.clipboard.writeText($("normalizedPre").textContent || "");
      ParsePro.toast("Copy", "Normalized JSON copied", "success");
    });

    $("copyRaw").addEventListener("click", async () => {
      await navigator.clipboard.writeText($("rawPre").textContent || "");
      ParsePro.toast("Copy", "Raw JSON copied", "success");
    });

    $("retryBtn").addEventListener("click", async () => {
      const btn = $("retryBtn");
      btn.disabled = true;
      try {
        const resp = await ParsePro.apiFetch(`/parse-runs/${runId}/retry/`, { method: "POST" });
        const data = await resp.json().catch(() => null);
        if (!resp.ok || !data?.success) {
          ParsePro.toast("Retry", data?.error?.message || "Retry failed", "danger");
          return;
        }
        const newRunId = data.data?.parse_run_id || data.data?.id || data.parse_run_id || data.id;
        ParsePro.toast("Retry", `Queued new parse run #${newRunId}`, "success");
        window.location.href = `/resumes/parse-runs/${newRunId}/`;
      } catch (err) {
        ParsePro.toast("Retry", err.message || "Retry failed", "danger");
      } finally {
        btn.disabled = false;
      }
    });

    await render();
  }

  // ---------------- Candidates list + detail + logs
  async function renderCandidatesList(r) {
    r.el.innerHTML = `
      <div class="d-flex align-items-center justify-content-between mb-3">
        <div>
          <h1 class="h3 mb-1">Candidates</h1>
          <div class="text-muted">Search, filter, review and edit candidate profiles.</div>
        </div>
        <div class="d-flex gap-2">
          <button class="btn btn-outline-dark" id="exportBtn"><i class="bi bi-download me-2"></i>Export CSV</button>
          <a class="btn btn-dark" href="/resumes/upload/"><i class="bi bi-upload me-2"></i>Upload</a>
        </div>
      </div>

      ${card("Filters", `
        <form class="row g-2 align-items-end" id="candFilterForm">
          <div class="col-12 col-md-4">
            <label class="form-label">Search</label>
            <input class="form-control" id="q" placeholder="Name, title, company, role..." />
          </div>
          <div class="col-12 col-md-2">
            <label class="form-label">Role</label>
            <input class="form-control" id="role" placeholder="Backend, Data..." />
          </div>
          <div class="col-12 col-md-2">
            <label class="form-label">Skill</label>
            <input class="form-control" id="skill" placeholder="Python" />
          </div>
          <div class="col-12 col-md-2">
            <label class="form-label">Min confidence</label>
            <input class="form-control" id="min_conf" placeholder="0.6" />
          </div>
          <div class="col-12 col-md-2 d-flex gap-2">
            <button class="btn btn-outline-dark w-100" type="submit"><i class="bi bi-funnel me-2"></i>Apply</button>
            <button class="btn btn-dark w-100" type="button" id="resetCand"><i class="bi bi-x-circle me-2"></i>Reset</button>
          </div>
        </form>
      `)}

      ${card("Results", `
        <div class="table-responsive">
          <table class="table align-middle">
            <thead><tr><th>Name</th><th>Role</th><th>Seniority</th><th>Confidence</th><th>Created</th><th></th></tr></thead>
            <tbody id="candBody"></tbody>
          </table>
        </div>
        <div id="candEmpty" class="text-muted d-none">No candidates found.</div>
        <div class="d-flex justify-content-between align-items-center mt-3">
          <div class="small text-muted" id="candMeta"></div>
          <div class="btn-group">
            <button class="btn btn-outline-dark btn-sm" id="candPrev">Prev</button>
            <button class="btn btn-outline-dark btn-sm" id="candNext">Next</button>
          </div>
        </div>
      `)}
    `;

    let nextUrl = null, prevUrl = null;

    function buildQueryFromForm() {
      const p = new URLSearchParams();
      const q = $("q").value.trim();
      const role = $("role").value.trim();
      const skill = $("skill").value.trim();
      const min = $("min_conf").value.trim();
      if (q) p.set("q", q);
      if (role) p.set("role", role);
      if (skill) p.set("skill", skill);
      if (min) p.set("min_conf", min);
      return p;
    }

    function applyQueryToForm(params) {
      $("q").value = params.get("q") || "";
      $("role").value = params.get("role") || "";
      $("skill").value = params.get("skill") || "";
      $("min_conf").value = params.get("min_conf") || "";
    }

    function toRel(url) {
      if (!url) return null;
      const u = new URL(url);
      return u.pathname.replace("/api/v1", "") + u.search;
    }

    async function load(path) {
      const resp = await ParsePro.apiFetch(path, { method: "GET" });
      const data = await resp.json().catch(() => null);

      const payload = data?.data || {};
      const results = payload.results || [];
      nextUrl = payload.next;
      prevUrl = payload.previous;

      const body = $("candBody");
      body.innerHTML = "";
      $("candEmpty").classList.toggle("d-none", results.length > 0);
      $("candMeta").textContent = `Showing ${results.length} of ${payload.count ?? results.length}`;

      for (const c of results) {
        body.insertAdjacentHTML("beforeend", `
          <tr>
            <td>
              <div class="fw-semibold">${esc(c.full_name || "—")}</div>
              <div class="small text-muted">${esc(c.headline || "")}</div>
            </td>
            <td class="small">${esc(c.primary_role || "—")}</td>
            <td class="small">${esc(c.seniority || "—")}</td>
            <td class="small">${typeof c.overall_confidence === "number" ? c.overall_confidence.toFixed(2) : "—"}</td>
            <td class="small">${fmtDate(c.created_at)}</td>
            <td class="text-end"><a class="btn btn-outline-dark btn-sm" href="/candidates/${c.id}/">Open</a></td>
          </tr>
        `);
      }
    }

    const params = new URLSearchParams(window.location.search);
    applyQueryToForm(params);

    $("candFilterForm").addEventListener("submit", (e) => {
      e.preventDefault();
      window.location.search = buildQueryFromForm().toString();
    });

    $("resetCand").addEventListener("click", () => window.location.search = "");

    $("exportBtn").addEventListener("click", () => {
      const p = buildQueryFromForm();
      window.location.href = `/api/v1/candidates/export/?${p.toString()}`;
    });

    await load(`/candidates/?page_size=20&${params.toString()}`);

    $("candPrev").addEventListener("click", async () => { if (prevUrl) await load(toRel(prevUrl)); });
    $("candNext").addEventListener("click", async () => { if (nextUrl) await load(toRel(nextUrl)); });
  }

  async function renderCandidateDetail(r) {
    const id = r.candidateId;

    r.el.innerHTML = `
      <div class="d-flex align-items-center justify-content-between mb-3">
        <div>
          <h1 class="h3 mb-1" id="candName">Candidate</h1>
          <div class="text-muted" id="candMetaLine">—</div>
        </div>
        <div class="d-flex gap-2">
          <a class="btn btn-outline-dark" href="/candidates/${id}/edit-logs/"><i class="bi bi-clock-history me-2"></i>Edit History</a>
          <a class="btn btn-dark" href="/candidates/"><i class="bi bi-arrow-left me-2"></i>Back</a>
        </div>
      </div>

      <div class="row g-3">
        <div class="col-12 col-xl-4">
          ${card("Contact", `
            <dl class="row small mb-0">
              <dt class="col-5 text-muted">Email</dt><dd class="col-7" id="cEmail">—</dd>
              <dt class="col-5 text-muted">Phone</dt><dd class="col-7" id="cPhone">—</dd>
              <dt class="col-5 text-muted">Location</dt><dd class="col-7" id="cLocation">—</dd>
              <dt class="col-5 text-muted">Links</dt>
              <dd class="col-7">
                <div><a href="#" target="_blank" rel="noopener" id="cLinkedIn">—</a></div>
                <div><a href="#" target="_blank" rel="noopener" id="cGitHub">—</a></div>
                <div><a href="#" target="_blank" rel="noopener" id="cPortfolio">—</a></div>
              </dd>
            </dl>
          `)}

          ${card("Classification", `
            <div class="d-flex align-items-center justify-content-between">
              <div><div class="text-muted small">Primary role</div><div class="fw-semibold" id="cRole">—</div></div>
              <div class="text-end"><div class="text-muted small">Confidence</div><div class="fw-semibold" id="cConf">—</div></div>
            </div>
            <div class="mt-2"><div class="text-muted small">Seniority</div><div id="cSeniority">—</div></div>
            <div class="mt-2"><div class="text-muted small">Summary</div><div id="cOneLiner">—</div></div>
          `)}
        </div>

        <div class="col-12 col-xl-8">
          ${card("Edit Candidate", `
            <div id="editAlert"></div>

            <form id="editForm" class="row g-2">
              <div class="col-12 col-md-6"><label class="form-label">Full name</label><input class="form-control" name="full_name" /></div>
              <div class="col-12 col-md-6"><label class="form-label">Headline</label><input class="form-control" name="headline" /></div>
              <div class="col-12 col-md-6"><label class="form-label">Email</label><input class="form-control" name="primary_email" type="email"/></div>
              <div class="col-12 col-md-6"><label class="form-label">Phone</label><input class="form-control" name="primary_phone"/></div>
              <div class="col-12 col-md-6"><label class="form-label">Location</label><input class="form-control" name="location"/></div>
              <div class="col-12 col-md-6"><label class="form-label">Primary role</label><input class="form-control" name="primary_role"/></div>
              <div class="col-12 col-md-6"><label class="form-label">Seniority</label><input class="form-control" name="seniority"/></div>
              <div class="col-12 col-md-6"><label class="form-label">LinkedIn</label><input class="form-control" name="linkedin"/></div>
              <div class="col-12 col-md-6"><label class="form-label">GitHub</label><input class="form-control" name="github"/></div>
              <div class="col-12 col-md-6"><label class="form-label">Portfolio</label><input class="form-control" name="portfolio"/></div>
              <div class="col-12"><label class="form-label">One-liner summary</label><textarea class="form-control" name="summary_one_liner" rows="2"></textarea></div>

              <div class="col-12">
                <label class="form-label">Highlights (JSON array)</label>
                <textarea class="form-control font-monospace" name="summary_highlights" rows="3" placeholder='["Highlight 1","Highlight 2"]'></textarea>
                <div class="form-text">Provide a JSON array of strings.</div>
              </div>

              <div class="col-12 d-flex gap-2">
                <button class="btn btn-dark" type="submit" id="saveBtn"><i class="bi bi-save me-2"></i>Save</button>
                <button class="btn btn-outline-dark" type="button" id="resetBtn"><i class="bi bi-arrow-counterclockwise me-2"></i>Reset</button>
              </div>
            </form>
          `)}

          ${card("Skills", `<div id="skillsWrap" class="d-flex flex-wrap gap-2"></div><div id="skillsEmpty" class="text-muted small d-none">No skills extracted.</div>`)}
          ${card("Experience", `<div id="expWrap"></div><div id="expEmpty" class="text-muted small d-none">No experience extracted.</div>`)}
          ${card("Education", `<div id="eduWrap"></div><div id="eduEmpty" class="text-muted small d-none">No education extracted.</div>`)}
        </div>
      </div>
    `;

    const resp = await ParsePro.apiFetch(`/candidates/${id}/`, { method: "GET" });
    const data = await resp.json().catch(() => null);
    const c = data?.data ? data.data : data;

    $("candName").textContent = c.full_name || "Candidate";
    $("candMetaLine").textContent =
      `${c.primary_role || "—"} • ${c.seniority || "—"} • Confidence ${typeof c.overall_confidence === "number" ? c.overall_confidence.toFixed(2) : "—"}`;

    const setText = (k, v) => { $(k).textContent = v; };
    const setLink = (k, url) => { const a = $(k); a.href = url || "#"; a.textContent = url || "—"; };

    setText("cEmail", c.primary_email || "—");
    setText("cPhone", c.primary_phone || "—");
    setText("cLocation", c.location || "—");
    setLink("cLinkedIn", c.linkedin);
    setLink("cGitHub", c.github);
    setLink("cPortfolio", c.portfolio);

    setText("cRole", c.primary_role || "—");
    setText("cSeniority", c.seniority || "—");
    setText("cConf", typeof c.overall_confidence === "number" ? c.overall_confidence.toFixed(2) : "—");
    setText("cOneLiner", c.summary_one_liner || "—");

    // skills
    const skills = c.skills || [];
    const sw = $("skillsWrap"); sw.innerHTML = "";
    $("skillsEmpty").classList.toggle("d-none", skills.length > 0);
    skills.forEach(s => sw.insertAdjacentHTML("beforeend", `<span class="badge text-bg-light border">${esc(s.name)}</span>`));

    // experience
    const exp = c.experience || [];
    const ew = $("expWrap"); ew.innerHTML = "";
    $("expEmpty").classList.toggle("d-none", exp.length > 0);
    exp.forEach(e => {
      ew.insertAdjacentHTML("beforeend", `
        <div class="border rounded-3 p-3 mb-2 bg-white">
          <div class="fw-semibold">${esc(e.title || "—")} <span class="text-muted">•</span> ${esc(e.company || "—")}</div>
          <div class="small text-muted">${esc(e.start_date || "")}${e.end_date ? " - " + esc(e.end_date) : (e.is_current ? " - Present" : "")}</div>
          ${(e.bullets || []).length
            ? `<ul class="small mt-2 mb-0">${(e.bullets || []).slice(0,5).map(b => `<li>${esc(b)}</li>`).join("")}</ul>`
            : `<div class="small text-muted mt-2">No bullets.</div>`}
        </div>
      `);
    });

    // education
    const edu = c.education || [];
    const uw = $("eduWrap"); uw.innerHTML = "";
    $("eduEmpty").classList.toggle("d-none", edu.length > 0);
    edu.forEach(ed => {
      uw.insertAdjacentHTML("beforeend", `
        <div class="border rounded-3 p-3 mb-2 bg-white">
          <div class="fw-semibold">${esc(ed.degree || "—")} <span class="text-muted">•</span> ${esc(ed.institution || "—")}</div>
          <div class="small text-muted">${esc(ed.field_of_study || "")}</div>
          <div class="small text-muted">${esc(ed.start_date || "")}${ed.end_date ? " - " + esc(ed.end_date) : ""}</div>
        </div>
      `);
    });

    // edit form
    const form = $("editForm");
    const alert = $("editAlert");
    const saveBtn = $("saveBtn");

    function fillForm() {
      form.full_name.value = c.full_name || "";
      form.headline.value = c.headline || "";
      form.primary_email.value = c.primary_email || "";
      form.primary_phone.value = c.primary_phone || "";
      form.location.value = c.location || "";
      form.primary_role.value = c.primary_role || "";
      form.seniority.value = c.seniority || "";
      form.linkedin.value = c.linkedin || "";
      form.github.value = c.github || "";
      form.portfolio.value = c.portfolio || "";
      form.summary_one_liner.value = c.summary_one_liner || "";
      form.summary_highlights.value = JSON.stringify(c.summary_highlights || [], null, 2);
    }

    function payloadFromForm() {
      let highlights = [];
      const raw = form.summary_highlights.value.trim();
      if (raw) {
        try { const p = JSON.parse(raw); if (Array.isArray(p)) highlights = p; } catch {}
      }
      return {
        full_name: form.full_name.value.trim() || null,
        headline: form.headline.value.trim() || null,
        primary_email: form.primary_email.value.trim() || null,
        primary_phone: form.primary_phone.value.trim() || null,
        location: form.location.value.trim() || null,
        primary_role: form.primary_role.value.trim() || null,
        seniority: form.seniority.value.trim() || null,
        linkedin: form.linkedin.value.trim() || null,
        github: form.github.value.trim() || null,
        portfolio: form.portfolio.value.trim() || null,
        summary_one_liner: form.summary_one_liner.value.trim() || null,
        summary_highlights: highlights,
      };
    }

    fillForm();
    $("resetBtn").addEventListener("click", fillForm);

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      alert.innerHTML = "";
      saveBtn.disabled = true;

      try {
        const resp = await ParsePro.apiFetch(`/candidates/${id}/`, { method: "PATCH", body: JSON.stringify(payloadFromForm()) });
        const out = await resp.json().catch(() => null);

        if (!resp.ok) {
          ParsePro.renderAlert(alert, out?.detail || out?.error?.message || "Save failed", "danger");
          return;
        }

        ParsePro.renderAlert(alert, "Saved successfully. Audit log recorded.", "success");
        ParsePro.toast("Candidate", "Saved", "success");
        setTimeout(() => window.location.reload(), 500);
      } catch (err) {
        ParsePro.renderAlert(alert, err.message || "Save failed", "danger");
      } finally {
        saveBtn.disabled = false;
      }
    });
  }

  async function renderCandidateEditLogs(r) {
    const id = r.candidateId;
    r.el.innerHTML = `
      <div class="d-flex align-items-center justify-content-between mb-3">
        <div>
          <h1 class="h3 mb-1">Edit History</h1>
          <div class="text-muted">Audit trail for candidate edits.</div>
        </div>
        <div class="d-flex gap-2">
          <a class="btn btn-outline-dark" href="/candidates/${id}/"><i class="bi bi-person me-2"></i>Back to Candidate</a>
          <a class="btn btn-dark" href="/candidates/"><i class="bi bi-arrow-left me-2"></i>Back</a>
        </div>
      </div>

      ${card("Audit Log", `
        <div class="text-muted d-none" id="logsEmpty">No edits recorded.</div>
        <div class="table-responsive">
          <table class="table align-middle">
            <thead><tr><th>Edited At</th><th>Edited By</th><th>Changes</th></tr></thead>
            <tbody id="logsBody"></tbody>
          </table>
        </div>
      `)}
    `;

    const resp = await ParsePro.apiFetch(`/candidates/${id}/edit-logs/`, { method: "GET" });
    const data = await resp.json().catch(() => null);
    const logs = data?.data || [];

    const body = $("logsBody");
    body.innerHTML = "";
    $("logsEmpty").classList.toggle("d-none", logs.length > 0);

    for (const l of logs) {
      const by = l.edited_by?.username || "—";
      const changes = l.changes || {};
      const changeHtml = Object.keys(changes).map(k => {
        const c = changes[k];
        return `<div class="small"><span class="fw-semibold">${esc(k)}</span>: <span class="text-muted">${esc(String(c.from ?? ""))}</span> → <span>${esc(String(c.to ?? ""))}</span></div>`;
      }).join("");

      body.insertAdjacentHTML("beforeend", `
        <tr>
          <td class="small">${fmtDate(l.edited_at)}</td>
          <td class="small">${esc(by)}</td>
          <td>${changeHtml}</td>
        </tr>
      `);
    }
  }

  // ---------------- Profile / About
  async function renderProfile(r) {
    r.el.innerHTML = `
      <div class="mb-3">
        <h1 class="h3 mb-1">Profile</h1>
        <div class="text-muted">Session settings and token storage preferences.</div>
      </div>

      <div class="row g-3">
        <div class="col-12 col-xl-6">
          ${card("Account", `
            <dl class="row small mb-0">
              <dt class="col-4 text-muted">Username</dt><dd class="col-8" id="pUsername">—</dd>
              <dt class="col-4 text-muted">Storage</dt><dd class="col-8" id="pStorage">—</dd>
            </dl>
            <hr class="my-3">
            <button class="btn btn-outline-dark" id="switchStorageBtn"><i class="bi bi-arrow-left-right me-2"></i>Switch storage mode</button>
            <div class="form-text mt-2">Switch between localStorage (persistent) and sessionStorage (session-only).</div>
          `)}
        </div>

        <div class="col-12 col-xl-6">
          ${card("Security", `
            <p class="text-muted small mb-3">
              JWT tokens are stored in browser storage for demo simplicity. For production, use HttpOnly cookies and CSRF protections.
            </p>
            <a href="/logout/" class="btn btn-dark"><i class="bi bi-box-arrow-right me-2"></i>Logout</a>
          `)}
        </div>
      </div>
    `;

    const u = ParsePro.getUser();
    $("pUsername").textContent = u.username || "—";
    $("pStorage").textContent =
      ParsePro.storage.mode() === "session" ? "sessionStorage (session-only)" : "localStorage (persistent)";

    $("switchStorageBtn").addEventListener("click", () => {
      const current = ParsePro.storage.mode();
      const next = current === "session" ? "local" : "session";

      const tokens = ParsePro.getTokens();
      const user = ParsePro.getUser();

      ParsePro.storage.setMode(next);
      ParsePro.storage.clearAuth();
      ParsePro.setTokens(tokens.access, tokens.refresh);
      ParsePro.setUser(user);

      ParsePro.toast("Profile", `Storage mode switched to ${next}`, "success");
      window.location.reload();
    });
  }

  async function renderAbout(r) {
    r.el.innerHTML = `
      <div class="mb-3">
        <h1 class="h3 mb-1">About / Disclaimer / Privacy</h1>
        <div class="text-muted">Scope, data handling, and limitations.</div>
      </div>

      ${card("Disclaimer", `
        <ul class="mb-0">
          <li>This tool assists in organizing resume information and does not make hiring decisions.</li>
          <li>Extraction, classification and summaries are probabilistic and may contain errors.</li>
          <li>Users should validate key details before decisions.</li>
        </ul>
      `)}

      ${card("Data usage / privacy", `
        <ul class="mb-0">
          <li>Resumes may include personally identifiable information (PII) such as email/phone.</li>
          <li>Resume text and parsing outputs are stored for auditability and evaluation.</li>
          <li>OpenRouter is used for GenAI extraction/classification/summary; align with compliance requirements.</li>
        </ul>
      `)}

      ${card("Support", `
        <p class="mb-0">For project support, contact the project owner/admin. Rotate keys regularly in non-demo deployments.</p>
      `)}
    `;
  }

  // ---------------- Router
  document.addEventListener("DOMContentLoaded", async () => {
    const r = root();
    if (!r) return;

    try {
      if (r.page === "dashboard") return await renderDashboard(r);
      if (r.page === "upload") return await renderUpload(r);
      if (r.page === "documents") return await renderDocuments(r);

      if (r.page === "parse_runs") return await renderParseRuns(r);
      if (r.page === "parse_run_detail") return await renderParseRunDetail(r);

      if (r.page === "candidates_list") return await renderCandidatesList(r);
      if (r.page === "candidate_detail") return await renderCandidateDetail(r);
      if (r.page === "candidate_edit_logs") return await renderCandidateEditLogs(r);

      if (r.page === "profile") return await renderProfile(r);
      if (r.page === "about") return await renderAbout(r);

      r.el.innerHTML = `<div class="alert alert-warning">Unknown page: ${esc(r.page)}</div>`;
    } catch (err) {
      ParsePro.toast("UI Error", err.message || "Failed to load page", "danger");
      r.el.innerHTML = `<div class="alert alert-danger">Failed to load page. See console for details.</div>`;
      console.error(err);
    }
  });
})();


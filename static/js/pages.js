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
        <div class="text-muted">Upload PDF/DOCX files. The system extracts, normalizes, validates, classifies, and summarizes.</div>
      </div>

      <div class="row g-3">
        <div class="col-12 col-xl-6">
          ${card("Upload", `
            <div id="uploadAlert"></div>
            <form id="uploadForm">
              <div class="mb-3">
                <label class="form-label fw-semibold">
                  <i class="bi bi-file-earmark-arrow-up me-1"></i>
                  Select Resume Files
                </label>
                <div class="position-relative">
                  <input type="file" class="form-control" name="file" id="fileInput" accept=".pdf,.doc,.docx,.txt" multiple required>
                  <div class="form-text">
                    <i class="bi bi-info-circle me-1"></i>
                    Supported formats: PDF, DOCX, DOC, TXT (max 10MB each)
                  </div>
                </div>
              </div>

              <!-- File Preview List -->
              <div class="mb-3 d-none" id="filePreviewSection">
                <div class="d-flex align-items-center justify-content-between mb-2">
                  <label class="form-label fw-semibold mb-0">
                    <i class="bi bi-files me-1"></i>
                    Selected Files
                  </label>
                  <button type="button" class="btn btn-sm btn-outline-danger" id="clearFilesBtn" title="Remove all files">
                    <i class="bi bi-x-circle"></i>
                    Clear All
                  </button>
                </div>
                <div class="border rounded bg-white" style="max-height: 250px; overflow-y: auto;">
                  <div id="filePreviewList" class="list-group list-group-flush"></div>
                </div>
                <div class="d-flex gap-2 mt-2 align-items-center">
                  <span id="fileCountBadge" class="badge text-bg-primary">0 files</span>
                  <span id="totalSizeBadge" class="badge text-bg-secondary">0 MB</span>
                  <span class="text-muted small flex-grow-1 text-end" id="fileWarning"></span>
                </div>
              </div>

              <div class="form-check mb-3">
                <input class="form-check-input" type="checkbox" id="bulkMode" checked>
                <label class="form-check-label" for="bulkMode">
                  <strong>Bulk upload mode</strong>
                </label>
                <div class="form-text">Process multiple files in one request (max 100 files). Recommended for better efficiency.</div>
              </div>

              <div class="form-check mb-3">
                <input class="form-check-input" type="checkbox" id="syncMode">
                <label class="form-check-label" for="syncMode">Run synchronously (demo/testing)</label>
                <div class="form-text">Default is async with Celery. Sync provides immediate results but may timeout for large files.</div>
              </div>

              <div class="mb-3">
                <button class="btn btn-outline-secondary btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#requirementsCollapse" aria-expanded="false" aria-controls="requirementsCollapse">
                  <i class="bi bi-funnel me-1"></i>Set Requirements (Optional)
                </button>
                <div class="collapse mt-2" id="requirementsCollapse">
                  <div class="card card-body bg-light">
                    <small class="text-muted mb-2 d-block">
                      <i class="bi bi-filter-circle me-1"></i>
                      Only candidates meeting these requirements will be kept. Others will be discarded.
                    </small>
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
                        <strong>Use AI Validation</strong> (Recommended)
                      </label>
                      <div class="form-text small">Uses AI for semantic matching (e.g., "Software Developer" matches "Software Engineer"). Disable for faster string matching.</div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="d-flex gap-2">
                <button class="btn btn-dark flex-grow-1" type="submit" id="uploadBtn">
                  <i class="bi bi-upload me-2"></i>
                  <span id="uploadBtnText">Upload and Parse</span>
                </button>
              </div>
            </form>
          `)}
        </div>

        <div class="col-12 col-xl-6">
          ${card("Upload Progress", `
            <div class="small text-muted mb-3">
              <i class="bi bi-clock-history me-1"></i>
              This panel updates in real-time as files are processed.
            </div>

            <!-- Overall Upload Progress -->
            <div class="mb-3 d-none" id="uploadProgressSection">
              <label class="form-label small fw-semibold">Overall Progress</label>
              <div class="progress mb-2" style="height: 24px;">
                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                     id="overallProgressBar" 
                     role="progressbar" 
                     style="width: 0%">
                  <span id="overallProgressText">0%</span>
                </div>
              </div>
              <div class="small text-muted" id="uploadStatusText">Uploading...</div>
            </div>

            <!-- Single File Parse Status -->
            <div id="singleFileStatus">
              <div class="d-flex align-items-center gap-2 mb-2">
                <span class="text-muted small">Parse Run ID:</span>
                <span class="fw-semibold" id="runId">—</span>
              </div>

              <div class="d-flex align-items-center gap-2 mb-3">
                <span class="text-muted small">Status:</span>
                <span class="badge text-bg-secondary" id="runStatus">—</span>
              </div>

              <div class="progress mb-3 d-none" id="runProgressWrap">
                <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%"></div>
              </div>

              <div class="d-flex gap-2 mb-3">
                <a class="btn btn-outline-dark btn-sm disabled" href="#" id="openRunBtn">
                  <i class="bi bi-file-text me-1"></i>Open Parse Run
                </a>
                <a class="btn btn-dark btn-sm disabled" href="#" id="openCandidateBtn">
                  <i class="bi bi-person me-1"></i>Open Candidate
                </a>
              </div>
            </div>

            <!-- Bulk Upload Results -->
            <div class="d-none" id="bulkResultsSection">
              <div class="mb-3">
                <label class="form-label small fw-semibold">Upload Summary</label>
                <div class="d-flex gap-2" id="bulkSummaryBadges"></div>
              </div>
              <div id="bulkResultsDetails"></div>
            </div>

            <hr class="my-3">
            <ul class="small mb-0 text-muted">
              <li>Duplicate files are automatically detected and linked to existing candidates</li>
              <li>Processing runs in the background - check Parse Runs page for all results</li>
              <li>You'll receive status updates as files complete</li>
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

    // File management state
    let selectedFiles = [];
    const fileInput = $("fileInput");
    
    // Helper function to format file size
    function formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
    }
    
    // Helper function to get file icon based on extension
    function getFileIcon(filename) {
      const ext = filename.split('.').pop().toLowerCase();
      if (ext === 'pdf') return 'bi-file-earmark-pdf-fill text-danger';
      if (ext === 'docx' || ext === 'doc') return 'bi-file-earmark-word-fill text-primary';
      if (ext === 'txt') return 'bi-file-earmark-text-fill text-secondary';
      return 'bi-file-earmark text-secondary';
    }
    
    // Update file preview list
    function updateFilePreview(files) {
      selectedFiles = Array.from(files);
      const previewSection = $("filePreviewSection");
      const previewList = $("filePreviewList");
      const countBadge = $("fileCountBadge");
      const sizeBadge = $("totalSizeBadge");
      const fileWarning = $("fileWarning");
      
      if (selectedFiles.length === 0) {
        previewSection.classList.add("d-none");
        return;
      }
      
      previewSection.classList.remove("d-none");
      
      // Calculate total size
      const totalSize = selectedFiles.reduce((sum, file) => sum + file.size, 0);
      const totalSizeMB = totalSize / (1024 * 1024);
      
      // Update badges
      countBadge.textContent = `${selectedFiles.length} file${selectedFiles.length !== 1 ? 's' : ''}`;
      countBadge.className = selectedFiles.length > 100 ? 'badge text-bg-danger' : 'badge text-bg-primary';
      sizeBadge.textContent = formatFileSize(totalSize);
      
      // Show warning if too many files
      if (selectedFiles.length > 100) {
        fileWarning.innerHTML = '<i class="bi bi-exclamation-triangle-fill text-danger me-1"></i>Maximum 100 files allowed';
      } else if (totalSizeMB > 100) {
        fileWarning.innerHTML = '<i class="bi bi-exclamation-triangle-fill text-warning me-1"></i>Large upload - may take some time';
      } else {
        fileWarning.textContent = '';
      }
      
      // Build file list HTML
      let html = '';
      selectedFiles.forEach((file, index) => {
        const sizeStr = formatFileSize(file.size);
        const isLarge = file.size > 10 * 1024 * 1024; // >10MB
        const icon = getFileIcon(file.name);
        
        html += `
          <div class="list-group-item d-flex align-items-center gap-2 py-2" data-file-index="${index}">
            <i class="bi ${icon} fs-5"></i>
            <div class="flex-grow-1 min-w-0">
              <div class="fw-semibold text-truncate small">${esc(file.name)}</div>
              <div class="text-muted" style="font-size: 0.75rem;">
                ${sizeStr}
                ${isLarge ? '<span class="text-danger ms-1"><i class="bi bi-exclamation-circle"></i> Too large</span>' : ''}
              </div>
            </div>
            <button type="button" class="btn btn-sm btn-outline-danger remove-file-btn" data-file-index="${index}" title="Remove this file">
              <i class="bi bi-x-lg"></i>
            </button>
          </div>
        `;
      });
      
      previewList.innerHTML = html;
      
      // Add remove button handlers
      previewList.querySelectorAll('.remove-file-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          const index = parseInt(btn.dataset.fileIndex);
          removeFile(index);
        });
      });
    }
    
    // Remove a file from the selection
    function removeFile(index) {
      selectedFiles.splice(index, 1);
      
      // Update the file input (we need to create a new FileList)
      const dt = new DataTransfer();
      selectedFiles.forEach(file => dt.items.add(file));
      fileInput.files = dt.files;
      
      updateFilePreview(selectedFiles);
    }
    
    // Clear all files
    $("clearFilesBtn").addEventListener("click", () => {
      selectedFiles = [];
      fileInput.value = '';
      updateFilePreview([]);
    });
    
    // File input change handler
    fileInput.addEventListener("change", (e) => {
      updateFilePreview(e.target.files);
    });

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
        ParsePro.renderAlert(alert, "Please select at least one resume file to upload.", "danger");
        btn.disabled = false;
        return;
      }

      if (bulkMode && files.length > 100) {
        ParsePro.renderAlert(alert, `You've selected ${files.length} files, but the maximum is 100. Please remove some files or split your upload.`, "danger");
        btn.disabled = false;
        return;
      }
      
      // Check for files that are too large (>10MB)
      const oversizedFiles = selectedFiles.filter(f => f.size > 10 * 1024 * 1024);
      if (oversizedFiles.length > 0) {
        const names = oversizedFiles.slice(0, 3).map(f => f.name).join(', ');
        const suffix = oversizedFiles.length > 3 ? ` and ${oversizedFiles.length - 3} more` : '';
        ParsePro.renderAlert(alert, `${oversizedFiles.length} file(s) exceed 10MB: ${names}${suffix}. Please remove them or compress the files.`, "danger");
        btn.disabled = false;
        return;
      }
      
      // Show upload progress UI
      const progressSection = $("uploadProgressSection");
      const progressBar = $("overallProgressBar");
      const progressText = $("overallProgressText");
      const uploadStatusText = $("uploadStatusText");
      const uploadBtnText = $("uploadBtnText");
      
      progressSection.classList.remove("d-none");
      progressBar.style.width = "10%";
      progressText.textContent = "10%";
      uploadStatusText.innerHTML = `<i class="bi bi-cloud-upload me-1"></i>Uploading ${files.length} file${files.length !== 1 ? 's' : ''}...`;
      uploadBtnText.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Uploading...';
      
      // Hide single file status during upload
      $("singleFileStatus").classList.add("d-none");

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
        
        // Update progress to 30% (uploading)
        progressBar.style.width = "30%";
        progressText.textContent = "30%";
        
        const resp = await ParsePro.apiFetch(endpoint, { method: "POST", body: fd });
        
        // Update progress to 60% (processing)
        progressBar.style.width = "60%";
        progressText.textContent = "60%";
        uploadStatusText.innerHTML = '<i class="bi bi-cpu me-1"></i>Processing files...';
        
        const data = await resp.json().catch(() => null);

        if (!resp.ok || !data?.success) {
          progressSection.classList.add("d-none");
          const errorMsg = data?.error?.message || "Upload failed. Please check your files and try again.";
          ParsePro.renderAlert(alert, errorMsg, "danger");
          uploadBtnText.textContent = "Upload and Parse";
          return;
        }
        
        // Complete progress
        progressBar.style.width = "100%";
        progressText.textContent = "100%";
        progressBar.classList.remove("progress-bar-animated");
        uploadStatusText.innerHTML = '<i class="bi bi-check-circle-fill text-success me-1"></i>Upload complete!';

        const payload = data.data || {};
        const userMessage = data.message || '';

        // Handle bulk upload response
        if (bulkMode && files.length > 1) {
          const summary = payload;
          const acceptedCount = summary.accepted?.length || summary.matching || 0;
          const rejectedCount = summary.rejected?.length || summary.rejected || 0;
          const errorCount = summary.errors?.length || 0;
          const total = summary.total || files.length;

          // Show bulk results section
          $("singleFileStatus").classList.add("d-none");
          $("bulkResultsSection").classList.remove("d-none");
          
          // Update summary badges
          const summaryBadges = $("bulkSummaryBadges");
          summaryBadges.innerHTML = `
            <span class="badge text-bg-primary">${total} Total</span>
            <span class="badge text-bg-success">${acceptedCount} Accepted</span>
            ${rejectedCount > 0 ? `<span class="badge text-bg-danger">${rejectedCount} Rejected</span>` : ''}
            ${errorCount > 0 ? `<span class="badge text-bg-warning">${errorCount} Errors</span>` : ''}
          `;

          let alertMessage = userMessage || `Upload completed: ${acceptedCount} candidates ready to review`;
          if (rejectedCount > 0) {
            alertMessage += `, ${rejectedCount} didn't match criteria`;
          }
          if (errorCount > 0) {
            alertMessage += `, ${errorCount} failed to process`;
          }

          ParsePro.renderAlert(alert, alertMessage, errorCount > 0 ? "warning" : "success");

          // Build detailed results display
          const resultsDetails = $("bulkResultsDetails");
          let resultsHtml = '';
          
          // Accepted candidates
          if (summary.accepted && summary.accepted.length > 0) {
            resultsHtml += `
              <div class="mb-3">
                <div class="d-flex align-items-center gap-2 mb-2">
                  <i class="bi bi-check-circle-fill text-success"></i>
                  <strong class="text-success">Accepted Candidates (${summary.accepted.length})</strong>
                </div>
                <div class="list-group list-group-flush border rounded">
            `;
            summary.accepted.forEach(r => {
              const isDuplicate = r.duplicate ? '<span class="badge text-bg-secondary ms-2">Duplicate</span>' : '';
              const candidateLink = r.candidate_id 
                ? `<a href="/candidates/${r.candidate_id}/" class="btn btn-sm btn-outline-dark" target="_blank"><i class="bi bi-box-arrow-up-right me-1"></i>View</a>`
                : '<span class="text-muted small">Processing...</span>';
              
              resultsHtml += `
                <div class="list-group-item d-flex align-items-center gap-2">
                  <i class="bi ${getFileIcon(r.filename)} fs-5"></i>
                  <div class="flex-grow-1 min-w-0">
                    <div class="fw-semibold small text-truncate">${esc(r.filename)}</div>
                    <div class="text-muted" style="font-size: 0.7rem;">
                      ${r.status ? badge(r.status) : ''}
                      ${isDuplicate}
                    </div>
                  </div>
                  ${candidateLink}
                </div>
              `;
            });
            resultsHtml += `</div></div>`;
          }
          
          // Rejected candidates
          if (summary.rejected && summary.rejected.length > 0) {
            resultsHtml += `
              <div class="mb-3">
                <div class="d-flex align-items-center gap-2 mb-2">
                  <i class="bi bi-x-circle-fill text-danger"></i>
                  <strong class="text-danger">Rejected Candidates (${summary.rejected.length})</strong>
                </div>
                <div class="list-group list-group-flush border rounded">
            `;
            summary.rejected.forEach(r => {
              const reasons = Array.isArray(r.discard_reasons) ? r.discard_reasons.join("; ") : "Does not meet requirements";
              resultsHtml += `
                <div class="list-group-item">
                  <div class="d-flex align-items-start gap-2">
                    <i class="bi ${getFileIcon(r.filename)} fs-5 text-danger"></i>
                    <div class="flex-grow-1 min-w-0">
                      <div class="fw-semibold small text-truncate">${esc(r.filename)}</div>
                      <div class="text-danger small mt-1">${esc(reasons)}</div>
                    </div>
                  </div>
                </div>
              `;
            });
            resultsHtml += `</div></div>`;
          }
          
          // Errors
          if (summary.errors && summary.errors.length > 0) {
            resultsHtml += `
              <div class="mb-3">
                <div class="d-flex align-items-center gap-2 mb-2">
                  <i class="bi bi-exclamation-triangle-fill text-warning"></i>
                  <strong class="text-warning">Processing Errors (${summary.errors.length})</strong>
                </div>
                <div class="list-group list-group-flush border rounded">
            `;
            summary.errors.forEach(e => {
              resultsHtml += `
                <div class="list-group-item">
                  <div class="d-flex align-items-start gap-2">
                    <i class="bi ${getFileIcon(e.filename)} fs-5 text-warning"></i>
                    <div class="flex-grow-1 min-w-0">
                      <div class="fw-semibold small text-truncate">${esc(e.filename)}</div>
                      <div class="text-warning small mt-1">${esc(e.error)}</div>
                    </div>
                  </div>
                </div>
              `;
            });
            resultsHtml += `</div></div>`;
          }
          
          resultsDetails.innerHTML = resultsHtml;
          
          // Show requirements info if applied
          if (summary.requirements_applied) {
            const reqKeys = Object.keys(summary.requirements_applied).filter(k => k !== 'use_llm_validation');
            if (reqKeys.length > 0) {
              alert.innerHTML += `
                <div class="mt-2 p-2 bg-info bg-opacity-10 border border-info rounded">
                  <div class="small">
                    <i class="bi bi-filter-circle me-1"></i>
                    <strong>Filters applied:</strong> ${reqKeys.join(', ').replace(/_/g, ' ')}
                  </div>
                </div>
              `;
            }
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
        $("singleFileStatus").classList.remove("d-none");
        $("bulkResultsSection").classList.add("d-none");
        
        if (payload.duplicate) {
          // Complete progress
          setTimeout(() => progressSection.classList.add("d-none"), 2000);
          
          // Check if duplicate was rejected due to requirements
          if (payload.requirements_check === "failed" && payload.rejection_reasons) {
            const reasons = Array.isArray(payload.rejection_reasons) 
              ? payload.rejection_reasons.join(", ") 
              : payload.rejection_reasons;
            ParsePro.renderAlert(alert, `This resume was already uploaded, but it doesn't meet your current filters: ${reasons}`, "danger");
            uploadBtnText.textContent = "Upload and Parse";
            return;
          }
          
          ParsePro.renderAlert(alert, userMessage || "This resume was already uploaded. Showing the existing candidate profile.", "info");
          setRunPanel(payload.parse_run_id, payload.status, payload.candidate_id || null);
          uploadBtnText.textContent = "Upload and Parse";
          setTimeout(() => progressSection.classList.add("d-none"), 2000);
          return;
        }

        // Check if candidate was rejected due to requirements
        if (payload.rejected && payload.rejection_reasons) {
          const reasons = Array.isArray(payload.rejection_reasons) 
            ? payload.rejection_reasons.join(", ") 
            : payload.rejection_reasons;
          ParsePro.renderAlert(alert, `This candidate doesn't match your filters: ${reasons}`, "warning");
          setRunPanel(payload.parse_run_id, payload.status, null);
          uploadBtnText.textContent = "Upload and Parse";
          setTimeout(() => progressSection.classList.add("d-none"), 2000);
          return;
        }

        // Show requirements info if applied and accepted
        if (payload.requirements_applied && payload.accepted) {
          ParsePro.renderAlert(alert, userMessage || "Resume uploaded! This candidate meets all your requirements and is being processed.", "success");
        } else {
          ParsePro.renderAlert(alert, userMessage || "Resume uploaded successfully! Processing has started.", "success");
        }

        setRunPanel(payload.parse_run_id, payload.status, payload.candidate_id || null);

        if (resp.status === 202 || ["queued", "processing"].includes(payload.status)) {
          await poll(payload.parse_run_id);
        } else {
          uploadBtnText.textContent = "Upload and Parse";
          setTimeout(() => progressSection.classList.add("d-none"), 2000);
        }
      } catch (err) {
        progressSection.classList.add("d-none");
        const errorMsg = err.message || "Upload failed. Please check your connection and try again.";
        ParsePro.renderAlert(alert, errorMsg, "danger");
        uploadBtnText.textContent = "Upload and Parse";
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
              <tr><th>ID</th><th>Filename</th><th>MIME</th><th>Size</th><th>Hash</th><th>Extract</th><th>Created</th><th></th></tr>
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
        <tr data-doc-id="${d.id}">
          <td class="mono">${d.id}</td>
          <td>${esc(d.original_filename || "—")}</td>
          <td class="small">${esc(d.mime_type || "—")}</td>
          <td class="small">${fmtBytes(d.file_size)}</td>
          <td class="small mono">${esc((d.file_hash || "").slice(0, 12) || "—")}</td>
          <td class="small">${esc(d.extraction_method || "—")}</td>
          <td class="small">${fmtDate(d.created_at)}</td>
          <td class="text-end">
            <button class="btn btn-outline-danger btn-sm delete-doc-btn" data-id="${d.id}" title="Delete"><i class="bi bi-trash"></i></button>
          </td>
        </tr>
      `);
    }

    // Attach delete handlers
    body.querySelectorAll(".delete-doc-btn").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();
        const id = btn.dataset.id;
        const filename = body.querySelector(`tr[data-doc-id="${id}"] td:nth-child(2)`)?.textContent?.trim() || `#${id}`;
        if (!confirm(`Delete document "${filename}"? This will also delete all associated parse runs and candidates.`)) return;
        btn.disabled = true;
        try {
          const resp = await ParsePro.apiFetch(`/resume-documents/${id}/`, { method: "DELETE" });
          if (resp.ok) {
            const data = await resp.json().catch(() => null);
            const msg = data?.data?.message || `Document deleted`;
            ParsePro.toast("Deleted", msg, "success");
            const row = body.querySelector(`tr[data-doc-id="${id}"]`);
            if (row) row.remove();
            // Update empty state
            $("docsEmpty").classList.toggle("d-none", body.children.length > 0);
          } else {
            const data = await resp.json().catch(() => null);
            ParsePro.toast("Error", data?.error?.message || "Delete failed", "danger");
          }
        } catch (err) {
          ParsePro.toast("Error", err.message || "Delete failed", "danger");
        } finally {
          btn.disabled = false;
        }
      });
    });
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
          <tr data-run-id="${x.id}">
            <td class="mono">${x.id}</td>
            <td>${badge(x.status)}</td>
            <td class="small">${esc(x.model_name || "—")}</td>
            <td class="small">${x.latency_ms ? x.latency_ms + " ms" : "—"}</td>
            <td class="small">${fmtDate(x.created_at)}</td>
            <td class="text-end">
              <a class="btn btn-outline-dark btn-sm" href="/resumes/parse-runs/${x.id}/">Open</a>
              <button class="btn btn-outline-danger btn-sm ms-1 delete-run-btn" data-id="${x.id}" title="Delete"><i class="bi bi-trash"></i></button>
            </td>
          </tr>
        `);
      }

      // Attach delete handlers
      body.querySelectorAll(".delete-run-btn").forEach(btn => {
        btn.addEventListener("click", async (e) => {
          e.preventDefault();
          const id = btn.dataset.id;
          if (!confirm(`Delete parse run #${id}? This will also delete any associated candidate.`)) return;
          btn.disabled = true;
          try {
            const resp = await ParsePro.apiFetch(`/parse-runs/${id}/`, { method: "DELETE" });
            if (resp.ok) {
              ParsePro.toast("Deleted", `Parse run #${id} deleted`, "success");
              const row = body.querySelector(`tr[data-run-id="${id}"]`);
              if (row) row.remove();
            } else {
              const data = await resp.json().catch(() => null);
              ParsePro.toast("Error", data?.error?.message || "Delete failed", "danger");
            }
          } catch (err) {
            ParsePro.toast("Error", err.message || "Delete failed", "danger");
          } finally {
            btn.disabled = false;
          }
        });
      });
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
          <button class="btn btn-outline-danger" id="deleteRunBtn"><i class="bi bi-trash me-2"></i>Delete</button>
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

    $("deleteRunBtn").addEventListener("click", async () => {
      if (!confirm(`Delete parse run #${runId}? This will also delete any associated candidate.`)) return;
      const btn = $("deleteRunBtn");
      btn.disabled = true;
      try {
        const resp = await ParsePro.apiFetch(`/parse-runs/${runId}/`, { method: "DELETE" });
        if (resp.ok) {
          ParsePro.toast("Deleted", `Parse run #${runId} deleted`, "success");
          window.location.href = "/resumes/parse-runs/";
        } else {
          const data = await resp.json().catch(() => null);
          ParsePro.toast("Error", data?.error?.message || "Delete failed", "danger");
        }
      } catch (err) {
        ParsePro.toast("Error", err.message || "Delete failed", "danger");
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


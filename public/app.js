// The Reading Room - Library Operations & DBMS Client Controller
document.addEventListener("DOMContentLoaded", () => {
  // Navigation tabs
  const navItems = document.querySelectorAll(".nav-item");
  const tabPanes = document.querySelectorAll(".tab-pane");
  const crumbPage = document.getElementById("topbar-crumb");

  // Dynamic Date Header
  updateDateHeader();

  // Load initial data
  loadAllData();

  // Tab switching
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const tabId = item.getAttribute("data-tab");
      switchTab(tabId);
    });
  });

  // Jump from stat cards
  document.querySelectorAll(".stat-card[data-jump]").forEach(card => {
    card.addEventListener("click", () => {
      const target = card.getAttribute("data-jump");
      switchTab(target);
    });
  });

  function switchTab(tabId) {
    navItems.forEach(nav => nav.classList.toggle("active", nav.getAttribute("data-tab") === tabId));
    tabPanes.forEach(pane => pane.classList.toggle("active", pane.id === `pane-${tabId}`));
    
    const activeLabel = document.querySelector(`.nav-item[data-tab="${tabId}"] .nav-label`);
    if (activeLabel) {
      crumbPage.textContent = activeLabel.textContent.toUpperCase();
    }

    if (tabId === "catalog") loadBooks();
    if (tabId === "members") loadMembers();
    if (tabId === "circulation") loadCirculation();
    if (tabId === "reservations") loadReservations();
    if (tabId === "fines") loadFines();
    if (tabId === "digital") loadDigitalAccess();
    if (tabId === "overview") loadOverview();
  }

  function updateDateHeader() {
    const now = new Date();
    const options = { weekday: 'long', month: 'long', day: 'numeric' };
    const dateStr = now.toLocaleDateString('en-US', options).toUpperCase();
    const headerEl = document.getElementById("current-date-header");
    if (headerEl) {
      headerEl.textContent = `${dateStr} · DAILY DESK`;
    }
  }

  // API Call helper
  async function fetchApi(endpoint, options = {}) {
    try {
      const res = await fetch(endpoint, {
        headers: { "Content-Type": "application/json" },
        ...options
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Server request failed");
      }
      return data;
    } catch (err) {
      showToast(err.message || "Network error", true);
      throw err;
    }
  }

  // Load all overview and desk stats
  async function loadOverview() {
    try {
      const res = await fetchApi("/api/stats");
      if (res.success) {
        const d = res.data;
        document.getElementById("kpi-titles").textContent = d.titles_count;
        document.getElementById("kpi-copies-sub").textContent = `${d.total_copies} copies across editions`;
        document.getElementById("kpi-available").textContent = d.available_copies;
        document.getElementById("kpi-loans-sub").textContent = `${d.active_loans} active loans`;
        document.getElementById("kpi-members").textContent = d.active_members;
        document.getElementById("kpi-holds-sub").textContent = `${d.waiting_holds} holds waiting`;
        document.getElementById("kpi-fines").textContent = `₹${d.outstanding_fines.toFixed(2)}`;
        document.getElementById("kpi-overdue-sub").textContent = `${d.overdue_loans} overdue loans`;

        // Side badges
        document.getElementById("badge-catalog-count").textContent = d.titles_count;
        document.getElementById("badge-members-count").textContent = d.active_members;
        document.getElementById("badge-holds-count").textContent = d.waiting_holds;

        // Right Forest Card stats
        document.getElementById("forest-digital-count").textContent = d.digital_visits;
        document.getElementById("forest-copies-ratio").textContent = `${d.available_copies} of ${d.total_copies}`;
      }

      // Load activity ledger feed
      const actRes = await fetchApi("/api/activity");
      if (actRes.success) {
        renderActivityFeed(actRes.data);
      }
    } catch (e) {
      console.error(e);
    }
  }

  function renderActivityFeed(items) {
    const container = document.getElementById("ledger-feed-list");
    if (!items || items.length === 0) {
      container.innerHTML = `<div class="empty-state">No recent desk events recorded.</div>`;
      return;
    }

    container.innerHTML = items.map(item => {
      let iconClass = "loan";
      let iconSvg = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>`;

      if (item.category === "Reservation") {
        iconClass = "reservation";
        iconSvg = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path></svg>`;
      } else if (item.category === "Return") {
        iconClass = "return";
        iconSvg = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
      } else if (item.category === "Digital Access") {
        iconClass = "digital";
        iconSvg = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>`;
      }

      return `
        <div class="ledger-row">
          <div class="ledger-icon ${iconClass}">
            ${iconSvg}
          </div>
          <div class="ledger-content">
            <div class="ledger-headline">
              <strong>${escapeHtml(item.member_name)}</strong> ${escapeHtml(item.action_text)}
            </div>
            <div class="ledger-sub">${escapeHtml(item.category)}</div>
          </div>
          <div class="ledger-time">${escapeHtml(item.event_time)}</div>
        </div>
      `;
    }).join("");
  }

  // BOOKS / CATALOG
  async function loadBooks() {
    const q = document.getElementById("catalog-search").value;
    const genre = document.getElementById("catalog-genre-filter").value;
    const res = await fetchApi(`/api/books?q=${encodeURIComponent(q)}&genre=${encodeURIComponent(genre)}`);
    const tbody = document.getElementById("books-tbody");
    
    if (!res.data || res.data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No matching titles in catalog.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.data.map(b => `
      <tr>
        <td><strong>#${b.book_id}</strong></td>
        <td>
          <div style="font-weight: 600; font-size: 0.9rem;">${escapeHtml(b.title)}</div>
          <div style="color: var(--text-muted); font-size: 0.78rem;">${escapeHtml(b.author)}</div>
        </td>
        <td><code>${escapeHtml(b.isbn)}</code></td>
        <td>${escapeHtml(b.genre)}</td>
        <td>${b.publication_year}</td>
        <td><strong>${b.available_copies}</strong> / ${b.total_copies} avail</td>
        <td>
          <span class="status-badge ${b.available_copies > 0 ? 'active' : 'overdue'}">
            ${b.available_copies > 0 ? 'In Stock' : 'Checked Out'}
          </span>
        </td>
        <td>
          <button class="btn-action-small return-btn" onclick="quickBorrow(${b.book_id})" ${b.available_copies <= 0 ? 'disabled' : ''}>
            Loan Out
          </button>
        </td>
      </tr>
    `).join("");
  }

  document.getElementById("catalog-search").addEventListener("input", debounce(loadBooks, 250));
  document.getElementById("catalog-genre-filter").addEventListener("change", loadBooks);

  // MEMBERS
  async function loadMembers() {
    const res = await fetchApi("/api/members");
    const tbody = document.getElementById("members-tbody");
    if (!res.data || res.data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No members found.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.data.map(m => `
      <tr>
        <td><code>${escapeHtml(m.membership_no)}</code></td>
        <td><strong>${escapeHtml(m.full_name)}</strong></td>
        <td>${escapeHtml(m.email)}</td>
        <td>${escapeHtml(m.phone || '—')}</td>
        <td>${m.active_loans_count} book(s)</td>
        <td><strong style="color: ${m.outstanding_fine_total > 0 ? 'var(--accent-red-text)' : 'inherit'}">₹${Number(m.outstanding_fine_total).toFixed(2)}</strong></td>
        <td>${m.joined_date}</td>
        <td>
          <span class="status-badge active">${escapeHtml(m.status)}</span>
        </td>
      </tr>
    `).join("");
  }

  // CIRCULATION
  async function loadCirculation() {
    const res = await fetchApi("/api/circulation");
    const tbody = document.getElementById("circulation-tbody");
    if (!res.data || res.data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No circulation records.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.data.map(c => `
      <tr>
        <td>#${c.loan_id}</td>
        <td>
          <strong>${escapeHtml(c.book_title)}</strong>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(c.book_author)}</div>
        </td>
        <td>
          ${escapeHtml(c.member_name)}
          <div style="font-size: 0.72rem; color: var(--text-muted);">(${escapeHtml(c.membership_no)})</div>
        </td>
        <td>${c.loan_date}</td>
        <td><strong>${c.due_date}</strong></td>
        <td>${c.return_date || '<span style="color: var(--text-muted);">Ongoing</span>'}</td>
        <td>
          <span class="status-badge ${c.status.toLowerCase()}">${c.status}</span>
        </td>
        <td>
          ${c.status !== 'Returned' 
            ? `<button class="btn-action-small return-btn" onclick="returnBook(${c.loan_id})">Log Return</button>`
            : `<span style="font-size: 0.75rem; color: var(--text-muted);">Closed</span>`
          }
        </td>
      </tr>
    `).join("");
  }

  // RESERVATIONS
  async function loadReservations() {
    const res = await fetchApi("/api/reservations");
    const tbody = document.getElementById("reservations-tbody");
    if (!res.data || res.data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No active holds.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.data.map(r => `
      <tr>
        <td>#${r.reservation_id}</td>
        <td><strong>${escapeHtml(r.book_title)}</strong></td>
        <td>${escapeHtml(r.member_name)} <small>(${escapeHtml(r.membership_no)})</small></td>
        <td>${r.reservation_date}</td>
        <td>${escapeHtml(r.notes || 'Hold queue')}</td>
        <td><span class="status-badge ${r.status === 'Waiting' ? 'waiting' : 'returned'}">${r.status}</span></td>
        <td>
          ${r.status === 'Waiting' ? `
            <button class="btn-action-small return-btn" onclick="updateReservationStatus(${r.reservation_id}, 'Fulfilled')">Fulfill</button>
            <button class="btn-action-small" onclick="updateReservationStatus(${r.reservation_id}, 'Cancelled')" style="background:#fee2e2;color:#991b1b;">Cancel</button>
          ` : `<span style="color:var(--text-muted);font-size:0.75rem;">Resolved</span>`}
        </td>
      </tr>
    `).join("");
  }

  // FINES
  async function loadFines() {
    const res = await fetchApi("/api/fines");
    const tbody = document.getElementById("fines-tbody");
    if (!res.data || res.data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No library fines on record.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.data.map(f => `
      <tr>
        <td>#${f.fine_id}</td>
        <td>
          <strong>${escapeHtml(f.member_name)}</strong>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(f.membership_no)}</div>
        </td>
        <td>${escapeHtml(f.book_title || 'Overdue item')}</td>
        <td>${escapeHtml(f.reason)}</td>
        <td><strong style="color: var(--accent-red-text); font-size: 0.95rem;">₹${Number(f.amount).toFixed(2)}</strong></td>
        <td>${f.issued_date}</td>
        <td>
          <span class="status-badge ${f.status === 'Outstanding' ? 'overdue' : 'paid'}">
            ${f.status}
          </span>
        </td>
        <td>
          ${f.status === 'Outstanding' 
            ? `<button class="btn-action-small pay-btn" onclick="payFine(${f.fine_id})">Mark Paid</button>`
            : `<span style="font-size:0.75rem; color: var(--text-muted);">Settled (${f.paid_date || 'Done'})</span>`
          }
        </td>
      </tr>
    `).join("");
  }

  // DIGITAL ACCESS
  async function loadDigitalAccess() {
    const res = await fetchApi("/api/digital-access");
    const tbody = document.getElementById("digital-tbody");
    if (!res.data || res.data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="empty-state">No digital visits logged.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.data.map(d => `
      <tr>
        <td>#${d.access_id}</td>
        <td><strong>${escapeHtml(d.book_title)}</strong> <span style="font-size: 0.75rem; color: var(--text-muted);">by ${escapeHtml(d.book_author)}</span></td>
        <td>${escapeHtml(d.member_name)}</td>
        <td><code>${d.accessed_at}</code></td>
        <td>${escapeHtml(d.device_type)}</td>
        <td>${d.session_minutes} mins</td>
      </tr>
    `).join("");
  }

  // GLOBAL ACTIONS & API CALLS
  window.returnBook = async function(loanId) {
    try {
      const res = await fetchApi("/api/circulation/return", {
        method: "POST",
        body: JSON.stringify({ loan_id: loanId })
      });
      showToast(res.message);
      if (res.fine_generated > 0) {
        showToast(`Late fine of ₹${res.fine_generated.toFixed(2)} assessed.`);
      }
      loadCirculation();
      loadOverview();
    } catch(e) {}
  };

  window.payFine = async function(fineId) {
    try {
      const res = await fetchApi(`/api/fines/${fineId}/pay`, { method: "POST" });
      showToast(res.message);
      loadFines();
      loadOverview();
    } catch(e) {}
  };

  window.updateReservationStatus = async function(resId, status) {
    try {
      const res = await fetchApi(`/api/reservations/${resId}/status`, {
        method: "POST",
        body: JSON.stringify({ status })
      });
      showToast(res.message);
      loadReservations();
      loadOverview();
    } catch(e) {}
  };

  window.quickBorrow = function(bookId) {
    populateLoanSelects();
    document.getElementById("loan-book-select").value = bookId;
    openModal("modal-issue-loan");
  };

  // SQL CONSOLE (DBMS REVIEW)
  const sqlInput = document.getElementById("sql-input");
  const btnExecuteSql = document.getElementById("btn-execute-sql");
  const sqlMetaText = document.getElementById("sql-meta-text");
  const sqlResultsContainer = document.getElementById("sql-results-container");
  const resultRowCount = document.getElementById("result-row-count");

  btnExecuteSql.addEventListener("click", executeSqlQuery);

  // Preset query buttons
  document.querySelectorAll(".btn-chip[data-sql]").forEach(btn => {
    btn.addEventListener("click", () => {
      sqlInput.value = btn.getAttribute("data-sql");
      executeSqlQuery();
    });
  });

  async function executeSqlQuery() {
    const query = sqlInput.value.trim();
    if (!query) return;

    sqlMetaText.textContent = "Executing query in SQLite engine...";
    try {
      const res = await fetchApi("/api/raw-query", {
        method: "POST",
        body: JSON.stringify({ query })
      });

      if (!res.success) {
        sqlMetaText.textContent = `Error: ${res.error}`;
        sqlResultsContainer.innerHTML = `<div class="empty-state" style="color: #dc2626;">${escapeHtml(res.error)}</div>`;
        return;
      }

      sqlMetaText.textContent = `Success in ${res.executionTimeMs} ms (${res.type})`;

      if (res.type === "SELECT") {
        resultRowCount.textContent = `${res.rowCount} row(s)`;
        if (res.rowCount === 0) {
          sqlResultsContainer.innerHTML = `<div class="empty-state">Query returned 0 rows.</div>`;
          return;
        }

        const headers = res.columns.map(c => `<th>${escapeHtml(c)}</th>`).join("");
        const rows = res.rows.map(row => {
          const cells = res.columns.map(c => `<td>${escapeHtml(String(row[c] !== null && row[c] !== undefined ? row[c] : 'NULL'))}</td>`).join("");
          return `<tr>${cells}</tr>`;
        }).join("");

        sqlResultsContainer.innerHTML = `
          <table class="data-table">
            <thead><tr>${headers}</tr></thead>
            <tbody>${rows}</tbody>
          </table>
        `;
      } else {
        resultRowCount.textContent = `${res.affectedRows} affected`;
        sqlResultsContainer.innerHTML = `<div class="empty-state" style="color: #059669;">${res.message}</div>`;
        loadOverview(); // Refresh stats if data was modified
      }
    } catch(err) {
      sqlMetaText.textContent = `Query execution failed`;
      sqlResultsContainer.innerHTML = `<div class="empty-state" style="color: #dc2626;">${escapeHtml(err.message)}</div>`;
    }
  }

  // Reset database state button
  document.getElementById("btn-reset-db-state").addEventListener("click", async () => {
    if (confirm("Reset SQLite database to original initial demo records?")) {
      const res = await fetchApi("/api/reset-db", { method: "POST" });
      showToast(res.message);
      loadAllData();
      executeSqlQuery();
    }
  });

  // MODALS HANDLING
  function openModal(id) {
    document.getElementById(id).classList.add("open");
  }

  function closeModal(id) {
    document.getElementById(id).classList.remove("open");
  }

  document.querySelectorAll(".modal-close, .modal-cancel").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.target.closest(".modal-backdrop").classList.remove("open");
    });
  });

  // Modal Triggers
  document.getElementById("btn-open-add-book").addEventListener("click", () => openModal("modal-add-book"));
  document.getElementById("btn-open-add-member").addEventListener("click", () => openModal("modal-add-member"));
  
  document.getElementById("btn-quick-new-loan").addEventListener("click", () => {
    populateLoanSelects();
    openModal("modal-issue-loan");
  });

  document.getElementById("btn-open-issue-loan").addEventListener("click", () => {
    populateLoanSelects();
    openModal("modal-issue-loan");
  });

  document.getElementById("btn-forest-loan").addEventListener("click", () => {
    populateLoanSelects();
    openModal("modal-issue-loan");
  });

  document.getElementById("btn-open-add-reservation").addEventListener("click", () => {
    populateReservationSelects();
    openModal("modal-add-reservation");
  });

  document.getElementById("btn-open-digital-read").addEventListener("click", () => {
    populateDigitalSelects();
    openModal("modal-digital-access");
  });

  document.getElementById("btn-forest-digital").addEventListener("click", () => {
    populateDigitalSelects();
    openModal("modal-digital-access");
  });

  async function populateLoanSelects() {
    const booksRes = await fetchApi("/api/books");
    const membersRes = await fetchApi("/api/members");

    const bookSel = document.getElementById("loan-book-select");
    const memberSel = document.getElementById("loan-member-select");

    bookSel.innerHTML = booksRes.data
      .filter(b => b.available_copies > 0)
      .map(b => `<option value="${b.book_id}">${escapeHtml(b.title)} (${b.available_copies} available)</option>`)
      .join("");

    memberSel.innerHTML = membersRes.data
      .map(m => `<option value="${m.member_id}">${escapeHtml(m.full_name)} (${m.membership_no})</option>`)
      .join("");
  }

  async function populateReservationSelects() {
    const booksRes = await fetchApi("/api/books");
    const membersRes = await fetchApi("/api/members");

    document.getElementById("reservation-book-select").innerHTML = booksRes.data
      .map(b => `<option value="${b.book_id}">${escapeHtml(b.title)}</option>`)
      .join("");

    document.getElementById("reservation-member-select").innerHTML = membersRes.data
      .map(m => `<option value="${m.member_id}">${escapeHtml(m.full_name)} (${m.membership_no})</option>`)
      .join("");
  }

  async function populateDigitalSelects() {
    const booksRes = await fetchApi("/api/books");
    const membersRes = await fetchApi("/api/members");

    document.getElementById("digital-book-select").innerHTML = booksRes.data
      .map(b => `<option value="${b.book_id}">${escapeHtml(b.title)}</option>`)
      .join("");

    document.getElementById("digital-member-select").innerHTML = membersRes.data
      .map(m => `<option value="${m.member_id}">${escapeHtml(m.full_name)}</option>`)
      .join("");
  }

  // Form Submissions
  document.getElementById("form-add-book").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const payload = Object.fromEntries(formData.entries());
    const res = await fetchApi("/api/books", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    showToast(res.message);
    closeModal("modal-add-book");
    e.target.reset();
    loadBooks();
    loadOverview();
  });

  document.getElementById("form-add-member").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const payload = Object.fromEntries(formData.entries());
    const res = await fetchApi("/api/members", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    showToast(`Member created: ${res.membership_no}`);
    closeModal("modal-add-member");
    e.target.reset();
    loadMembers();
    loadOverview();
  });

  document.getElementById("form-issue-loan").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const payload = Object.fromEntries(formData.entries());
    const res = await fetchApi("/api/circulation/borrow", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    showToast(res.message);
    closeModal("modal-issue-loan");
    e.target.reset();
    loadCirculation();
    loadOverview();
  });

  document.getElementById("form-add-reservation").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const payload = Object.fromEntries(formData.entries());
    const res = await fetchApi("/api/reservations", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    showToast(res.message);
    closeModal("modal-add-reservation");
    e.target.reset();
    loadReservations();
    loadOverview();
  });

  document.getElementById("form-digital-access").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const payload = Object.fromEntries(formData.entries());
    const res = await fetchApi("/api/digital-access", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    showToast(res.message);
    closeModal("modal-digital-access");
    e.target.reset();
    loadDigitalAccess();
    loadOverview();
  });

  function loadAllData() {
    loadOverview();
    loadBooks();
  }

  // Toast notification
  function showToast(msg, isError = false) {
    const toast = document.getElementById("toast");
    toast.textContent = msg;
    toast.style.backgroundColor = isError ? "#991B1B" : "#1A2621";
    toast.classList.add("show");
    setTimeout(() => {
      toast.classList.remove("show");
    }, 3200);
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function debounce(fn, ms) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), ms);
    };
  }
});

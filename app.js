/**
 * KW Planner - Frontend para GitHub Pages
 * Chama a API do backend e exibe saída + links para download dos CSVs.
 */

(function () {
  const apiUrlInput = document.getElementById("apiUrl");
  const apiStatus = document.getElementById("apiStatus");
  const apiStatusText = document.getElementById("apiStatusText");
  const btnRun = document.getElementById("btnRun");
  const runningEl = document.getElementById("running");
  const outputEl = document.getElementById("output");
  const exportsEl = document.getElementById("exports");

  // Se a página estiver em GitHub Pages (seu-usuario.github.io), use a URL da API que você configurar
  const defaultApiUrl = "http://104.131.34.227:5000";
  if (!apiUrlInput.value) {
    apiUrlInput.value = defaultApiUrl;
  }

  let selectedOption = null;

  function getApiBase() {
    const url = (apiUrlInput.value || "").trim();
    if (url) return url.replace(/\/$/, "");
    return ""; // same origin
  }

  function apiFetch(path, options = {}) {
    const base = getApiBase();
    const url = base ? base + path : path;
    return fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
  }

  async function checkHealth() {
    apiStatus.classList.remove("connected", "error");
    apiStatusText.textContent = "Verificando API...";
    try {
      const res = await apiFetch("/api/health");
      if (res.ok) {
        apiStatus.classList.add("connected");
        apiStatusText.textContent = "API conectada";
      } else {
        apiStatus.classList.add("error");
        apiStatusText.textContent = "API respondeu com erro";
      }
    } catch (e) {
      apiStatus.classList.add("error");
      apiStatusText.textContent = "API inacessível. Configure a URL do backend acima.";
    }
  }

  document.querySelectorAll(".card").forEach((card) => {
    card.addEventListener("click", function () {
      const option = parseInt(this.dataset.option, 10);
      document.querySelectorAll(".card").forEach((c) => c.classList.remove("selected"));
      document.querySelectorAll(".card-form").forEach((f) => f.classList.add("hidden"));
      this.classList.add("selected");
      const form = this.querySelector(".card-form");
      if (form) {
        form.classList.remove("hidden");
      }
      selectedOption = option;
      btnRun.disabled = false;
    });
  });

  function getParams() {
    if (!selectedOption) return {};
    const params = {};
    if (selectedOption === 1) {
      params.domain_url = document.getElementById("domain1").value.trim();
      params.include_subdomains = document.getElementById("subdomains1").checked;
    } else if (selectedOption === 2) {
      params.niche = document.getElementById("niche2").value.trim();
    } else if (selectedOption === 3) {
      params.url = document.getElementById("url3").value.trim();
    } else if (selectedOption === 4) {
      params.keyword = document.getElementById("keyword4").value.trim();
    } else if (selectedOption === 5) {
      params.domain_url = document.getElementById("domain5").value.trim();
      params.theme = document.getElementById("theme5").value.trim();
    } else if (selectedOption === 6) {
      params.domain_url = document.getElementById("domain6").value.trim();
      params.include_subdomains = document.getElementById("subdomains6").checked;
    }
    return params;
  }

  function showExports(exports) {
    exportsEl.innerHTML = "";
    if (!exports || exports.length === 0) return;
    const title = document.createElement("p");
    title.textContent = "Downloads:";
    title.style.marginBottom = "0.5rem";
    title.style.fontWeight = "600";
    exportsEl.appendChild(title);
    exports.forEach((item) => {
      const blob = new Blob([csvFromData(item.data)], {
        type: "text/csv;charset=utf-8;",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = item.filename || "export.csv";
      a.textContent = item.filename || "Baixar CSV";
      exportsEl.appendChild(a);
    });
  }

  function csvFromData(data) {
    if (!Array.isArray(data) || data.length === 0) return "";
    const headers = Object.keys(data[0]);
    const rows = data.map((row) =>
      headers.map((h) => JSON.stringify(String(row[h] ?? ""))).join(",")
    );
    const BOM = "\uFEFF";
    return BOM + [headers.join(","), ...rows].join("\r\n");
  }

  btnRun.addEventListener("click", async function () {
    if (!selectedOption) return;
    const params = getParams();
    if (
      (selectedOption <= 6 && selectedOption !== 7 && selectedOption !== 8) &&
      Object.values(params).every((v) => v === "" || v === false)
    ) {
      const need =
        selectedOption === 5
          ? "domain_url e theme"
          : selectedOption === 1 || selectedOption === 6
          ? "domain_url"
          : selectedOption === 2
          ? "niche"
          : selectedOption === 3
          ? "url"
          : "keyword";
      outputEl.textContent = "Preencha os campos obrigatórios: " + need + ".";
      return;
    }
    btnRun.disabled = true;
    runningEl.classList.remove("hidden");
    outputEl.textContent = "Executando... aguarde (pode levar vários minutos).\n";
    exportsEl.innerHTML = "";

    try {
      const res = await apiFetch("/api/analyze", {
        method: "POST",
        body: JSON.stringify({ option: selectedOption, params }),
      });
      const data = await res.json().catch(() => ({}));
      const text = data.output || "";
      const error = data.error || null;
      const exports = data.exports || [];

      outputEl.textContent = text + (error ? "\n\nErro: " + error : "");
      showExports(exports);
    } catch (e) {
      outputEl.textContent =
        "Falha ao chamar a API. Verifique a URL do backend e se o servidor está no ar.\n\n" +
        e.message;
    } finally {
      btnRun.disabled = false;
      runningEl.classList.add("hidden");
    }
  });

  // Verificar API ao carregar e quando mudar a URL
  checkHealth();
  apiUrlInput.addEventListener("blur", checkHealth);
})();

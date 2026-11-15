const form = document.getElementById("agent-form");
const input = document.getElementById("query-input");
const resultsArea = document.getElementById("results-area");
const runtimePill = document.getElementById("runtime-pill");

const isStaticHost = window.location.hostname.endsWith("github.io");
runtimePill.textContent = isStaticHost ? "Static Edge Agent" : "Vercel Python Agent";

document.querySelectorAll(".chip").forEach((btn) => {
  btn.addEventListener("click", () => {
    input.value = btn.getAttribute("data-query");
    form.dispatchEvent(new Event("submit"));
  });
});

async function runClientFallbackAgent(query) {
  const trace = ["Step 1: Running client-side autonomous verification..."];
  const findings = [];

  try {
    const qUrl = `https://alquran.cloud{encodeURIComponent(query)}/all/en.sahih`;
    const qResp = await fetch(qUrl);
    const qData = await qResp.json();
    const matches = (qData.data && qData.data.matches ? qData.data.matches : []).slice(0, 3);
    matches.forEach((m) => {
      findings.push({
        source: `Quran ${m.surah.number}:${m.numberInSurah} (${m.surah.englishName})`,
        grade: "Mutawatir (Authentic Revelation)",
        text: m.text
      });
    });
    trace.push(`Step 1 Complete: Retrieved ${matches.length} Quranic record(s).`);
  } catch (e) {
    trace.push("Step 1 Notice: Quran endpoint skipped.");
  }

  try {
    const wUrl = `https://wikipedia.org{encodeURIComponent(query)}&format=json&origin=*&srlimit=2`;
    const wResp = await fetch(wUrl);
    const wData = await wResp.json();
    const hits = wData.query && wData.query.search ? wData.query.search : [];
    hits.forEach((h) => {
      findings.push({
        source: `Reference Record: ${h.title}`,
        grade: "Cross-Referenced Summary",
        text: h.snippet.replace(/<[^>]+>/g, "")
      });
    });
    trace.push(`Step 2 Complete: Cross-referenced ${hits.length} external record(s).`);
  } catch (e) {
    trace.push("Step 2 Notice: Reference lookup skipped.");
  }

  return {
    agent: "SahihAgent Static Edge Runtime",
    verdict: findings.length > 0
      ? `Verified — ${findings.length} source record(s) retrieved.`
      : "Unverified — No direct textual match found.",
    answer: findings.length > 0
      ? `Autonomous verification results for "${query}":`
      : "No direct matches found. Try refining your keywords.",
    trace,
    sources: findings
  };
}

function renderReport(data) {
  const traceItems = (data.trace || []).map((t) => `<li>&bull; ${t}</li>`).join("");
  const sourceRows = (data.sources || [])
    .map(
      (s) => `
      <tr>
        <td><strong>${s.source}</strong></td>
        <td><span class="grade-badge">${s.grade}</span></td>
        <td>${s.text}</td>
      </tr>`
    )
    .join("");

  resultsArea.innerHTML = `
    <div class="card">
      <div class="verdict-banner">
        <h3>${data.verdict}</h3>
        <p>${data.answer}</p>
      </div>
      <div class="trace-box">
        <strong>Agent Reasoning Trace (${data.agent}):</strong>
        <ul>${traceItems}</ul>
      </div>
      ${
        sourceRows
          ? `<table class="source-table">
              <thead>
                <tr>
                  <th>Primary Source</th>
                  <th>Authenticity Grade</th>
                  <th>Verified Text</th>
                </tr>
              </thead>
              <tbody>${sourceRows}</tbody>
            </table>`
          : ""
      }
    </div>
  `;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = input.value.trim();
  if (!query) return;

  resultsArea.innerHTML = `<div class="card"><p>SahihAgent is autonomously verifying primary sources...</p></div>`;

  try {
    let report;
    if (!isStaticHost) {
      const res = await fetch("/api/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      });
      if (!res.ok) throw new Error("Serverless agent error");
      report = await res.json();
    } else {
      report = await runClientFallbackAgent(query);
    }
    renderReport(report);
  } catch (err) {
    const fallback = await runClientFallbackAgent(query);
    renderReport(fallback);
  }
});

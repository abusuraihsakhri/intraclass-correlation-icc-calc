/* Dependency-free browser implementation of balanced-design ANOVA ICCs. */
(function (root) {
  "use strict";
  const names = [
    ["icc_1_1", "ICC(1,1)", "One-way random · single"],
    ["icc_1_k", "ICC(1,k)", "One-way random · mean of k"],
    ["icc_2_1", "ICC(2,1)", "Two-way random · absolute agreement · single"],
    ["icc_2_k", "ICC(2,k)", "Two-way random · absolute agreement · mean of k"],
    ["icc_3_1", "ICC(3,1)", "Two-way mixed · consistency · single"],
    ["icc_3_k", "ICC(3,k)", "Two-way mixed · consistency · mean of k"]
  ];

  function ratio(a, b) {
    return Math.abs(b) <= Number.EPSILON * Math.max(Math.abs(a), Math.abs(b)) ? null : a / b;
  }
  function parseRatings(text) {
    const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/).map(x => x.trim()).filter(Boolean);
    if (lines.length > 5001) throw new Error("Maximum 5,000 subjects.");
    const tokens = lines.map(line => line.split(/[,\t]/).map(cell => cell.trim()));
    if (tokens.length && tokens[0].every(x => x !== "" && !Number.isFinite(Number(x)))) tokens.shift();
    if (tokens.length < 2 || tokens[0].length < 2) {
      throw new Error("Enter at least two subject rows and two numeric rater columns.");
    }
    const k = tokens[0].length;
    if (k > 50) throw new Error("Maximum 50 raters.");
    return tokens.map((cells, i) => {
      if (cells.length !== k) throw new Error("Row " + (i + 1) + ": inconsistent rater count.");
      return cells.map(cell => {
        if (!cell || !Number.isFinite(Number(cell))) {
          throw new Error("Row " + (i + 1) + ": missing or nonnumeric rating.");
        }
        const num = Number(cell);
        if (Math.abs(num) > 1e12) throw new Error("Ratings must have magnitude at most 1e12.");
        return num;
      });
    });
  }
  function compute(rows) {
    if (!Array.isArray(rows) || rows.length < 2 || !Array.isArray(rows[0]) || rows[0].length < 2) {
      throw new Error("At least two subjects and two raters are required.");
    }
    const n = rows.length, k = rows[0].length;
    if (n > 5000 || k > 50) throw new Error("Maximum 5,000 subjects and 50 raters.");
    for (const row of rows) {
      if (!Array.isArray(row) || row.length !== k || row.some(x => typeof x !== "number" || !Number.isFinite(x))) {
        throw new Error("Ratings must be a complete finite rectangular numeric matrix.");
      }
    }
    const grand = rows.reduce((s, row) => s + row.reduce((a, x) => a + x, 0), 0) / (n * k);
    const rowMeans = rows.map(row => row.reduce((a, x) => a + x, 0) / k);
    const colMeans = Array.from({length: k}, (_, j) =>
      rows.reduce((a, row) => a + row[j], 0) / n);
    const ssr = k * rowMeans.reduce((a, m) => a + (m - grand) ** 2, 0);
    const ssc = n * colMeans.reduce((a, m) => a + (m - grand) ** 2, 0);
    const sst = rows.reduce((a, row) =>
      a + row.reduce((s, x) => s + (x - grand) ** 2, 0), 0);
    const msr = ssr / (n - 1);
    const msw = Math.max(0, sst - ssr) / (n * (k - 1));
    const msc = ssc / (k - 1);
    const mse = Math.max(0, sst - ssr - ssc) / ((n - 1) * (k - 1));
    const values = [msr, msw, msc, mse];
    if (!values.every(Number.isFinite)) throw new Error("Numerical overflow: rescale measurements.");
    return {
      subjects: n, raters: k, ms_between: msr, ms_within: msw,
      ms_rater: msc, ms_error: mse,
      icc_1_1: ratio(msr - msw, msr + (k - 1) * msw),
      icc_1_k: ratio(msr - msw, msr),
      icc_2_1: ratio(msr - mse, msr + (k - 1) * mse + k * (msc - mse) / n),
      icc_2_k: ratio(msr - mse, msr + (msc - mse) / n),
      icc_3_1: ratio(msr - mse, msr + (k - 1) * mse),
      icc_3_k: ratio(msr - mse, msr)
    };
  }
  function designEffect(m, rho) {
    if (!Number.isFinite(m) || m < 1 || !Number.isFinite(rho) || rho < 0 || rho > 1) {
      throw new Error("Cluster size must be ≥ 1 and cluster ICC between 0 and 1.");
    }
    return 1 + (m - 1) * rho;
  }
  const publicApi = { parseRatings, compute, designEffect, names };
  if (typeof module !== "undefined" && module.exports) module.exports = publicApi;
  root.ICC = publicApi;

  if (typeof document === "undefined") return;
  const $ = id => document.getElementById(id);
  const form = $("icc-form");
  if (!form) return;
  let lastResult = null;
  const format = value => value === null ? "Not estimable" : Number(value).toFixed(6);

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    $("error").textContent = "";
    try {
      lastResult = compute(parseRatings($("ratings").value));
      $("summary").textContent = lastResult.subjects + " subjects × " +
        lastResult.raters + " raters · balanced complete design";
      const body = $("results-body");
      body.replaceChildren();
      for (const [key, label, explanation] of names) {
        const tr = document.createElement("tr");
        for (const value of [label, explanation, format(lastResult[key])]) {
          const td = document.createElement("td");
          td.textContent = value;
          tr.appendChild(td);
        }
        body.appendChild(tr);
      }
      $("msr").textContent = format(lastResult.ms_between);
      $("msw").textContent = format(lastResult.ms_within);
      $("msc").textContent = format(lastResult.ms_rater);
      $("mse").textContent = format(lastResult.ms_error);
      $("results").hidden = false;
      $("export").disabled = false;
    } catch (err) {
      lastResult = null;
      $("results").hidden = true;
      $("export").disabled = true;
      $("error").textContent = err.message;
    }
  });

  $("design-form").addEventListener("submit", function (event) {
    event.preventDefault();
    $("design-error").textContent = "";
    try {
      const m = $("cluster-size").value, rho = $("cluster-icc").value;
      if (m.trim() === "" || rho.trim() === "") throw new Error("Both inputs are required.");
      $("design-value").textContent = format(designEffect(Number(m), Number(rho)));
    } catch (err) {
      $("design-value").textContent = "—";
      $("design-error").textContent = err.message;
    }
  });

  $("upload").addEventListener("change", async function (event) {
    const file = event.target.files[0];
    if (!file) return;
    $("error").textContent = "";
    if (file.size > 1024 * 1024) {
      $("error").textContent = "CSV must be no larger than 1 MB.";
      return;
    }
    try {
      $("ratings").value = await file.text();
      form.requestSubmit();
    } catch (_err) {
      $("error").textContent = "Unable to read CSV file.";
    }
  });

  $("export").addEventListener("click", function () {
    if (!lastResult) return;
    const headers = ["subjects", "raters", "ms_between", "ms_within", "ms_rater", "ms_error",
                     ...names.map(([key]) => key)];
    const csv = headers.join(",") + "\n" +
      headers.map(key => lastResult[key] === null ? "" : lastResult[key]).join(",") + "\n";
    const url = URL.createObjectURL(new Blob([csv], {type:"text/csv;charset=utf-8"}));
    const link = document.createElement("a");
    link.href = url;
    link.download = "icc-results.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
})(typeof window !== "undefined" ? window : globalThis);

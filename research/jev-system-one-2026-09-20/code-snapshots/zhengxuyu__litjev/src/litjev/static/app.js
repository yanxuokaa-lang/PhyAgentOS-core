"use strict";
const el = (id) => document.getElementById(id);
async function loadExample() {
  try {
    const response = await fetch("/example");
    if (!response.ok) throw new Error("无法加载示例");
    const example = await response.json();
    el("schema-input").value = JSON.stringify(example.questions, null, 2);
  } catch (error) { el("error").textContent = error.message; el("error").hidden = false; }
}
function seconds(value) { return Number.isFinite(value) ? `${value.toFixed(3)} s` : "—"; }
async function health() {
  try {
    const response = await fetch("/health");
    if (!response.ok) throw new Error("服务不可用");
    const status = await response.json();
    el("health").textContent = status.model_loaded ? "● 模型已就绪" : "● 已连接 · 模型待加载";
  } catch { el("health").textContent = "○ 服务未连接"; }
}
function renderAnswers(answers, diagnostics) {
  el("answers").replaceChildren();
  for (const [name, answer] of Object.entries(answers)) {
    const card = document.createElement("article"); card.className = "answer";
    const heading = document.createElement("div"); heading.className = "answer-heading";
    const title = document.createElement("strong"); title.textContent = name;
    const winner = document.createElement("span"); winner.className = "winner";
    winner.textContent = answer.type === "noul" ? `P(yes) ${answer.noul.toFixed(4)}` : `${answer.choice ?? answer.score.toFixed(4)} · confidence ${answer.confidence.toFixed(4)}`;
    heading.append(title, winner); card.append(heading);
    const field = diagnostics.fields[name];
    if (field.provenance?.candidate_token_ids) {
      const p = field.provenance;
      const detail = document.createElement("details");
      const summary = document.createElement("summary"); summary.textContent = "本字段 logits 的实际取值位置";
      const content = document.createElement("pre");
      content.textContent = `方法：${p.method}\n文本解码器：${p.decoder_layer_count} 层，最后 block 索引 ${p.last_decoder_layer_index}\n最终 RMSNorm → ${p.module}\noutput.logits[${p.batch_index}, ${p.selected_logit_index}, ${JSON.stringify(p.candidate_token_ids)}]\n等价于 full_logits[${p.batch_index}, ${p.absolute_position}, ids]（0-based）\n本行后缀：${JSON.stringify(p.slot_text)}\n后缀 token IDs：${JSON.stringify(p.slot_token_ids)}\n原始键：${JSON.stringify(p.candidate_labels)}\n内部代码：${JSON.stringify(p.candidate_codes)}\n直接读取的 logits：${JSON.stringify(field.logits)}\n温度 T = ${p.temperature}`;
      detail.append(summary, content); card.append(detail);
    }
    for (const [label, probability] of Object.entries(answer.probabilities ?? field.probabilities)) {
      const row = document.createElement("div"); row.className = "probability";
      const text = document.createElement("span"); text.textContent = label;
      const bar = document.createElement("progress"); bar.max = 1; bar.value = probability;
      bar.setAttribute("aria-label", `${name} / ${label}`);
      const value = document.createElement("span"); value.textContent = `${(probability * 100).toFixed(2)}%`;
      row.append(text, bar, value); card.append(row);
    }
    el("answers").append(card);
  }
}
el("example").addEventListener("click", loadExample);
el("decision-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  el("error").hidden = true;
  el("answers").replaceChildren();
  el("raw-details").hidden = true;
  el("raw").textContent = "";
  el("calibration").textContent = "等待本次响应的校准状态。";
  for (const id of ["roundtrip", "decision-time", "setup-time"]) el(id).textContent = "—";
  let schema;
  let screenshot;
  try {
    schema = JSON.parse(el("schema-input").value);
    if (!schema || Array.isArray(schema) || typeof schema !== "object") throw new Error("Schema 必须是 JSON 对象。");
    if (Object.keys(schema).length < 1) throw new Error("请至少输入一个问题。");
    const file = el("image-input").files[0];
    if (file) {
      if (!["image/png", "image/jpeg"].includes(file.type) || file.size > 4_000_000) throw new Error("截图必须是小于 4 MB 的 PNG/JPEG。");
      screenshot = await new Promise((resolve, reject) => {
        const reader = new FileReader(); reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error("无法读取截图")); reader.readAsDataURL(file);
      });
    }
  } catch (error) {
    el("error").textContent = `输入错误：${error.message}`; el("error").hidden = false;
    el("result-status").textContent = "输入无效"; return;
  }
  el("submit").disabled = true; el("example").disabled = true;
  el("output-panel").setAttribute("aria-busy", "true");
  el("result-status").textContent = "运行中…";
  const started = performance.now();
  const timer = setInterval(() => { el("elapsed").textContent = `已等待 ${((performance.now() - started) / 1000).toFixed(1)} s`; }, 100);
  try {
    const response = await fetch("/v1/systemone/debug", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({model: "litjev", questions: schema, state: el("state-input").value, ...(screenshot ? {image: screenshot} : {})})
    });
    const text = await response.text();
    el("roundtrip").textContent = seconds((performance.now() - started) / 1000);
    let result;
    try { result = JSON.parse(text); } catch { throw new Error(`服务返回 HTTP ${response.status}，未得到 JSON。请查看服务日志。`); }
    if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : JSON.stringify(result.detail));
    const {result: standard, diagnostics} = result;
    renderAnswers(standard.answers, diagnostics);
    el("decision-time").textContent = seconds(diagnostics.timing?.decision_seconds);
    el("setup-time").textContent = seconds(diagnostics.timing?.model_setup_seconds);
    el("calibration").textContent = `${diagnostics.calibration_fitted ? "已加载温度参数" : "未校准"}；confidence 是 LitJev 分布集中度，不是正确率，也不保证数值与 Jev 相同。`;
    el("raw").textContent = JSON.stringify(result, null, 2); el("raw-details").hidden = false;
    el("result-status").textContent = `${Object.keys(standard.answers).length} 个问题 · ${diagnostics.forward_calls} 次 forward`;
  } catch (error) {
    el("error").textContent = error.message; el("error").hidden = false;
    el("result-status").textContent = "请求失败";
  } finally {
    clearInterval(timer); el("elapsed").textContent = `请求结束 · ${((performance.now() - started) / 1000).toFixed(3)} s`;
    el("submit").disabled = false; el("example").disabled = false;
    el("output-panel").setAttribute("aria-busy", "false"); health();
  }
});
loadExample(); health();

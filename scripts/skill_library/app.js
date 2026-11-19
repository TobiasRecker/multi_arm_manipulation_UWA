const content = document.querySelector("#content");
const main = document.querySelector("main");
const navigation = document.querySelector("nav a");
const timestamp = new Intl.DateTimeFormat("en-AU", {
  hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  timeZone: "Australia/Perth",
});
const workflowPhase = {
  oak_capture: "capture",
  oak_registration: "registration",
  offline_plan: "planning",
  n100_approach: "planning",
  wrist_diagnostic: "wrist",
  oak_entry_capture: "wrist",
  n100_contact: "contact_review",
};
const state = {
  programs: [], catalogError: "", loading: true, run: null, pending: "", actionError: "",
  connectionError: "", timer: null,
};

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function link(href, className, label) {
  const node = element("a", className, label);
  node.href = href;
  return node;
}

function programRoute(id) {
  return `#program/${encodeURIComponent(id)}`;
}

function selectedProgram() {
  const route = window.location.hash.slice(1);
  if (!route.startsWith("program/")) return null;
  return state.programs.find(program => programRoute(program.id).slice(1) === route) ?? null;
}

async function request(url, options) {
  const response = await fetch(url, { cache: "no-store", ...options });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status}).`);
  return result;
}

function heading(title, description) {
  const header = element("header", "page-heading");
  header.append(element("h1", "", title));
  if (description) header.append(element("p", "", description));
  return header;
}

function cartonImage(program) {
  if (program.id !== "carton-supported-v1") return null;
  const figure = element("figure", "program-image");
  const image = element("img");
  image.src = "/assets/carton.png";
  image.alt = "Avocado carton on the worktable in the UWA cell model";
  image.width = 912;
  image.height = 808;
  figure.append(image, element("figcaption", "", "Cell model"));
  return figure;
}

function details(program) {
  const list = element("dl", "facts");
  for (const [term, value] of [["Workpiece", program.object], ["Arms", program.arms.join(" · ")]]) {
    const item = element("div");
    item.append(element("dt", "", term), element("dd", "", value));
    list.append(item);
  }
  return list;
}

function programCard(program) {
  const card = element("article", "program-card");
  const figure = cartonImage(program);
  if (figure) card.append(figure);
  else card.classList.add("text-only");
  const copy = element("div", "program-copy");
  copy.append(element("h2", "", program.title), element("p", "", program.description), details(program));
  copy.append(link(programRoute(program.id), "button primary", "Open program"));
  card.append(copy);
  return card;
}

function workflow(program) {
  const section = element("section", "panel workflow");
  section.append(element("h2", "", "Program steps"));
  const steps = element("ol", "steps");
  const activeRun = state.run?.program === program.id ? state.run : null;
  for (const stage of program.stages) {
    const item = element("li");
    const body = element("div", "step-body");
    body.append(element("h3", "", stage.title), element("p", "", stage.description));
    item.dataset.phase = stage.id;
    if (activeRun?.state === "running" && stage.id === (workflowPhase[activeRun.phase] || activeRun.phase)) {
      item.setAttribute("aria-current", "step");
    }
    item.append(body);
    steps.append(item);
  }
  section.append(steps);
  return section;
}

function startButton(program, mode, label, style) {
  const button = element("button", `button ${style}`, label);
  button.type = "button";
  button.dataset.mode = mode;
  button.disabled = !program[`${mode}_available`];
  button.addEventListener("click", () => start(program, mode));
  return button;
}

function actions(program) {
  const section = element("section", "panel actions");
  section.append(element("h2", "", "Run program"));
  if (program.live_available) {
    section.append(element("p", "", "Start the physical procedure and review its motion in UWA Robot Power."));
  } else if (program.live_blocker) {
    section.append(element("p", "", program.live_blocker));
  }
  const demoText = "The offline demo uses saved inputs. It plans motion without connecting to the cell.";
  if (program.demo_available) section.append(element("p", "", demoText));
  const buttons = element("div", "run-buttons");
  buttons.append(startButton(program, "live", "Start program", "primary"));
  buttons.append(startButton(program, "demo", "Run offline demo", program.live_available ? "secondary" : "primary"));
  section.append(buttons);
  const message = element("p", "feedback");
  message.id = "action-feedback";
  message.setAttribute("role", "status");
  section.append(message);
  return section;
}

function statusPanel() {
  const panel = element("section", "panel status-panel");
  panel.id = "run-status";
  panel.setAttribute("aria-label", "Run status");
  return panel;
}

function localTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return timestamp.format(date);
}

function phaseTitle(run, phase) {
  const program = state.programs.find(candidate => candidate.id === run.program);
  if (phase === "oak_entry_capture") return "Capture the open entry";
  const title = program?.stages.find(stage => stage.id === (workflowPhase[phase] || phase))?.title;
  if (title) return title;
  return (phase || "").replaceAll("_", " ").replaceAll("-", " ");
}

function runState(run) {
  const waiting = run.mode === "live" && run.state === "running" &&
    ["motion_review", "contact_review"].includes(run.phase);
  const label = waiting ? "REVIEW REQUIRED" :
    ({ running: "RUNNING", succeeded: "COMPLETE", failed: "FAILED" }[run.state] || "UNKNOWN");
  return `${run.mode === "live" ? "CELL" : "OFFLINE DEMO"} · ${label}`;
}

function verdict(code) {
  return {
    REVIEW_REQUIRED: "Review required",
    INVALID_INPUT: "Input unavailable",
    EXPECTED_RIM_OUT_OF_FRAME: "Projected rim out of frame",
    RIM_NOT_FOUND: "Rim not found",
    RIM_NOT_VISIBLE_AT_TARGET: "Rim not visible at the target",
    RIM_UNCERTAIN: "Rim detection uncertain",
    RIM_MEASURED: "Rim measured",
  }[code] || code;
}

function summarizeResult(result) {
  const evidence = element("dl", "evidence");
  const rows = [
    ["Carton pose", result.pose],
    ["Motion plan", result.plan],
    ["Contact", result.contact],
    ["Wrist check", result.wrist],
  ];
  for (const [label, value] of rows) {
    if (typeof value === "string" && value) {
      evidence.append(element("dt", "", label), element("dd", "", value));
    } else if (label === "Wrist check" && value?.status) {
      const text = [verdict(value.status), value.reason].filter(Boolean).join(". ");
      const description = element("dd", "", text);
      const arms = element("ul", "arm-evidence");
      for (const [arm, record] of Object.entries(value.arms || {})) {
        const name = { right_front: "Right front", right_rear: "Right rear" }[arm] || arm;
        const offset = Number.isFinite(record.signed_image_offset_px)
          ? ` · ${record.signed_image_offset_px.toFixed(1)} px rim offset` : "";
        arms.append(element("li", "", `${name} · ${verdict(record.status)}${offset}`));
      }
      if (arms.childElementCount) description.append(arms);
      evidence.append(element("dt", "", label), description);
    }
  }
  return evidence.childElementCount ? evidence : null;
}

function artifactLinks(run) {
  if (run.mode !== "demo" || run.state === "running" || !run.result?.artifacts) return null;
  const list = element("ul", "artifact-links");
  list.setAttribute("aria-label", "Saved camera previews");
  for (const [key, label] of [
    ["oak_preview", "OAK4 pose preview"],
    ["right_front_preview", "Right front wrist"],
    ["right_rear_preview", "Right rear wrist"],
  ]) {
    if (!run.result.artifacts[key]) continue;
    const item = element("li");
    const image = link(`/api/runs/${encodeURIComponent(run.id)}/artifacts/${key}`, "text-link", label);
    image.target = "_blank";
    image.rel = "noopener";
    item.append(image);
    list.append(item);
  }
  return list.childElementCount ? list : null;
}

function eventList(run) {
  const list = element("ol", "events");
  for (const event of [...(run.events || [])].reverse()) {
    const item = element("li");
    const time = element("time", "", localTime(event.at));
    if (time.textContent) time.dateTime = event.at;
    const body = element("div");
    body.append(element("strong", "", phaseTitle(run, event.phase)));
    if (event.message) body.append(element("p", "", event.message));
    item.append(time, body);
    list.append(item);
  }
  return list;
}

function updateStatus() {
  const panel = document.querySelector("#run-status");
  if (!panel) return;
  const run = state.run;
  const title = element("h2", "", "Run status");
  if (!run) {
    panel.replaceChildren(title, element("p", "", "No program has been started."));
    return;
  }
  const program = state.programs.find(candidate => candidate.id === run.program);
  const badge = element("strong", `status ${run.state}`, runState(run));
  const summary = element("div", "run-summary");
  summary.setAttribute("role", "status");
  summary.append(badge, element("h3", "", program?.title || run.program));
  if (run.message) summary.append(element("p", "", run.message));
  if (state.connectionError) summary.append(element("p", "feedback", state.connectionError));

  const next = [title, summary];
  const evidence = run.result && summarizeResult(run.result);
  if (evidence) next.push(evidence);
  const artifacts = artifactLinks(run);
  if (artifacts) next.push(artifacts);
  if (run.events?.length) next.push(eventList(run));
  if (program && selectedProgram()?.id !== program.id) {
    next.push(link(programRoute(program.id), "text-link", "Open this program"));
  }
  if (panel.textContent !== next.map(node => node.textContent).join("")) panel.replaceChildren(...next);

  for (const step of document.querySelectorAll(".steps li")) {
    if (selectedProgram()?.id === run.program && run.state === "running" &&
        step.dataset.phase === (workflowPhase[run.phase] || run.phase)) {
      step.setAttribute("aria-current", "step");
    } else {
      step.removeAttribute("aria-current");
    }
  }
}

function updateActions() {
  const program = selectedProgram();
  const blocked = Boolean(state.pending) || state.run?.state === "running";
  for (const button of document.querySelectorAll("[data-mode]")) {
    button.disabled = blocked || !program[`${button.dataset.mode}_available`];
  }
  const feedback = document.querySelector("#action-feedback");
  if (feedback) {
    feedback.classList.toggle("pending", Boolean(state.pending) && !state.actionError);
    feedback.textContent = state.actionError || (state.pending ? "Sending start request…" : "");
  }
}

function render() {
  const program = selectedProgram();
  navigation.setAttribute("aria-current", program ? "location" : "page");
  document.title = `${program?.title || "Program library"} · UWA Robot Power`;
  if (program) {
    const intro = heading(program.title, program.description);
    intro.prepend(link("#library", "text-link back-link", "Program library"));
    const columns = element("div", "columns");
    const left = element("div", "stack");
    const right = element("div", "stack");
    const figure = cartonImage(program);
    const identity = element("section", "panel program-identity");
    if (figure) identity.append(figure);
    identity.append(details(program));
    left.append(actions(program), workflow(program));
    right.append(identity, statusPanel());
    columns.append(left, right);
    content.replaceChildren(intro, columns);
  } else {
    const intro = heading("Program library", "Open a saved program to review its steps or start a run.");
    const cards = element("div", "program-list");
    if (state.loading) {
      const message = element("p", "", "Loading saved programs…");
      message.setAttribute("role", "status");
      cards.append(message);
    } else if (state.catalogError) {
      const message = element("p", "feedback", state.catalogError);
      message.setAttribute("role", "alert");
      const retry = element("button", "button secondary", "Reload library");
      retry.type = "button";
      retry.addEventListener("click", loadCatalog);
      cards.append(message, retry);
    } else if (!state.programs.length) {
      cards.append(element("p", "", "No saved programs are available."));
    } else {
      cards.append(...state.programs.map(programCard));
    }
    content.replaceChildren(intro, cards);
    if (state.run) content.append(statusPanel());
  }
  updateActions();
  updateStatus();
}

async function poll() {
  clearTimeout(state.timer);
  const run = state.run;
  if (!run || run.state !== "running") return;
  try {
    state.run = await request(`/api/runs/${encodeURIComponent(run.id)}`);
    state.connectionError = "";
  } catch (error) {
    state.connectionError = `Run status unavailable. Retrying. ${error.message}`;
  }
  updateActions();
  updateStatus();
  if (state.run?.state === "running") state.timer = setTimeout(poll, 1250);
}

async function start(program, mode) {
  if (state.pending || state.run?.state === "running" || !program[`${mode}_available`]) return;
  state.actionError = "";
  state.pending = mode;
  updateActions();
  try {
    state.run = await request("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ program: program.id, mode }),
    });
    state.connectionError = "";
    updateStatus();
    poll();
  } catch (error) {
    state.actionError = `Start failed. ${error.message}`;
  } finally {
    state.pending = "";
    updateActions();
  }
}

async function loadCatalog() {
  state.loading = true;
  state.catalogError = "";
  render();
  try {
    const catalog = await request("/api/catalog");
    state.programs = catalog.programs;
    state.run = catalog.active_run;
  } catch (error) {
    state.catalogError = `Could not load the library. ${error.message}`;
  } finally {
    state.loading = false;
    render();
    poll();
  }
}

document.querySelector(".skip-link").addEventListener("click", event => {
  event.preventDefault();
  main.focus();
});
window.addEventListener("hashchange", () => {
  state.actionError = "";
  render();
  main.focus();
});
loadCatalog();

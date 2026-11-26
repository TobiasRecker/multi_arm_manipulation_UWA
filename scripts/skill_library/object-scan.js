import { textureEditor } from "./scan-textures.js";

const programUrl = "#program/object-scan-v1";
const cameraNames = {
  oak4: "OAK4",
  oak_pro: "OAK Pro",
  wrist_left_front: "Left front wrist",
  wrist_left_rear: "Left rear wrist",
  wrist_right_front: "Right front wrist",
  wrist_right_rear: "Right rear wrist",
};
const pending = {
  capturing: "Capturing a new view",
  analyzing: "Gemini is reviewing the selected images",
  assessing: "Gemini is assessing coverage",
  publishing: "Saving the asset draft",
};
const dateFormat = new Intl.DateTimeFormat("en-AU", {
  dateStyle: "medium", timeStyle: "short", timeZone: "Australia/Perth",
});
const faceNames = {
  "+x": "+X end", "-x": "−X end", "+y": "+Y side", "-y": "−Y side",
  "+z": "+Z face", "-z": "−Z face",
};
let activeView;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function link(href, className, label) {
  const node = el("a", className, label);
  node.href = href;
  return node;
}

function button(label, style, action) {
  const node = el("button", `button ${style}`, label);
  node.type = "button";
  if (action) node.addEventListener("click", action);
  return node;
}

function panel(title, ...children) {
  const section = el("section", "panel scan-panel");
  section.append(el("h2", "", title), ...children);
  return section;
}

function heading(title, caption, back) {
  const header = el("header", "page-heading");
  if (back) header.append(link(back[0], "text-link back-link", back[1]));
  header.append(el("h1", "", title));
  if (caption) header.append(el("p", "", caption));
  return header;
}

function feedback(text = "", error = false) {
  const node = el("p", `feedback${error ? "" : " pending"}`, text);
  node.setAttribute("role", error ? "alert" : "status");
  return node;
}

function dateLabel(value) {
  const date = new Date(value);
  return value && !Number.isNaN(date.getTime()) ? `${dateFormat.format(date)} AWST` : "";
}

function smallList(items, className = "scan-list") {
  const list = el("ul", className);
  for (const item of items) list.append(el("li", "", item));
  return list;
}

function field(caption, input, description) {
  const node = el("label", "scan-field");
  node.append(el("span", "", caption), input);
  if (description) node.append(el("small", "", description));
  return node;
}

function options(entries) {
  const node = el("select");
  for (const [value, text] of entries) {
    const option = el("option", "", text);
    option.value = value;
    node.append(option);
  }
  return node;
}

function cameraSelection(selected, title) {
  const group = el("fieldset", "scan-cameras");
  group.append(el("legend", "", title));
  for (const [id, name] of Object.entries(cameraNames)) {
    const label = el("label", "scan-choice");
    const input = el("input");
    input.type = "checkbox";
    input.value = id;
    input.name = "camera";
    input.checked = selected.includes(id);
    label.append(input, el("span", "", name));
    group.append(label);
  }
  return group;
}

function selectedCameras(group) {
  const cameras = [...group.querySelectorAll(":checked")].map(input => input.value);
  if (!cameras.length) throw new Error("Select at least one camera.");
  return cameras;
}

function bindAction(view, container, message, action) {
  const notice = feedback();
  container.append(notice);
  return async () => {
    if (view.busy || activeView !== view) return;
    view.busy = true;
    const buttons = [...view.root.querySelectorAll("button:not(:disabled)")];
    for (const control of buttons) control.disabled = true;
    notice.setAttribute("role", "status");
    notice.classList.add("pending");
    notice.textContent = message;
    try {
      await action();
    } catch (error) {
      notice.setAttribute("role", "alert");
      notice.classList.remove("pending");
      notice.textContent = error.message;
    } finally {
      view.busy = false;
      for (const control of buttons) control.disabled = false;
    }
  };
}

function submit(form, label, style = "primary") {
  const node = button(label, style);
  node.type = "submit";
  form.append(node);
}

function post(view, suffix, payload) {
  const base = view.scan ? `/api/scans/${view.scan.id}` : "/api/scans";
  return view.request(`${base}${suffix}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
}

function scanUrl(id) {
  return `#scan/${encodeURIComponent(id)}`;
}

function newScanForm(view) {
  const form = el("form", "scan-form");
  const name = el("input");
  name.required = true;
  name.maxLength = 100;
  name.placeholder = "Wooden beam";
  const description = el("textarea");
  description.required = true;
  description.maxLength = 2000;
  description.rows = 3;
  description.placeholder = "Rectangular timber on the right table, pale wood with a dark knot at one end.";
  const count = options([["", "Ask Gemini to discuss"], ["1", "One arm"], ["2", "Two arms"],
    ["3", "Three arms"], ["4", "Four arms"]]);
  const shape = options([["other", "Other or unknown"], ["box", "Rectangular solid (cuboid)"]]);
  const dimensions = el("fieldset", "scan-dimensions");
  dimensions.hidden = true;
  dimensions.append(el("legend", "", "Measured outer dimensions (optional)"));
  const measurements = [["X length", "mm"], ["Y width", "mm"], ["Z height", "mm"]].map(([axis, unit]) => {
    const input = el("input");
    input.type = "number";
    input.min = "1";
    input.max = "5000";
    input.step = "any";
    dimensions.append(field(`${axis} (${unit})`, input));
    return input;
  });
  shape.addEventListener("change", () => { dimensions.hidden = shape.value !== "box"; });
  const cameras = cameraSelection(["oak4"], "Default cameras");
  form.append(field("Object name", name), field("Object description", description), cameras,
    field("How many robots should hold it?", count), field("Object shape", shape), dimensions);
  submit(form, "Create scan session");
  const action = bindAction(view, form, "Creating scan session…", async () => {
    const data = { name: name.value.trim(), description: description.value.trim(),
      camera_ids: selectedCameras(cameras), robot_count: count.value ? Number(count.value) : null, shape: shape.value };
    if (!data.name || !data.description) throw new Error("Enter an object name and description.");
    if (shape.value === "box" && measurements.some(input => input.value)) {
      if (measurements.some(input => !input.value || !(input.valueAsNumber > 0))) {
        throw new Error("Enter all three measured dimensions or leave them empty.");
      }
      data.dimensions_mm = measurements.map(input => input.valueAsNumber);
    }
    const result = await post(view, "", data);
    if (activeView === view) window.location.hash = scanUrl(result.id);
  });
  form.addEventListener("submit", event => { event.preventDefault(); action(); });
  return form;
}

function statusLabel(scan) {
  if (pending[scan.status]) return pending[scan.status];
  if (scan.error) return "Action failed";
  if (scan.asset) return "Asset draft available";
  if (scan.coverage) return "Coverage assessed";
  if (scan.proposal && scan.approval?.revision === scan.proposal.revision) return "Scan sequence approved";
  if (scan.proposal) return "Scan proposal ready for review";
  if (scan.captures?.length) return "Views captured";
  return "Ready to capture the first view";
}

function renderPrograms(view, scans) {
  const columns = el("div", "columns scan-columns");
  const sessions = panel("Scan sessions");
  if (!scans.length) sessions.append(el("p", "", "Saved sessions will appear here."));
  else {
    const list = el("ul", "scan-records");
    for (const scan of scans) {
      const item = el("li");
      item.append(link(scanUrl(scan.id), "text-link", scan.name),
        el("p", "", [statusLabel(scan), dateLabel(scan.updated_at)].filter(Boolean).join(" · ")));
      list.append(item);
    }
    sessions.append(list);
  }
  columns.append(panel("Start a scan", newScanForm(view)), sessions);
  view.root.replaceChildren(heading("Object scan",
    "Capture an object, review Gemini's scan proposal, and save the views and model draft to the Asset library.",
    ["#library", "Program library"]), columns);
}

function safeFileUrl(value) {
  return typeof value === "string" && value.startsWith("/api/") ? value : null;
}

function capturePhoto(file) {
  const figure = el("figure", "scan-photo");
  const caption = cameraNames[file.camera] || file.camera;
  const original = safeFileUrl(file.url);
  const preview = safeFileUrl(file.preview);
  if (file.error) figure.append(feedback(file.error, true));
  if (preview || original) {
    const photo = el("img");
    photo.alt = `${caption} capture`;
    photo.loading = "lazy";
    photo.src = preview || original;
    if (original) {
      const full = link(original, "", "");
      full.target = "_blank";
      full.rel = "noopener";
      full.append(photo);
      figure.append(full);
    } else figure.append(photo);
  }
  figure.append(el("figcaption", "", caption));
  return figure;
}

function scanAction(view, suffix, data) {
  return async () => {
    const result = await post(view, suffix, data());
    if (activeView === view) showSession(view, result);
  };
}

function captureSection(view, scan) {
  const form = el("form", "scan-form");
  const label = el("input");
  label.required = true;
  label.maxLength = 180;
  label.value = scan.captures.length ? "" : "Initial table view";
  label.placeholder = "Beam on its long side, grip marks visible";
  const notes = el("textarea");
  notes.maxLength = 1000;
  notes.rows = 2;
  notes.placeholder = "Rolled onto the broad side. The end facing OAK4 was previously under a gripper.";
  const cameras = cameraSelection(scan.camera_ids, "Cameras for this view");
  form.append(el("p", "", "Keep the object and arms still until capture finishes. OAK4 uses HQ HDR color and Stereo HDR for the overview, then native 48 MP HQ HDR for detail views."),
    field("View label", label), field("Support, occlusion or repositioning notes (optional)", notes), cameras);
  submit(form, "Capture view");
  const action = bindAction(view, form, "Starting camera capture…", scanAction(view, "/capture", () => {
    if (!label.value.trim()) throw new Error("Enter a view label.");
    return { label: label.value.trim(), camera_ids: selectedCameras(cameras),
      ...(notes.value.trim() ? { notes: notes.value.trim() } : {}) };
  }));
  form.addEventListener("submit", event => { event.preventDefault(); action(); });
  const section = panel("Capture views", form);
  for (const capture of [...scan.captures].reverse()) {
    const group = el("article", "scan-capture");
    const images = el("div", "scan-photos");
    images.append(...(capture.files || []).map(capturePhoto));
    group.append(el("h3", "", capture.label), el("p", "", dateLabel(capture.at)));
    if (capture.notes) group.append(el("p", "", capture.notes));
    group.append(images);
    section.append(group);
  }
  return section;
}

function observationOverlay(observation, file) {
  const source = safeFileUrl(file?.preview);
  if (!source || !observation.box_2d) return null;
  const figure = el("figure", "scan-observation");
  const canvas = el("canvas");
  const context = canvas.getContext("2d");
  if (!context) return null;
  figure.hidden = true;
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", "Image with Gemini's object box, visible axis and numbered grasp candidates");
  figure.append(canvas, el("figcaption", "", "Gemini image estimates · native camera orientation"));
  const image = new Image();
  image.addEventListener("load", () => {
    const scale = Math.min(1, 780 / image.naturalWidth, 600 / image.naturalHeight);
    const width = canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
    const height = canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
    context.drawImage(image, 0, 0, width, height);
    const pixel = ([y, x]) => [x / 1000 * width, y / 1000 * height];
    const [top, left, bottom, right] = observation.box_2d;
    const [x1, y1] = pixel([top, left]);
    const [x2, y2] = pixel([bottom, right]);
    context.beginPath();
    context.rect(x1, y1, x2 - x1, y2 - y1);
    if (observation.axis_2d) {
      context.moveTo(...pixel(observation.axis_2d[0]));
      context.lineTo(...pixel(observation.axis_2d[1]));
    }
    context.lineWidth = 6;
    context.strokeStyle = "#17232c";
    context.stroke();
    context.lineWidth = 3;
    context.strokeStyle = "#99f8e6";
    context.stroke();
    for (const [index, point] of (observation.grasp_points || []).entries()) {
      const [x, y] = pixel(point.point_2d);
      context.beginPath();
      context.arc(x, y, 13, 0, 2 * Math.PI);
      context.fillStyle = "#ffdd4a";
      context.fill();
      context.strokeStyle = "#17232c";
      context.stroke();
      context.fillStyle = "#17232c";
      context.font = "bold 16px sans-serif";
      context.textAlign = "center";
      context.textBaseline = "middle";
      context.fillText(String(index + 1), x, y);
    }
    figure.hidden = false;
  });
  image.src = source;
  return figure;
}

function addObservations(section, analysis, source) {
  if (!analysis) return;
  const names = { found: "Object found", uncertain: "Object detection uncertain", absent: "Object not found" };
  section.append(el("h3", "", names[analysis.status] || "Object observations"));
  for (const observation of analysis.observations || []) {
    const detail = el("div", "scan-detail");
    detail.append(el("strong", "", cameraNames[observation.camera] || observation.camera));
    if (observation.reason) detail.append(el("p", "", observation.reason));
    const overlay = observationOverlay(observation, source?.files?.find(file => file.camera === observation.camera));
    if (overlay) detail.append(overlay);
    if (observation.grasp_points?.length) {
      detail.append(smallList(observation.grasp_points.map((point, index) =>
        `Grasp candidate ${index + 1} · ${point.reason}`)));
    }
    section.append(detail);
  }
  for (const geometry of analysis.geometry || []) {
    const name = cameraNames[geometry.camera] || geometry.camera;
    if (geometry.obb?.size_m?.length === 3) {
      const size = geometry.obb.size_m.map(value => Math.round(value * 1000)).join(" × ");
      section.append(el("p", "", `${name} RGB-D bounding box estimate · ${size} mm · Frame ${geometry.obb.frame}`));
    } else if (geometry.reason) section.append(el("p", "", `${name} geometry · ${geometry.reason}`));
  }
}

function proposalSection(view, scan) {
  const section = panel("Identification and scan proposal");
  const source = scan.captures.find(capture => capture.id === scan.proposal?.source_capture_id);
  if (source) section.append(el("p", "", `Source view · ${source.label}`));
  addObservations(section, scan.analysis, source);
  const questions = scan.analysis?.questions || [];
  if (questions.length) section.append(el("h3", "", "Questions from Gemini"), smallList(questions));
  const form = el("form", "scan-form");
  form.append(el("p", "", "This sends images from this scan and your object description to Gemini through the configured Antigravity account."));
  const answer = el("textarea");
  answer.rows = 2;
  answer.maxLength = 1200;
  if (scan.analysis) form.append(field(questions.length ? "Answer Gemini (optional)" : "Additional context (optional)", answer));
  submit(form, scan.analysis ? "Update Gemini proposal" : "Analyze with Gemini", "secondary");
  const action = bindAction(view, form, "Requesting Gemini analysis…", scanAction(view, "/analyze", () => ({
    allow_gemini: true, ...(answer.value.trim() ? { answer: answer.value.trim() } : {}),
  })));
  form.addEventListener("submit", event => { event.preventDefault(); action(); });
  if (scan.captures.length) section.append(form);
  else section.append(el("p", "", "Capture an initial view to request identification and a scan proposal."));

  const proposal = scan.proposal;
  if (!proposal) return section;
  if (proposal.approach) section.append(el("h3", "", "Suggested approach"), el("p", "", proposal.approach));
  if (proposal.presentation_views?.length) {
    section.append(el("h3", "", "Suggested presentation views"), smallList(proposal.presentation_views));
  }
  if (proposal.motion_blocker) {
    section.append(el("p", "scan-callout", `Robot motion unavailable. ${proposal.motion_blocker}`));
  }
  const approved = scan.approval?.revision === proposal.revision;
  if (approved) section.append(el("strong", "status succeeded", "Scan sequence approved"));
  else {
    const review = el("div", "scan-form");
    review.append(el("p", "", "Approve this scan sequence for guidance. Robot movement requires a separate checked plan and Motion Review."));
    const approve = button("Approve scan sequence", "primary");
    review.append(approve);
    const approveAction = bindAction(view, review, "Recording scan sequence approval…",
      scanAction(view, "/approve", () => ({ revision: proposal.revision })));
    approve.addEventListener("click", approveAction);
    section.append(review);
  }
  return section;
}

function coverageSection(view, scan) {
  const section = panel("Coverage and next views");
  const coverage = scan.coverage;
  if (coverage) {
    const labels = { candidate: "Candidate coverage", more_views: "More views needed", uncertain: "Coverage uncertain" };
    section.append(el("strong", "status", labels[coverage.status] || "Gemini coverage assessment"));
    if (coverage.summary) section.append(el("p", "", coverage.summary));
    for (const face of coverage.faces || []) {
      const detail = el("div", "scan-detail");
      detail.append(el("strong", "", `${faceNames[face.face] || face.face} · ${face.status}`));
      if (face.reason) detail.append(el("p", "", face.reason));
      if (face.views?.length) detail.append(el("p", "", `Views · ${face.views.join(", ")}`));
      section.append(detail);
    }
    if (coverage.missing_views?.length) section.append(el("h3", "", "Missing views"), smallList(coverage.missing_views));
    if (coverage.repositioning?.length) {
      section.append(el("h3", "", "Repositioning suggestions"), smallList(coverage.repositioning));
    }
  }
  if (scan.captures.length) {
    const assessment = el("div", "scan-form");
    assessment.append(el("p", "", "Gemini compares scan photos for visibility, occlusion and texture coverage. This sends scan images through the configured Antigravity account."));
    const run = button(coverage ? "Reassess with Gemini" : "Assess coverage with Gemini", "secondary");
    assessment.append(run);
    run.addEventListener("click", bindAction(view, assessment, "Requesting coverage assessment…",
      scanAction(view, "/assess", () => ({ allow_gemini: true }))));
    section.append(assessment);
  } else section.append(el("p", "", "Capture views before asking Gemini to assess coverage."));
  return section;
}

function publishingSection(view, scan) {
  const section = panel("Save to Asset library");
  const controls = el("div", "scan-form");
  controls.append(el("p", "", scan.publish_available
    ? "Save the captured views, coverage report and available model as a draft."
    : "Capture views and assess current coverage to make a draft available."));
  const save = button(scan.asset ? "Update asset draft" : "Save asset draft", "primary");
  save.disabled = !scan.publish_available;
  controls.append(save);
  save.addEventListener("click", bindAction(view, controls, "Saving an asset draft…",
    scanAction(view, "/publish", () => ({}))));
  section.append(controls);
  if (scan.asset) section.append(link("#assets", "text-link", "View saved draft in Asset library"));
  return section;
}

function dimensionsSection(view, scan) {
  if (scan.shape !== "box") return null;
  const form = el("form", "scan-form");
  const dimensions = el("fieldset", "scan-dimensions");
  dimensions.append(el("legend", "", "Measured outer dimensions"));
  const inputs = ["X length", "Y width", "Z height"].map((axis, index) => {
    const input = el("input");
    input.type = "number";
    input.min = "1";
    input.max = "5000";
    input.step = "any";
    input.required = true;
    input.value = scan.dimensions_mm?.[index] ?? "";
    dimensions.append(field(`${axis} (mm)`, input));
    return input;
  });
  form.append(el("p", "", "Enter measured values to build a rectangular geometry draft."), dimensions);
  submit(form, "Save dimensions", "secondary");
  const action = bindAction(view, form, "Saving measured dimensions…", scanAction(view, "/dimensions", () => ({
    dimensions_mm: inputs.map(input => input.valueAsNumber),
  })));
  form.addEventListener("submit", event => { event.preventDefault(); action(); });
  const details = el("details", "scan-optional");
  const summary = scan.dimensions_mm ? `${scan.dimensions_mm.join(" × ")} mm · edit measurements` : "Add measurements";
  details.append(el("summary", "", summary), form);
  return panel("Rectangular model geometry", details);
}

function showSession(view, scan) {
  clearTimeout(view.timer);
  if (view.scan?.status === scan.status && pending[scan.status] && view.scan.updated_at === scan.updated_at) {
    view.root.querySelector(".scan-poll-error")?.remove();
    view.timer = setTimeout(() => refreshSession(view), 1200);
    return;
  }
  view.scan = scan;
  const status = statusLabel(scan);
  const intro = heading(scan.name, scan.description, [programUrl, "Object scan"]);
  const state = el("p", `scan-callout${scan.error ? " scan-error" : ""}`, status);
  state.setAttribute("role", "status");
  intro.append(state);
  if (scan.robot_count) intro.append(el("p", "", `Planned holding arms · ${scan.robot_count}`));
  if (scan.error) intro.append(feedback(typeof scan.error === "string" ? scan.error : scan.error.message, true));
  const columns = el("div", "columns scan-columns");
  const left = el("div", "stack scan-stack");
  const right = el("div", "stack scan-stack");
  left.append(captureSection(view, scan), proposalSection(view, scan));
  right.append(coverageSection(view, scan));
  const dimensions = dimensionsSection(view, scan);
  if (dimensions) right.append(dimensions);
  const editor = textureEditor(scan, {
    el, button, field, options, panel, submit, cameraNames, faceNames, safeFileUrl,
    action: (container, payload) => bindAction(view, container, "Saving face texture…",
      scanAction(view, "/texture", payload)),
  });
  if (editor) right.append(editor);
  right.append(publishingSection(view, scan));
  columns.append(left, right);
  if (pending[scan.status]) {
    for (const control of columns.querySelectorAll("button, input, select, textarea")) control.disabled = true;
  }
  document.title = `${scan.name} · Object scan · UWA Robot Power`;
  view.root.replaceChildren(intro, columns);
  if (pending[scan.status]) view.timer = setTimeout(() => refreshSession(view), 1200);
}

async function refreshSession(view) {
  try {
    const scan = await view.request(`/api/scans/${view.route.id}`);
    if (activeView === view) showSession(view, scan);
  } catch (error) {
    if (activeView !== view) return;
    if (!view.scan) showLoadError(view, error);
    else {
      const notice = view.root.querySelector(".scan-poll-error") || feedback("", true);
      notice.classList.add("scan-poll-error");
      notice.textContent = `Scan status unavailable. Retrying. ${error.message}`;
      if (!notice.isConnected) view.root.querySelector("header").append(notice);
      view.timer = setTimeout(() => refreshSession(view), 2500);
    }
  }
}

function assetCard(asset) {
  const card = el("article", "panel scan-panel asset-card");
  const body = el("div", "asset-copy");
  body.append(el("strong", "status", "ASSET DRAFT"), el("h2", "", asset.name));
  if (asset.description) body.append(el("p", "", asset.description));
  const preview = safeFileUrl(asset.preview);
  if (preview) {
    const image = el("img", "asset-preview");
    image.src = preview;
    image.alt = `${asset.name} scan preview`;
    image.loading = "lazy";
    card.append(image);
  }
  if (asset.model?.dimensions_mm) {
    const size = `${asset.model.dimensions_mm.join(" × ")} mm`;
    body.append(el("p", "", ["Model dimensions", size, asset.model.dimension_source].filter(Boolean).join(" · ")));
  }
  if (asset.model?.textured_faces?.length) body.append(el("p", "", `Photo-textured faces · ${asset.model.textured_faces.length} of 6`));
  if (asset.coverage?.summary) body.append(el("p", "", asset.coverage.summary));
  if (asset.coverage?.missing_views?.length) {
    body.append(el("h3", "", "Missing views"), smallList(asset.coverage.missing_views));
  }
  const saved = dateLabel(asset.updated_at || asset.created_at);
  if (saved) body.append(el("p", "asset-date", `Saved ${saved}`));
  const files = el("div", "run-buttons");
  for (const file of asset.files || []) {
    const url = safeFileUrl(file.url);
    if (url) {
      const download = link(url, "button secondary", file.label);
      download.download = "";
      files.append(download);
    }
  }
  if (files.childElementCount) body.append(files);
  body.append(link(scanUrl(asset.scan_id || asset.id), "text-link", "Open source scan"));
  card.append(body);
  return card;
}

function renderAssets(view, assets) {
  const intro = heading("Asset library", "Browse scanned objects and download their saved drafts.", ["#library", "Program library"]);
  const start = link(programUrl, "button primary", "Open Object scan");
  intro.append(start);
  if (!assets.length) {
    view.root.replaceChildren(intro, panel("No saved asset drafts", el("p", "", "Create an Object scan to add the first asset.")));
    return;
  }
  const filter = el("input");
  filter.type = "search";
  filter.placeholder = "Name or description";
  const results = el("div", "program-list");
  const status = el("p", "asset-filter-result", "");
  status.setAttribute("role", "status");
  const cards = assets.map(asset => [asset, assetCard(asset)]);
  const update = () => {
    const query = filter.value.trim().toLowerCase();
    let shown = 0;
    for (const [asset, card] of cards) {
      card.hidden = !`${asset.name} ${asset.description || ""}`.toLowerCase().includes(query);
      if (!card.hidden) shown++;
    }
    status.textContent = shown ? "" : "No asset drafts match this search.";
  };
  filter.addEventListener("input", update);
  results.append(...cards.map(([, card]) => card));
  view.root.replaceChildren(intro, field("Search assets", filter), status, results);
}

function showLoadError(view, error) {
  const title = view.route.kind === "assets" ? "Asset library" : "Object scan";
  view.root.replaceChildren(heading(title, "", ["#library", "Program library"]),
    panel("Could not load this page", feedback(error.message, true), button("Try again", "secondary", () => load(view))));
}

async function load(view) {
  if (view.route.kind === "session") {
    await refreshSession(view);
    return;
  }
  try {
    const assets = view.route.kind === "assets";
    const result = await view.request(assets ? "/api/assets" : "/api/scans");
    if (activeView !== view) return;
    if (assets) renderAssets(view, result.assets);
    else renderPrograms(view, result.scans);
  } catch (error) {
    if (activeView === view) showLoadError(view, error);
  }
}

export function leaveScanView() {
  if (activeView) clearTimeout(activeView.timer);
  activeView = null;
}

export function scanRoute(hash) {
  if (hash === "#assets") return { kind: "assets" };
  if (hash === programUrl) return { kind: "program" };
  if (/^#scan\/[a-f0-9]{32}$/.test(hash)) return { kind: "session", id: hash.slice(6) };
  return null;
}

export function renderScanView(root, route, request) {
  if (activeView?.route.kind === route.kind && activeView.route.id === route.id) return;
  leaveScanView();
  const title = route.kind === "assets" ? "Asset library" : "Object scan";
  document.title = `${title} · UWA Robot Power`;
  root.replaceChildren(heading(title, "", ["#library", "Program library"]), feedback("Loading…"));
  activeView = { root, route, request };
  load(activeView);
}

export function renderAssetLink() {
  return panel("Asset library", el("p", "", "Browse captured objects and their model drafts."),
    link("#assets", "button secondary", "Open Asset library"));
}

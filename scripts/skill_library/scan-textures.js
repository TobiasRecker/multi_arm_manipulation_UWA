const directions = {
  "+x": ["+Y", "+Z"], "-x": ["−Y", "+Z"], "+y": ["−X", "+Z"],
  "-y": ["+X", "+Z"], "+z": ["+X", "+Y"], "-z": ["+X", "−Y"],
};
const cornerNames = ["Lower left", "Lower right", "Upper right", "Upper left"];

export function textureEditor(scan, ui) {
  if (scan.shape !== "box") return null;
  const { el, button, field, options, panel, submit, cameraNames, faceNames, safeFileUrl, action } = ui;
  const sources = scan.captures.flatMap(capture => (capture.files || [])
    .filter(file => safeFileUrl(file.url))
    .map(file => ({ capture, file })));
  if (!sources.length) return null;

  const form = el("form", "scan-form scan-texture");
  const face = options(Object.entries(faceNames));
  const photo = options(sources.map(({ capture, file }, index) => [String(index),
    `${capture.label} · ${cameraNames[file.camera] || file.camera}`]));
  const hint = el("p", "", "");
  const loadStatus = el("p", "", "");
  loadStatus.setAttribute("role", "status");
  const canvas = el("canvas", "scan-texture-image");
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", "Native photo with numbered texture corners");
  canvas.hidden = true;
  canvas.append(el("span", "", "Use the normalized coordinate fields to select corners."));
  const context = canvas.getContext("2d");
  const coordinates = el("div", "scan-corner-grid");
  const pairs = cornerNames.map((name, index) => {
    const pair = el("fieldset", "scan-corners");
    pair.append(el("legend", "", `${index + 1} · ${name}`));
    const inputs = ["X", "Y"].map(axis => {
      const input = el("input");
      input.type = "number";
      input.required = true;
      input.min = "0";
      input.max = "1";
      input.step = "any";
      pair.append(field(axis, input));
      return input;
    });
    coordinates.append(pair);
    return inputs;
  });
  const reset = button("Clear corners", "secondary");
  const axes = el("p", "", "X, Y and Z refer to the draft model’s length, width and height.");
  const saved = el("p", "", "");
  let image = null;
  let generation = 0;
  let selectedCorner = 0;
  let existing = null;

  function draw() {
    if (!image || !context) return;
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const points = pairs.map(([x, y]) => [x.valueAsNumber * canvas.width, y.valueAsNumber * canvas.height]);
    const edges = points.filter(point => point.every(Number.isFinite));
    if (edges.length > 1) {
      context.beginPath();
      for (const [x, y] of edges) context.lineTo(x, y);
      if (edges.length === 4) context.closePath();
      context.lineWidth = 4;
      context.strokeStyle = "#17232c";
      context.stroke();
      context.lineWidth = 2;
      context.strokeStyle = "#ffdd4a";
      context.stroke();
    }
    points.forEach(([x, y], index) => {
      if (!Number.isFinite(x) || !Number.isFinite(y)) return;
      context.beginPath();
      context.arc(x, y, 9, 0, Math.PI * 2);
      context.fillStyle = "#ffdd4a";
      context.fill();
      context.strokeStyle = "#17232c";
      context.lineWidth = 2;
      context.stroke();
      context.font = "bold 13px sans-serif";
      context.textAlign = "center";
      context.textBaseline = "middle";
      context.fillStyle = "#17232c";
      context.fillText(String(index + 1), x, y);
    });
  }

  function setCorners(corners = []) {
    pairs.forEach((pair, index) => pair.forEach((input, axis) => {
      input.value = corners[index]?.[axis] ?? "";
    }));
    selectedCorner = corners.length % 4;
    draw();
  }

  function loadPhoto() {
    const { capture, file } = sources[Number(photo.value)];
    const token = ++generation;
    image = null;
    canvas.hidden = true;
    setCorners(existing?.capture_id === capture.id && existing.camera === file.camera ? existing.corners : []);
    loadStatus.textContent = "Loading the native photo…";
    const source = new Image();
    source.onload = () => {
      if (token !== generation) return;
      image = source;
      const scale = Math.min(1, 840 / image.naturalWidth, 720 / image.naturalHeight);
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
      canvas.hidden = !context;
      loadStatus.textContent = context ? "" : "Enter corner coordinates directly.";
      draw();
    };
    source.onerror = () => {
      if (token === generation) loadStatus.textContent = "Could not load the native photo.";
    };
    source.src = file.url;
  }

  function selectFace() {
    const [right, up] = directions[face.value];
    hint.textContent = `Look at the chosen face from the outside. Use ${right} as right and ${up} as up to identify the four corners.`;
    existing = (scan.textures || []).find(texture => texture.face === face.value);
    saved.textContent = existing ? "This face already has a saved assignment." : "";
    if (existing) {
      const index = sources.findIndex(({ capture, file }) => capture.id === existing.capture_id && file.camera === existing.camera);
      if (index >= 0) photo.value = String(index);
    }
    loadPhoto();
  }

  form.append(el("p", "", "Use a photo with all four corners of the face visible. Click the corners in order or enter normalized coordinates from 0 to 1, measured from the top left of the native image."),
    axes, field("Model face", face), field("Source photo", photo), hint, saved, loadStatus, canvas, coordinates, reset);
  submit(form, "Save face texture", "secondary");
  form.addEventListener("submit", event => { event.preventDefault(); save(); });
  const save = action(form, () => {
    const { capture, file } = sources[Number(photo.value)];
    return { face: face.value, capture_id: capture.id, camera: file.camera,
      corners: pairs.map(pair => pair.map(input => input.valueAsNumber)) };
  });
  reset.addEventListener("click", () => setCorners());
  photo.addEventListener("change", loadPhoto);
  face.addEventListener("change", selectFace);
  coordinates.addEventListener("input", draw);
  canvas.addEventListener("click", event => {
    const rect = canvas.getBoundingClientRect();
    const point = [(event.clientX - rect.left) / rect.width, (event.clientY - rect.top) / rect.height];
    pairs[selectedCorner].forEach((input, axis) => { input.value = Math.max(0, Math.min(1, point[axis])).toFixed(5); });
    selectedCorner = (selectedCorner + 1) % 4;
    draw();
  });
  const details = el("details", "scan-optional");
  const count = (scan.textures || []).length;
  details.append(el("summary", "", count ? `Assign photo textures · ${count} of 6 faces` : "Assign photo textures"), form);
  details.addEventListener("toggle", () => {
    if (details.open && !generation) selectFace();
  });
  return panel("Rectangular model textures", details);
}

const form = document.querySelector("#uploadForm");
const fileInput = document.querySelector("#plateImage");
const fileLabel = document.querySelector("#fileLabel");
const dropZone = document.querySelector("#dropZone");
const processButton = document.querySelector("#processButton");
const clearButton = document.querySelector("#clearButton");
const plateValue = document.querySelector("#plateValue");
const confidenceValue = document.querySelector("#confidenceValue");
const summaryText = document.querySelector("#summaryText");
const summaryTitle = document.querySelector("#summaryTitle");
const savePath = document.querySelector("#savePath");
const stageImage = document.querySelector("#stageImage");
const stageTitle = document.querySelector("#stageTitle");
const stageCounter = document.querySelector("#stageCounter");
const prevStage = document.querySelector("#prevStage");
const nextStage = document.querySelector("#nextStage");
const connectionStatus = document.querySelector("#connectionStatus");
const processCropButton = document.querySelector("#processCropButton");
const useVehicleButton = document.querySelector("#useVehicleButton");
const refreshHistoryButton = document.querySelector("#refreshHistoryButton");
const historyList = document.querySelector("#historyList");
const historyDetail = document.querySelector("#historyDetail");
const historySearch = document.querySelector("#historySearch");
const historyMode = document.querySelector("#historyMode");
const historyStatus = document.querySelector("#historyStatus");
const historyReason = document.querySelector("#historyReason");
const historyDateFrom = document.querySelector("#historyDateFrom");
const historyDateTo = document.querySelector("#historyDateTo");
const resultTabs = document.querySelectorAll(".result-tab");

let stages = [];
let currentStage = 0;
let originalFile = null;
let lastVehicleCropBase64 = null;
let lastPlateCropBase64 = null;
let sessionResults = {};
let activeResultMode = null;

function getMode() {
  return new FormData(form).get("mode") || "detect";
}

function modeText(mode = getMode()) {
  if (mode === "vehicle") return "Detectar carro";
  if (mode === "ocr") return "Leer texto OCR";
  return "Detectar placa";
}

function setStatus(text, className = "") {
  connectionStatus.textContent = text;
  connectionStatus.className = `status-pill ${className}`.trim();
}

function setLoading(isLoading) {
  processButton.disabled = isLoading;
  processButton.textContent = isLoading ? "Procesando..." : modeText();
}

function setFile(file, keepOriginal = true) {
  const dataTransfer = new DataTransfer();
  dataTransfer.items.add(file);
  fileInput.files = dataTransfer.files;
  if (keepOriginal) originalFile = file;
  updateFileLabel();
}

function updateModeLabels() {
  const mode = getMode();
  processButton.textContent = modeText(mode);
  summaryTitle.textContent =
    mode === "vehicle" ? "Deteccion de carro" : mode === "ocr" ? "Lectura OCR" : "Deteccion PDI";
}

function updateFileLabel() {
  const file = fileInput.files[0];
  fileLabel.textContent = file ? file.name : "Seleccionar imagen";
  if (file && (!originalFile || !file.name.startsWith("recorte_"))) {
    originalFile = file;
  }
}

function renderStage() {
  if (!stages.length) {
    stageCounter.textContent = "0 / 0";
    return;
  }

  const stage = stages[currentStage];
  stageImage.src = stage.image;
  stageTitle.textContent = stage.title;
  stageCounter.textContent = `${currentStage + 1} / ${stages.length}`;
}

function updateResultTabs() {
  resultTabs.forEach((button) => {
    const mode = button.dataset.resultMode;
    const hasResult = Boolean(sessionResults[mode]);
    button.disabled = !hasResult;
    button.classList.toggle("active", mode === activeResultMode && hasResult);
  });
}

function showSessionResult(mode) {
  const item = sessionResults[mode];
  if (!item) return;

  activeResultMode = mode;
  stages = item.stages || [];
  currentStage = item.currentStage || 0;
  plateValue.textContent = item.data.plate || "Sin resultado";
  confidenceValue.textContent = `${Math.round((item.data.confidence || 0) * 100)}%`;
  savePath.textContent = item.data.savedDir || "Resultado no guardado";
  renderAnalysisReport(item.data, mode);
  renderStage();
  updateResultTabs();
  setStatus(item.data.type || "Procesado", "is-success");
}

function setContextButtons() {
  useVehicleButton.style.display = lastVehicleCropBase64 ? "inline-block" : "none";
  processCropButton.style.display = lastPlateCropBase64 ? "inline-block" : "none";
}

function resetResults() {
  stages = [];
  currentStage = 0;
  originalFile = null;
  lastVehicleCropBase64 = null;
  lastPlateCropBase64 = null;
  sessionResults = {};
  activeResultMode = null;
  plateValue.textContent = "Sin procesar";
  confidenceValue.textContent = "0%";
  summaryText.innerHTML = `<p class="empty-state">Los detalles del procesamiento apareceran aqui.</p>`;
  savePath.textContent = "Pendiente";
  stageImage.src = "/samples/edomex.jpg";
  stageTitle.textContent = "Vista previa";
  stageCounter.textContent = "0 / 0";
  summaryText.classList.remove("is-error", "is-success");
  setContextButtons();
  updateResultTabs();
  setStatus("Laboratorio academico");
  updateModeLabels();
}

function renderAnalysisReport(data, mode) {
  const report = data.report || {};
  const summary = data.summary || [];
  const bbox = data.bbox || report?.plate?.bbox || report?.vehicle?.bbox;
  const parts = report.plateParts || [];
  const texts = report.allTexts || [];
  const summaryItems = summary
    .filter(line => line && !line.startsWith("="))
    .slice(0, 8);

  summaryText.innerHTML = `
    <div class="report-grid">
      <div class="metric-card">
        <span>Resultado</span>
        <strong>${escapeHtml(data.plate || "Sin resultado")}</strong>
      </div>
      <div class="metric-card">
        <span>Confianza</span>
        <strong>${Math.round((data.confidence || 0) * 100)}%</strong>
      </div>
      <div class="metric-card">
        <span>Servicio</span>
        <strong>${escapeHtml(formatMode(mode))}</strong>
      </div>
      <div class="metric-card">
        <span>Motivo</span>
        <strong>${escapeHtml(data.reasonLabel || formatReason(data.reason))}</strong>
      </div>
    </div>
    ${
      bbox
        ? `<div class="bbox-strip">
            <span>x=${bbox[0]}</span><span>y=${bbox[1]}</span><span>w=${bbox[2]}</span><span>h=${bbox[3]}</span>
          </div>`
        : ""
    }
    ${
      parts.length
        ? `<div class="report-section"><h3>Fragmentos OCR</h3>${parts.map(item => `<p>${escapeHtml(item.text)} <span>${Math.round((item.confidence || 0) * 100)}%</span></p>`).join("")}</div>`
        : ""
    }
    ${
      texts.length
        ? `<div class="report-section"><h3>Textos detectados</h3>${texts.map(item => `<p>${escapeHtml(item.text)} <span>${Math.round((item.confidence || 0) * 100)}%</span></p>`).join("")}</div>`
        : ""
    }
    <div class="report-section">
      <h3>Analisis</h3>
      ${
        summaryItems.length
          ? summaryItems.map(line => `<p>${escapeHtml(line)}</p>`).join("")
          : "<p>No hay detalles adicionales.</p>"
      }
    </div>
  `;
}

async function dataUrlToFile(dataUrl, filename) {
  const response = await fetch(dataUrl);
  const blob = await response.blob();
  return new File([blob], filename, { type: blob.type || "image/png" });
}

function endpointForMode(mode) {
  if (mode === "vehicle") return "/api/vehicle";
  if (mode === "ocr") return "/api/process";
  return "/api/detect";
}

function waitTextForMode(mode) {
  if (mode === "vehicle") return "Detectando el carro principal con PDI clasico...";
  if (mode === "ocr") return "Ejecutando OCR sobre la imagen seleccionada...";
  return "Detectando regiones candidatas de placa...";
}

async function processImage(event) {
  event.preventDefault();

  if (!fileInput.files.length) {
    summaryText.innerHTML = `<p class="empty-state is-error">Seleccione una imagen antes de procesar.</p>`;
    summaryText.classList.add("is-error");
    return;
  }

  const mode = getMode();
  setLoading(true);
  setStatus("Procesando");
  summaryText.classList.remove("is-error", "is-success");
    summaryText.innerHTML = `<p class="empty-state">${escapeHtml(waitTextForMode(mode))}</p>`;

  const formData = new FormData();
  formData.append("mode", mode);
  formData.append("plate_image", fileInput.files[0]);
  if (mode === "ocr" && originalFile) {
    formData.append("original_image", originalFile);
  }

  try {
    const response = await fetch(endpointForMode(mode), {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.error || "No se pudo procesar la imagen.");
    }

    sessionResults[mode] = {
      data,
      stages: data.stages || [],
      currentStage: 0,
    };

    if (data.vehicleCrop) lastVehicleCropBase64 = data.vehicleCrop;
    if (data.plateCrop || data.crop) lastPlateCropBase64 = data.plateCrop || data.crop;
    setContextButtons();

    summaryText.classList.add("is-success");
    showSessionResult(mode);
    await loadHistory();
  } catch (error) {
    plateValue.textContent = "Error";
    confidenceValue.textContent = "0%";
    summaryText.innerHTML = `<p class="empty-state is-error">${escapeHtml(error.message)}</p>`;
    summaryText.classList.add("is-error");
    setStatus("Error", "is-error");
  } finally {
    setLoading(false);
  }
}

function formatMode(mode) {
  if (mode === "vehicle") return "Carro";
  if (mode === "ocr") return "OCR";
  if (mode === "detect") return "Placa";
  return mode || "Proceso";
}

function formatReason(reason) {
  if (reason === "possible_collision") return "Posible choque";
  if (reason === "circuit_button") return "Activacion del boton";
  return "Procesado en web";
}

function formatDate(value) {
  if (!value) return "Sin fecha";
  return new Date(value).toLocaleString("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function reportHtml(detection) {
  const report = detection.report || {};
  const parts = report.plateParts || [];
  const texts = report.allTexts || [];
  const plate = typeof report.plate === "string" ? report.plate : detection.plate || "No detectada";
  const confidence = Math.round((report.confidence ?? detection.confidence ?? 0) * 100);

  return `
    <div class="report-grid">
      <div class="metric-card">
        <span>Matricula</span>
        <strong>${escapeHtml(plate)}</strong>
      </div>
      <div class="metric-card">
        <span>Confianza</span>
        <strong>${confidence}%</strong>
      </div>
      <div class="metric-card">
        <span>Modo</span>
        <strong>${escapeHtml(formatMode(detection.mode))}</strong>
      </div>
      <div class="metric-card">
        <span>Motivo</span>
        <strong>${escapeHtml(detection.reasonLabel || formatReason(detection.reason))}</strong>
      </div>
    </div>
    <div class="report-section">
      <h3>Fragmentos de matricula</h3>
      ${
        parts.length
          ? parts.map(item => `<p>${escapeHtml(item.text)} <span>${Math.round((item.confidence || 0) * 100)}%</span></p>`).join("")
          : "<p>No hay fragmentos OCR guardados.</p>"
      }
    </div>
    <div class="report-section">
      <h3>Textos detectados</h3>
      ${
        texts.length
          ? texts.map(item => `<p>${escapeHtml(item.text)} <span>${Math.round((item.confidence || 0) * 100)}%</span></p>`).join("")
          : "<p>No hay textos OCR guardados.</p>"
      }
    </div>
  `;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function loadHistory() {
  if (!historyList) return;
  try {
    const params = new URLSearchParams();
    if (historySearch.value.trim()) params.set("q", historySearch.value.trim());
    if (historyMode.value) params.set("mode", historyMode.value);
    if (historyStatus.value) params.set("status_filter", historyStatus.value);
    if (historyReason.value) params.set("reason", historyReason.value);
    if (historyDateFrom.value) params.set("date_from", historyDateFrom.value);
    if (historyDateTo.value) params.set("date_to", historyDateTo.value);

    const response = await fetch(`/api/detections?${params.toString()}`);
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || "No se pudo cargar el historial.");

    const detections = data.detections || [];
    if (!detections.length) {
      historyList.innerHTML = `<p class="empty-state">Todavia no hay detecciones guardadas.</p>`;
      return;
    }

    historyList.innerHTML = detections.map(item => `
      <button class="history-item" type="button" data-id="${item.id}">
        <span>${escapeHtml(formatMode(item.mode))}</span>
        <strong>${escapeHtml(item.plate)}</strong>
        <small>${escapeHtml(formatDate(item.timestamp))}</small>
        <small>${escapeHtml(item.reasonLabel || formatReason(item.reason))}</small>
        <em>${item.detected ? "Detectada" : "No detectada"}</em>
      </button>
    `).join("");
  } catch (error) {
    historyList.innerHTML = `<p class="empty-state is-error">${escapeHtml(error.message)}</p>`;
  }
}

async function loadDetectionDetail(id) {
  const response = await fetch(`/api/detections/${id}`);
  const data = await response.json();
  if (!response.ok || !data.ok) throw new Error(data.error || "No se pudo cargar el detalle.");
  const detection = data.detection;
  const images = detection.images || {};

  historyDetail.innerHTML = `
    <div class="history-detail-header">
      <div>
        <p class="eyebrow">${escapeHtml(formatMode(detection.mode))}</p>
        <h2>${escapeHtml(detection.plate)}</h2>
        <small>${escapeHtml(detection.reasonLabel || formatReason(detection.reason))}</small>
      </div>
      <span class="confidence">${Math.round((detection.confidence || 0) * 100)}%</span>
    </div>
    <div class="history-images">
      <figure class="${images.original ? "" : "is-empty"}">
        ${images.original ? `<img src="${images.original}" alt="Imagen original">` : `<div>Sin imagen original</div>`}
        <figcaption>Original</figcaption>
      </figure>
      <figure class="${images.plateCrop ? "" : "is-empty"}">
        ${images.plateCrop ? `<img src="${images.plateCrop}" alt="Recorte de placa">` : `<div>Sin recorte de placa</div>`}
        <figcaption>Recorte de placa</figcaption>
      </figure>
    </div>
    ${reportHtml(detection)}
  `;
}

fileInput.addEventListener("change", updateFileLabel);
form.addEventListener("submit", processImage);

form.querySelectorAll('input[name="mode"]').forEach((input) => {
  input.addEventListener("change", updateModeLabels);
});

clearButton.addEventListener("click", () => {
  form.reset();
  updateFileLabel();
  resetResults();
});

useVehicleButton.addEventListener("click", async () => {
  if (!lastVehicleCropBase64) return;
  const file = await dataUrlToFile(lastVehicleCropBase64, "recorte_carro.png");
  setFile(file, false);
  document.querySelector('input[name="mode"][value="detect"]').checked = true;
  updateModeLabels();
  form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
});

processCropButton.addEventListener("click", async () => {
  if (!lastPlateCropBase64) return;
  const file = await dataUrlToFile(lastPlateCropBase64, "recorte_placa.png");
  setFile(file, false);
  document.querySelector('input[name="mode"][value="ocr"]').checked = true;
  updateModeLabels();
  form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
});

prevStage.addEventListener("click", () => {
  if (!stages.length) return;
  currentStage = (currentStage - 1 + stages.length) % stages.length;
  if (activeResultMode && sessionResults[activeResultMode]) {
    sessionResults[activeResultMode].currentStage = currentStage;
  }
  renderStage();
});

nextStage.addEventListener("click", () => {
  if (!stages.length) return;
  currentStage = (currentStage + 1) % stages.length;
  if (activeResultMode && sessionResults[activeResultMode]) {
    sessionResults[activeResultMode].currentStage = currentStage;
  }
  renderStage();
});

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("is-dragging");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("is-dragging");
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("is-dragging");

  if (event.dataTransfer.files.length) {
    setFile(event.dataTransfer.files[0], true);
  }
});

historyList.addEventListener("click", async (event) => {
  const item = event.target.closest(".history-item");
  if (!item) return;
  historyList.querySelectorAll(".history-item").forEach(button => button.classList.remove("active"));
  item.classList.add("active");
  historyDetail.innerHTML = `<p class="empty-state">Cargando detalle...</p>`;
  try {
    await loadDetectionDetail(item.dataset.id);
  } catch (error) {
    historyDetail.innerHTML = `<p class="empty-state is-error">${escapeHtml(error.message)}</p>`;
  }
});

refreshHistoryButton.addEventListener("click", (event) => {
  event.preventDefault();
  loadHistory();
});

[historySearch, historyMode, historyStatus, historyReason, historyDateFrom, historyDateTo].forEach(control => {
  if (!control) return;
  control.addEventListener("input", loadHistory);
  control.addEventListener("change", loadHistory);
});

resultTabs.forEach((button) => {
  button.addEventListener("click", () => {
    showSessionResult(button.dataset.resultMode);
  });
});

const tabButtons = document.querySelectorAll(".tab-button");
const sourceSections = document.querySelectorAll(".source-section");
const cameraSelect = document.querySelector("#cameraSelect");
const cameraStream = document.querySelector("#cameraStream");
const captureButton = document.querySelector("#captureButton");
const cameraCanvas = document.querySelector("#cameraCanvas");

let currentStream = null;

function stopCamera() {
  if (currentStream) {
    currentStream.getTracks().forEach(track => track.stop());
    currentStream = null;
  }
  if (cameraStream) cameraStream.srcObject = null;
}

async function startCamera(deviceId = null) {
  stopCamera();
  const constraints = {
    video: deviceId ? { deviceId: { exact: deviceId } } : { facingMode: "environment" }
  };

  try {
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    currentStream = stream;
    cameraStream.srcObject = stream;
    await cameraStream.play().catch(error => console.warn("Video play error:", error));
  } catch (err) {
    if (err.name === "NotReadableError" || err.name === "TrackStartError") {
      summaryText.innerHTML = `<p class="empty-state is-error">La camara esta siendo usada por otra app. Cierrala e intenta de nuevo.</p>`;
    } else {
      summaryText.innerHTML = `<p class="empty-state is-error">No se pudo acceder a la camara. Revisa los permisos.</p>`;
    }
    summaryText.classList.add("is-error");
    throw err;
  }
}

async function loadCameras() {
  try {
    if (!currentStream) {
      await startCamera().catch(() => {});
    }

    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(device => device.kind === "videoinput");

    cameraSelect.innerHTML = "";
    if (videoDevices.length === 0) {
      cameraSelect.innerHTML = "<option value=''>No se encontraron camaras</option>";
      return;
    }

    videoDevices.forEach((device, index) => {
      const option = document.createElement("option");
      option.value = device.deviceId;
      option.text = device.label || `Camara ${index + 1}`;
      cameraSelect.appendChild(option);
    });
  } catch (err) {
    cameraSelect.innerHTML = "<option value=''>Error al cargar camaras</option>";
  }
}

tabButtons.forEach(button => {
  button.addEventListener("click", () => {
    tabButtons.forEach(btn => btn.classList.remove("active"));
    sourceSections.forEach(sec => sec.style.display = "none");

    button.classList.add("active");
    const targetId = button.getAttribute("data-target");
    document.getElementById(targetId).style.display = "block";

    if (targetId === "cameraSection") loadCameras();
    else stopCamera();
  });
});

if (cameraSelect) {
  cameraSelect.addEventListener("change", (event) => {
    startCamera(event.target.value);
  });
}

if (captureButton) {
  captureButton.addEventListener("click", () => {
    if (!currentStream) return;

    const context = cameraCanvas.getContext("2d");
    cameraCanvas.width = cameraStream.videoWidth || 640;
    cameraCanvas.height = cameraStream.videoHeight || 480;
    context.drawImage(cameraStream, 0, 0, cameraCanvas.width, cameraCanvas.height);

    cameraCanvas.toBlob((blob) => {
      const file = new File([blob], "captura_camara.png", { type: "image/png" });
      setFile(file, true);
      document.querySelector('[data-target="uploadSection"]').click();
      summaryText.innerHTML = `<p class="empty-state">Foto capturada correctamente. Selecciona un modo y procesa la imagen.</p>`;
      summaryText.classList.remove("is-error");
      summaryText.classList.add("is-success");
    }, "image/png");
  });
}

resetResults();
loadHistory();

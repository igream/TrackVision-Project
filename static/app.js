const form = document.querySelector("#uploadForm");
const fileInput = document.querySelector("#plateImage");
const fileLabel = document.querySelector("#fileLabel");
const dropZone = document.querySelector("#dropZone");
const processButton = document.querySelector("#processButton");
const clearButton = document.querySelector("#clearButton");
const plateValue = document.querySelector("#plateValue");
const confidenceValue = document.querySelector("#confidenceValue");
const summaryText = document.querySelector("#summaryText");
const savePath = document.querySelector("#savePath");
const stageImage = document.querySelector("#stageImage");
const stageTitle = document.querySelector("#stageTitle");
const stageCounter = document.querySelector("#stageCounter");
const prevStage = document.querySelector("#prevStage");
const nextStage = document.querySelector("#nextStage");
const connectionStatus = document.querySelector("#connectionStatus");

let stages = [];
let currentStage = 0;

function setStatus(text, className = "") {
  connectionStatus.textContent = text;
  connectionStatus.className = `status-pill ${className}`.trim();
}

function setLoading(isLoading) {
  processButton.disabled = isLoading;
  processButton.textContent = isLoading ? "Procesando..." : "Procesar placa";
}

function updateFileLabel() {
  const file = fileInput.files[0];
  fileLabel.textContent = file ? file.name : "Seleccionar imagen";
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

function resetResults() {
  stages = [];
  currentStage = 0;
  plateValue.textContent = "Sin procesar";
  confidenceValue.textContent = "0%";
  summaryText.textContent = "Los detalles del procesamiento aparecerán aquí.";
  savePath.textContent = "Pendiente de guardado";
  stageImage.src = "/samples/edomex.jpg";
  stageTitle.textContent = "Vista previa";
  stageCounter.textContent = "0 / 0";
  summaryText.classList.remove("is-error", "is-success");
  setStatus("Web local");
}

async function processImage(event) {
  event.preventDefault();

  if (!fileInput.files.length) {
    summaryText.textContent = "Seleccione una imagen antes de procesar.";
    summaryText.classList.add("is-error");
    return;
  }

  setLoading(true);
  setStatus("Procesando");
  summaryText.classList.remove("is-error", "is-success");
  summaryText.textContent = "Analizando imagen, detectando contornos y ejecutando OCR...";

  const formData = new FormData(form);

  try {
    const response = await fetch("/api/process", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.error || "No se pudo procesar la imagen.");
    }

    stages = data.stages || [];
    currentStage = 0;
    plateValue.textContent = data.plate;
    confidenceValue.textContent = `${Math.round((data.confidence || 0) * 100)}%`;
    savePath.textContent = data.savedDir || "Resultado no guardado";
    summaryText.textContent = (data.summary || []).join("\n");
    summaryText.classList.add("is-success");
    renderStage();
    setStatus(data.type || "Procesado", "is-success");
  } catch (error) {
    plateValue.textContent = "Error";
    confidenceValue.textContent = "0%";
    summaryText.textContent = error.message;
    summaryText.classList.add("is-error");
    setStatus("Error", "is-error");
  } finally {
    setLoading(false);
  }
}

fileInput.addEventListener("change", updateFileLabel);
form.addEventListener("submit", processImage);

clearButton.addEventListener("click", () => {
  form.reset();
  updateFileLabel();
  resetResults();
});

prevStage.addEventListener("click", () => {
  if (!stages.length) {
    return;
  }
  currentStage = (currentStage - 1 + stages.length) % stages.length;
  renderStage();
});

nextStage.addEventListener("click", () => {
  if (!stages.length) {
    return;
  }
  currentStage = (currentStage + 1) % stages.length;
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
    fileInput.files = event.dataTransfer.files;
    updateFileLabel();
  }
});

resetResults();

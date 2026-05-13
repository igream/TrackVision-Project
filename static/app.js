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

let stages = [];
let currentStage = 0;
let lastCropBase64 = null;

function getMode() {
  return new FormData(form).get("mode") || "detect";
}

function getModeText() {
  return getMode() === "detect" ? "Detectar placa" : "Leer texto OCR";
}

function setStatus(text, className = "") {
  connectionStatus.textContent = text;
  connectionStatus.className = `status-pill ${className}`.trim();
}

function setLoading(isLoading) {
  processButton.disabled = isLoading;
  processButton.textContent = isLoading ? "Procesando..." : getModeText();
}

function updateModeLabels() {
  processButton.textContent = getModeText();
  summaryTitle.textContent = getMode() === "detect" ? "Deteccion PDI" : "Lectura OCR";
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
  lastCropBase64 = null;
  if (processCropButton) processCropButton.style.display = "none";
  plateValue.textContent = "Sin procesar";
  confidenceValue.textContent = "0%";
  summaryText.textContent = "Los detalles del procesamiento apareceran aqui.";
  savePath.textContent = "Pendiente";
  stageImage.src = "/samples/edomex.jpg";
  stageTitle.textContent = "Vista previa";
  stageCounter.textContent = "0 / 0";
  summaryText.classList.remove("is-error", "is-success");
  setStatus("Laboratorio academico");
  updateModeLabels();
}

async function processImage(event) {
  event.preventDefault();

  if (!fileInput.files.length) {
    summaryText.textContent = "Seleccione una imagen antes de procesar.";
    summaryText.classList.add("is-error");
    return;
  }

  const mode = getMode();
  const endpoint = mode === "detect" ? "/api/detect" : "/api/process";
  const waitText =
    mode === "detect"
      ? "Analizando bordes, morfologia y contornos candidatos..."
      : "Analizando imagen, detectando contornos y ejecutando OCR...";

  setLoading(true);
  setStatus("Procesando");
  summaryText.classList.remove("is-error", "is-success");
  summaryText.textContent = waitText;

  const formData = new FormData(form);

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.error || "No se pudo procesar la imagen.");
    }

    stages = data.stages || [];
    currentStage = 0;
    
    if (mode === "detect" && data.crop) {
      lastCropBase64 = data.crop;
      if (processCropButton) processCropButton.style.display = "inline-block";
    } else {
      lastCropBase64 = null;
      if (processCropButton) processCropButton.style.display = "none";
    }
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

form.querySelectorAll('input[name="mode"]').forEach((input) => {
  input.addEventListener("change", updateModeLabels);
});

clearButton.addEventListener("click", () => {
  form.reset();
  updateFileLabel();
  resetResults();
});

if (processCropButton) {
  processCropButton.addEventListener("click", async () => {
    if (!lastCropBase64) return;

    try {
      const res = await fetch(lastCropBase64);
      const blob = await res.blob();
      const file = new File([blob], "crop.png", { type: "image/png" });
      
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      fileInput.files = dataTransfer.files;
      updateFileLabel();

      const ocrRadio = document.querySelector('input[name="mode"][value="ocr"]');
      if (ocrRadio) {
        ocrRadio.checked = true;
        updateModeLabels();
      }

      form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
    } catch (err) {
      console.error("Error al preparar el recorte para OCR:", err);
    }
  });
}

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

// Tab logic
const tabButtons = document.querySelectorAll(".tab-button");
const sourceSections = document.querySelectorAll(".source-section");

// Camera elements
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
  if (cameraStream) {
    cameraStream.srcObject = null;
  }
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
    await cameraStream.play().catch(e => console.warn("Video play error:", e));
  } catch (err) {
    console.error("Error accessing camera:", err);
    if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
      summaryText.textContent = "La cámara está siendo usada por otra app (como Teams o Zoom). Ciérrala e intenta de nuevo.";
    } else {
      summaryText.textContent = "No se pudo acceder a la cámara. Revisa los permisos.";
    }
    summaryText.classList.add("is-error");
    throw err;
  }
}

async function loadCameras() {
  try {
    let permissionGranted = false;
    if (!currentStream) {
      try {
        await startCamera();
        permissionGranted = true;
      } catch (e) {
        console.warn("Fallo al iniciar cámara inicialmente, se intentará enumerar de todos modos.");
      }
    } else {
      permissionGranted = true;
    }
    
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(device => device.kind === "videoinput");
    
    cameraSelect.innerHTML = "";
    if (videoDevices.length === 0) {
      cameraSelect.innerHTML = "<option value=''>No se encontraron cámaras</option>";
      return;
    }
    
    videoDevices.forEach((device, index) => {
      const option = document.createElement("option");
      option.value = device.deviceId;
      option.text = device.label || `Cámara ${index + 1}`;
      cameraSelect.appendChild(option);
    });
    
    if (currentStream && currentStream.getVideoTracks().length > 0) {
       const activeTrack = currentStream.getVideoTracks()[0];
       const settings = activeTrack.getSettings();
       if (settings && settings.deviceId) {
          cameraSelect.value = settings.deviceId;
       }
    } else if (permissionGranted && videoDevices.length > 0) {
       cameraSelect.value = videoDevices[0].deviceId;
    }
  } catch (err) {
    console.error("Error enumerating cameras:", err);
    cameraSelect.innerHTML = "<option value=''>Error al cargar cámaras</option>";
  }
}

if (tabButtons && tabButtons.length > 0) {
  tabButtons.forEach(button => {
    button.addEventListener("click", () => {
      tabButtons.forEach(btn => btn.classList.remove("active"));
      sourceSections.forEach(sec => sec.style.display = "none");
      
      button.classList.add("active");
      const targetId = button.getAttribute("data-target");
      document.getElementById(targetId).style.display = "block";
      
      if (targetId === "cameraSection") {
        loadCameras();
      } else {
        stopCamera();
      }
    });
  });
}

if (cameraSelect) {
  cameraSelect.addEventListener("change", (e) => {
    startCamera(e.target.value);
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
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      fileInput.files = dataTransfer.files;
      
      updateFileLabel();
      
      document.querySelector('[data-target="uploadSection"]').click();
      
      summaryText.textContent = "Foto capturada correctamente. Selecciona un modo y procesa la imagen.";
      summaryText.classList.remove("is-error");
      summaryText.classList.add("is-success");
      
    }, "image/png");
  });
}

resetResults();

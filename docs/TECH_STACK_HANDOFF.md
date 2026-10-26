# Flood Segmentation Web Application
## Technical Stack and Development Handoff

### 1. Project Overview

**Project Name:** Flood Segmentation Web Application

**Objective:** Develop a locally hosted, Dockerized web application that uses a trained DeepLabV3+ model with a MobileNetV2 backbone to segment flooded regions from satellite imagery.

The application will serve as an interactive portfolio demonstration for recruiters and other users.

**Core requirements:**
- Run entirely on localhost.
- Use FastAPI to connect the web interface to the trained model.
- Support CPU inference by default.
- Support NVIDIA GPU inference optionally.
- Use Docker and Docker Compose for reproducible setup.
- Allow users to upload supported satellite images and view predictions.
- Provide example satellite images for demonstration.
- Be shareable through GitHub without requiring manual installation of Python or Node.js dependencies.

No cloud hosting, authentication system, or database is required.

---

### 2. Recommended Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React + Vite | Interactive web interface |
| Styling | Tailwind CSS | Responsive dashboard design |
| Backend | FastAPI | REST API for model inference |
| API Communication | Axios | Frontend-to-backend HTTP requests |
| ML Framework | PyTorch | Model loading and inference |
| Model Architecture | DeepLabV3+ MobileNetV2 | Flood segmentation |
| Image Processing | NumPy, Rasterio, Pillow | Satellite image preprocessing |
| Visualization | OpenCV | Segmentation masks and image overlays |
| Web Server | Nginx | Serve frontend and proxy API requests |
| Containerization | Docker | Application packaging |
| Container Management | Docker Compose | Start frontend and backend together |
| GPU Acceleration | CUDA-enabled PyTorch | Optional NVIDIA GPU inference |
| Version Control | Git + GitHub | Source code management |

### 3. Application Architecture

```text
               User's Browser
                       |
             http://localhost:8080
                       |
                       v
           Docker Compose Environment
                       |
             +---------+---------+
             |                   |
             v                   |
       React Frontend            |
       Tailwind CSS              |
       Nginx                     |
             |                   |
             | /api/predict      |
             v                   |
       FastAPI Backend           |
             |                   |
             v                   |
       Image Preprocessing       |
             |                   |
             v                   |
       DeepLabV3+ MobileNetV2    |
             |                   |
       +-----+------+            |
       |            |            |
       v            v            |
     CPU          GPU            |
   Default      Optional         |
       |            |            |
       +-----+------+            |
             |                   |
             v                   |
      Segmentation Mask          |
             |                   |
             v                   |
       Prediction Response ------+
                       |
                       v
             Visualization in Browser
```

The frontend and backend must run in separate Docker containers.

Nginx should forward `/api/*` requests to the backend service through Docker's internal network.

### 4. Frontend Requirements

**Technologies:** React, Vite, Tailwind CSS, Axios.

Implement the following:

1. **Dashboard**
   - Project title and short description.
   - Model architecture and information.
   - Current inference device (CPU or GPU).

2. **Satellite Image Upload**
   - Upload supported satellite image formats.
   - Validate file type and size.
   - Display an image preview.
   - Provide example images stored locally.

3. **Flood Segmentation**
   - Send images to the FastAPI backend.
   - Show loading indicators during inference.
   - Display the predicted flood mask.

4. **Prediction Visualization**
   - Original satellite image.
   - Predicted flood segmentation mask.
   - Flood mask overlay.
   - Adjustable overlay opacity.

5. **Model Information**
   - Model architecture.
   - Parameter count.
   - Validated IoU and Dice scores, if available.
   - Measured inference time.
   - Current execution device.

Do not hardcode or fabricate performance metrics.

### 5. FastAPI Backend Requirements

**Technologies:** FastAPI, PyTorch, NumPy, Rasterio, Pillow, OpenCV.

Implement the following endpoints:

| Endpoint | Method | Function |
|---|---|---|
| `/api/health` | GET | Check backend availability |
| `/api/model-info` | GET | Return model information and device |
| `/api/predict` | POST | Upload image and generate segmentation |
| `/docs` | GET | FastAPI Swagger documentation on the backend |

The prediction workflow must:

1. Validate the uploaded file.
2. Read and decode the satellite image.
3. Apply the exact preprocessing used during model training.
4. Convert the image to a PyTorch tensor.
5. Transfer the tensor to the selected device.
6. Perform inference without gradient computation.
7. Convert model output into a binary flood mask using the configured threshold.
8. Generate a visualization overlay.
9. Return the results and measured inference time.

### 6. Model Integration

**Architecture:** DeepLabV3+ with MobileNetV2 backbone.

Use the existing trained model checkpoint from the FYP. Do not retrain or replace the model.

Requirements:
- Reconstruct the exact model architecture used during training.
- Load the trained model weights.
- Use `model.eval()`.
- Use `torch.inference_mode()` for inference.
- Preserve the original preprocessing pipeline.
- Use the same spectral bands, channel order, normalization, and output threshold used during training.
- Ensure model outputs are spatially aligned with the input image.

**Important:** Sentinel-1 and Sentinel-2 data must not be treated as interchangeable. Supported input types must match the trained model's expected channels and preprocessing.

If the model was trained with 256 × 256 patches, implement that input pipeline first. Larger images may require tiled inference and reconstruction.

### 7. CPU and GPU Support

The application must support two execution modes.

**CPU mode (default)**

```bash
docker compose up --build
```

Requirements:
- Work without an NVIDIA GPU.
- Use CPU-compatible PyTorch.
- Avoid CUDA runtime requirements.
- Run model inference on CPU.

**GPU mode (optional)**

```bash
docker compose -f compose.yaml -f compose.gpu.yaml up --build
```

Requirements:
- Support compatible NVIDIA GPUs.
- Use a CUDA-enabled PyTorch environment.
- Require correctly configured NVIDIA drivers and Docker GPU support.
- Run inference using CUDA when available.

**Device selection:**

```python
import torch

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)
```

Automatic device selection must happen inside the backend container.

CPU and GPU modes may require different container images or build configurations. Do not require every CPU user to install CUDA.

### 8. Docker Configuration

Use Docker Compose to manage two services.

**Frontend container**
- Node.js for the build stage.
- Nginx to serve the production React build.
- Expose port 8080 on localhost.
- Proxy API requests to the FastAPI container.

**Backend container**
- Python runtime.
- FastAPI and Uvicorn.
- PyTorch and image processing dependencies.
- Trained DeepLab model.
- Internal API port 8000.

Use a CPU-compatible backend image by default and a separate GPU-specific configuration.

No internet connection should be required after the Docker images, dependencies, model weights, and example assets have been downloaded.

### 9. Recommended Project Structure

```text
flood-segmentation-app/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.jsx
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
│
├── backend/
│   ├── main.py
│   ├── model.py
│   ├── inference.py
│   ├── preprocessing.py
│   ├── visualization.py
│   ├── requirements.txt
│   ├── requirements-gpu.txt
│   ├── Dockerfile
│   └── Dockerfile.gpu
│
├── models/
│   └── deeplabv3plus.pth
│
├── samples/
│   └── example_images/
│
├── tests/
│
├── compose.yaml
├── compose.gpu.yaml
├── .dockerignore
├── .gitignore
├── README.md
└── TECH_STACK_HANDOFF.md
```

### 10. GitHub Requirements

The GitHub repository must include:

- Complete frontend and backend source code.
- Dockerfiles and Docker Compose configuration.
- Dependencies and installation instructions.
- Sample satellite images with appropriate usage permissions.
- Instructions for providing the trained model checkpoint.
- Screenshots of the application.
- CPU and GPU execution instructions.
- Troubleshooting information.

Large model checkpoints should be distributed through Git LFS or an external model download link when appropriate. Do not assume the checkpoint will be included directly in Git.

### 11. Development Phases

**Phase 1: Model Inference Integration**
- Load the existing checkpoint.
- Reproduce the preprocessing pipeline.
- Validate predictions locally on CPU and GPU.

**Phase 2: FastAPI Development**
- Create inference API endpoints.
- Implement image validation and error handling.
- Implement mask generation and prediction responses.

**Phase 3: Frontend Development**
- Create React dashboard.
- Implement satellite image upload.
- Display segmentation predictions and overlays.
- Add model information and metrics.

**Phase 4: Dockerization**
- Create frontend and backend Dockerfiles.
- Configure Docker Compose.
- Set CPU as the default execution mode.
- Add optional NVIDIA GPU support.
- Test communication between containers.

**Phase 5: GitHub Release and Testing**
- Test clean setup using only the README instructions.
- Validate startup without a GPU.
- Confirm inference and visualization functionality.
- Verify compatibility with the supplied checkpoint.
- Add example images and documentation.
- Push the finished application to GitHub.

### 12. Acceptance Criteria

The project is considered complete when:

- [ ] Users can clone the repository.
- [ ] Users can start the application using Docker Compose.
- [ ] The website is accessible at `http://localhost:8080`.
- [ ] The backend successfully loads the trained DeepLabV3+ model.
- [ ] Satellite image preprocessing matches the training pipeline.
- [ ] Users can upload supported satellite imagery.
- [ ] The application produces flood segmentation predictions.
- [ ] Predictions are visualized as masks and overlays.
- [ ] The application runs on CPU without an NVIDIA GPU.
- [ ] Optional GPU inference works on compatible systems.
- [ ] The app does not require cloud hosting or a database.
- [ ] A new user can follow the README to reproduce the demo.

### 13. Development Constraints

- Do not introduce unnecessary cloud infrastructure.
- Do not add a database unless explicitly requested.
- Do not retrain or modify the existing model weights.
- Do not change the original preprocessing without validation.
- Prioritize a simple, reliable demonstration.
- Optimize for local reproducibility and ease of use.
- Keep CPU compatibility as a primary requirement.

**Final Deliverable:** A fully functional, Dockerized flood segmentation web application that users can run locally from a GitHub repository, with CPU inference by default and optional NVIDIA GPU acceleration.
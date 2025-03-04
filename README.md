# Crop Mapping Backend

This is a Django-based backend for crop mapping and monitoring, providing APIs to fetch Sentinel-2 and Sentinel-1 indices using ASGI.

## Prerequisites
- Python 3.9 or higher
- An ASGI server (e.g., Uvicorn)

---

## 1. Clone the Repository
```bash
git clone <your-repository-url>
cd crop_mapping_backend
```

## 2. Set Up a Virtual Environment
Create and activate a virtual environment:


```bash
python -m venv .venv
```

Activate the virtual environment:

### On macOS/Linux:
```bash
source .venv/bin/activate
```

### On Windows:
```bash
.venv\Scripts\activate
```

---

## 3. Install Python Dependencies
Install the required Python packages:

```bash
pip install -r requirements.txt
```

---

## 4. Run the Django ASGI Application
Run the Django app with Uvicorn (ASGI server) for async support:

```bash
uvicorn crop_mapping_backend.asgi:application --reload
```

- `--reload`: Enables auto-reloading for development.








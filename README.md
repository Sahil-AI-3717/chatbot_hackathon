# Chatbot Backend

This project is a FastAPI-based backend for a data analysis chatbot that uses Gemini and LangChain for code generation and data processing.

## Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

## Installation

1. **Clone or download this repository.**
2. **Install Python** (if not already installed):
   - Download from: https://www.python.org/downloads/
   - Verify installation:
     ```powershell
     python --version
     ```
3. **Install dependencies:**
   - Open a terminal in the project directory and run:
     ```powershell
     pip install -r requirements.txt
     ```

## Running the Project

1. Make sure your Excel data file is present at the path specified in `backend.py` (update `EXCEL_FILE_PATH` if needed).
2. Start the FastAPI server using Uvicorn:
   ```powershell
   uvicorn backend:app --reload
   ```
3. The API will be available at: http://127.0.0.1:8000

## API Endpoint

### POST `/api/ask`
- **Description:** Submit a question for data analysis.
- **Request Body:**
  ```json
  {
    "question": "Your question about the data."
  }
  ```
- **Response:**
  - JSON with the answer or error message.

## Example Usage

```powershell
curl -X POST "http://127.0.0.1:8000/api/ask" -H "Content-Type: application/json" -d "{\"question\": \"Give me the count of each umbrella tag per country.\"}"
```

---

For any issues, please check your Python installation, dependencies, and the path to your Excel file.

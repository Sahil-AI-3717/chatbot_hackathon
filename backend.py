import os
import json
import re
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import google.generativeai as genai
from langchain_core.prompts import ChatPromptTemplate
from io import StringIO

# --- IMPORTANT: Configure this section ---
# Replace with the actual path to your Excel file
EXCEL_FILE_PATH = 'combined france and uk.xlsx'
# Set your Gemini API key here
GEMINI_API_KEY = "AIzaSyC7ArGGt5TxvWgihT0GtwdAgNuEm69hOVo"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Chatbot Logic ---
class State(dict):
    pass

system_message = """
You are a world-class data analyst who writes clean, correct, and efficient Python code to answer user questions.

Given a user's question and a pandas DataFrame named `df`, your task is to write a complete Python function named `answer_query`. This function should take the DataFrame as input and perform the necessary data manipulation to answer the question.

The DataFrame `df` has the following columns:
{df_info}

The code should be self-contained within the function and use the pandas library to process the data. The function must return a variable named `result_data` which contains the final answer. `result_data` should be a pandas DataFrame or a list of dictionaries, formatted to be easily converted to JSON. Do not return a string.

Here is an example of a good response for the question: "Give me the count of each umbrella tag per country."
```python
def answer_query(df):
    # Split the 'Umbrella Tags' column into individual tags
    df_exploded = df.assign(**{{'Umbrella Tags': df['Umbrella Tags'].str.split(',')}}).explode('Umbrella Tags')
    
    # Strip whitespace from the tags
    df_exploded['Umbrella Tags'] = df_exploded['Umbrella Tags'].str.strip()
    
    # Group by country and tag to get the count
    result_data = df_exploded.groupby(['Country', 'Umbrella Tags']).size().reset_index(name='Count')
    
    # Convert the DataFrame to a list of dictionaries for JSON output
    result_data = result_data.rename(columns={{'Umbrella Tags': 'Umbrella tag name'}}).to_dict('records')
    
    return result_data
```
"""

user_prompt = "Question: {input}"
query_prompt_template = ChatPromptTemplate([
    ("system", system_message),
    ("user", user_prompt)
])

def get_gemini_python(question, df_info):
    """Generates Python code based on the user's question and DataFrame info."""
    prompt = query_prompt_template.invoke({
        "input": question,
        "df_info": df_info
    })
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=str(prompt)
    )
    code = response.text.strip()
    if code.startswith('```python'):
        code = code.split('```python')[1].strip()
    if code.endswith('```'):
        code = code.rsplit('```', 1)[0].strip()
    return code

def write_code(state, df_info):
    python_code = get_gemini_python(state["question"], df_info)
    state["code"] = python_code
    return state

def execute_code(state, df):
    try:
        local_vars = {'df': df, 'pd': pd}
        exec(state["code"], globals(), local_vars)
        result = local_vars['answer_query'](df)
        
        # If result is a DataFrame, convert datetime columns to string
        if isinstance(result, pd.DataFrame):
            for col in result.select_dtypes(include=['datetime', 'datetimetz']).columns:
                result[col] = result[col].astype(str)
            result = result.to_dict('records')
        # If result is a list of dicts, convert any datetime or numpy values to string/native
        elif isinstance(result, list):
            import numpy as np
            for row in result:
                for k, v in row.items():
                    if hasattr(v, 'isoformat'):
                        row[k] = str(v)
                    elif isinstance(v, (np.integer, np.floating)):
                        row[k] = v.item()

        state["result"] = result
        state["answer"] = json.dumps(state["result"], indent=2)
    except Exception as e:
        state["answer"] = f"Error executing Python code: {e}\n[Code: {state['code']}]"
    return state

# --- Load DataFrame once on startup ---
try:
    df = pd.read_excel(EXCEL_FILE_PATH)
    buffer = StringIO()
    df.info(buf=buffer)
    df_info = buffer.getvalue()
except Exception as e:
    df = None
    df_info = f"Error loading data: {e}"
    print(df_info)

# --- API Endpoint ---
from pydantic import BaseModel

class AskRequest(BaseModel):
    question: str

@app.post("/api/ask")
async def ask_question(request: AskRequest):
    if df is None:
        return JSONResponse(content={"error": "Failed to load data."}, status_code=500)

    question = request.question
    if not question:
        return JSONResponse(content={"error": "No question provided."}, status_code=400)

    state = State(question=question)
    state = write_code(state, df_info)
    state = execute_code(state, df)

    return JSONResponse(content=json.loads(state['answer']))

# To run: uvicorn backend:app --reload

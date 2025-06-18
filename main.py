# from fastapi import FastAPI, UploadFile, File
# from fastapi.responses import JSONResponse
# from pydantic import BaseModel
# from groq_chat import chat_with_groq
# from pdf_utils import process_pdf, search_pdf
# from search_utils import search_web, get_weather
# from dotenv import load_dotenv
# import pyttsx3
# import os
# import io
# from fastapi.middleware.cors import CORSMiddleware

# load_dotenv()

# app = FastAPI()

# # Add this before your routes
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Or specify your frontend URL(s)
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # 🔊 Initialize voice engine
# engine = pyttsx3.init()
# engine.setProperty('rate', 160)

# def speak_text(text):
#     try:
#         engine.say(text)
#         engine.runAndWait()
#     except Exception:
#         pass  # Optionally log or handle environments without audio

# # 🧠 Handle frontend text query
# class QueryRequest(BaseModel):
#     query: str

# @app.post("/chat")
# async def chat(req: QueryRequest):
#     try:
#         query = req.query

#         # 🌦️ Weather
#         if "weather" in query.lower():
#             response = get_weather()

#         # 🌐 Web search
#         elif query.lower().startswith("search the web for"):
#             response = search_web(query)

#         # 📄 PDF Q&A
#         elif query.lower().startswith("ask pdf:"):
#             pdf_question = query.replace("ask pdf:", "").strip()
#             context = search_pdf(pdf_question)
#             full_prompt = f"Use the following context to answer the question:\n\n{context}\n\nQuestion: {pdf_question}"
#             response = chat_with_groq(full_prompt)

#         # 🤖 AI Response
#         else:
#             response = chat_with_groq(query)

#         # 🔊 Speak response (optional)
#         speak_text(response)

#         return {"response": response}
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": str(e)})

# # 📥 Upload PDF to be processed and embedded
# @app.post("/upload_pdf")
# async def upload_pdf(file: UploadFile = File(...)):
#     contents = await file.read()

#     # Step 1: extract text
#     text = extract_text_from_pdf(BytesIO(contents))  # ← implement this

#     # Step 2: chunk + embed
#     chunks = split_into_chunks(text)
#     embeddings = embed_chunks(chunks)

#     # Step 3: store in Qdrant
#     store_in_qdrant(embeddings, chunks)

#     return {"status": "success"}

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import requests
import fitz  # PyMuPDF
import uuid
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import os

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Qdrant setup
qdrant = QdrantClient(":memory:")  # You can use "localhost" or "http://localhost:6333"
qdrant.recreate_collection(
    collection_name="pdf_chunks",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

# Constants
GROQ_API_KEY = "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"
GROQ_MODEL = "llama3-70b-8192"
SERP_API_KEY = "4124f8e11d6d4302d3824864e27793e62c5a03c97256b6e4ec4e366d262b4c8c"

# Utility: Extract text from PDF
def extract_text_from_pdf(file_bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# Utility: Split text into chunks
def chunk_text(text: str, max_tokens: int = 200) -> List[str]:
    sentences = text.split(". ")
    chunks, current_chunk = [], ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_tokens:
            current_chunk += sentence + ". "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

# Utility: Embed text
def embed_text(text_list: List[str]):
    return embedding_model.encode(text_list).tolist()

# Route: Upload PDF
@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    content = await file.read()
    text = extract_text_from_pdf(content)
    chunks = chunk_text(text)
    embeddings = embed_text(chunks)

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embeddings[i],
            payload={"text": chunks[i]}
        )
        for i in range(len(chunks))
    ]
    qdrant.upsert(collection_name="pdf_chunks", points=points)
    return {"status": "PDF processed", "chunks": len(chunks)}

# Route: Ask from PDF
class QueryInput(BaseModel):
    question: str

@app.post("/ask_pdf")
async def ask_pdf(data: QueryInput):
    question = data.question
    query_vec = embed_text([question])[0]

    hits = qdrant.search(
        collection_name="pdf_chunks",
        query_vector=query_vec,
        limit=3
    )

    context = " ".join([hit.payload["text"] for hit in hits])
    prompt = f"Answer the question using this context:\n{context}\n\nQ: {question}\nA:"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    }

    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body)
    data = response.json()

    if "choices" in data:
        return {"answer": data["choices"][0]["message"]["content"]}
    else:
        return {"error": data.get("message", "Unknown error")}

# Route: AI Chat (Generic)
@app.post("/chat")
async def chat(data: QueryInput):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "user", "content": data.question}
        ],
    }

    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body)
    data = response.json()

    if "choices" in data:
        return {"answer": data["choices"][0]["message"]["content"]}
    else:
        return {"error": data.get("message", "Unknown error")}

# Route: Weather
@app.get("/weather")
def get_weather(city: str):
    try:
        url = f"https://wttr.in/{city}?format=%C+%t+%w"
        headers = {"User-Agent": "curl/7.64.1"}
        res = requests.get(url, headers=headers)
        return {"weather": res.text}
    except Exception as e:
        return {"error": str(e)}

# Route: Web Search using SerpAPI
@app.get("/web_search")
def web_search(query: str):
    try:
        url = f"https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": SERP_API_KEY,
            "engine": "google",
        }
        res = requests.get(url, params=params).json()
        answer_box = res.get("answer_box", {})
        if "answer" in answer_box:
            return {"result": answer_box["answer"]}
        elif "snippet" in res.get("organic_results", [{}])[0]:
            return {"result": res["organic_results"][0]["snippet"]}
        else:
            return {"result": "No good answer found."}
    except Exception as e:
        return {"error": str(e)}

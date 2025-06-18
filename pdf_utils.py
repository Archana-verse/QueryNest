import fitz  # PyMuPDF
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import uuid
from typing import Any, Dict

# Initialize Qdrant and model only once
qdrant = QdrantClient(":memory:")  # For production, use a persistent path or host
model = SentenceTransformer("all-MiniLM-L6-v2")

qdrant.recreate_collection(
    collection_name="pdf_chunks",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
)

def process_pdf(file: Any) -> Dict[str, Any]:
    """
    Processes a PDF file, splits it into text chunks, embeds them, and uploads to Qdrant.
    Expects a file-like object (e.g., io.BytesIO).
    """
    contents = file.read()
    doc = fitz.open(stream=contents, filetype="pdf")
    chunks = []

    for page in doc:
        text = page.get_text().strip()
        if len(text) > 30:
            chunks.append(text)

    if not chunks:
        return {"message": "No valid text chunks found in PDF."}

    vectors = model.encode(chunks).tolist()

    qdrant.upload_points(
        collection_name="pdf_chunks",
        points=[
            PointStruct(id=str(uuid.uuid4()), vector=vec, payload={"text": chunk})
            for vec, chunk in zip(vectors, chunks)
        ]
    )

    return {"message": f"{len(chunks)} chunks embedded"}

def search_pdf(query: str) -> str:
    """
    Searches the embedded PDF chunks for the most relevant matches to the query.
    """
    if not query.strip():
        return ""

    query_vector = model.encode([query])[0].tolist()
    hits = qdrant.search(
        collection_name="pdf_chunks",
        query_vector=query_vector,
        limit=5
    )
    context = "\n".join(hit.payload["text"] for hit in hits if "text" in hit.payload)
    return context

def handle_pdf_query(question):
    embedded = embed_text(question)
    hits = qdrant_client.search(
        collection_name="pdf_chunks",
        query_vector=embedded,
        limit=3
    )

    context = "\n".join([hit.payload["text"] for hit in hits])
    prompt = f"Use the following PDF content to answer:\n{context}\n\nQuestion: {question}"

    return chat_with_groq(prompt)

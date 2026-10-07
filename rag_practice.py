from fastapi import HTTPException
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
from pgvector import Vector
import hashlib
from database_docker import get_connection


load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def chunk_document(docs, chunk_size, overlap):

    if chunk_size < 1:
        raise ValueError("Chunk size must be greater than 0.")

    if overlap < 0:
        raise ValueError("Overlap must be greater than or equal to 0.")

    if overlap >= chunk_size:
        raise ValueError("Overlap must be less than chunk size")

    chunk_list = []

    sentences = [s.strip() for s in docs.split(".") if s.strip()]

    chunk_data = []

    for sentence in sentences:
        draft = ". ".join(chunk_data + [sentence]) + "."

        if len(draft) > chunk_size and chunk_data:

            chunk_list.append(". ".join(chunk_data) + ".")

            chunk_data = chunk_data[-overlap:] if overlap > 0 else []

        chunk_data.append(sentence)

    if chunk_data:

        chunk_list.append(". ".join(chunk_data) + ".")

    return chunk_list

def delete_document(source, conn):

    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM rag.documents
        WHERE source = %s
        """,
        (source,)
    )

    deleted = cursor.rowcount

    return deleted


def reindex_document(source, document, chunk_size, overlap):

    if not document.strip():
        raise ValueError("Document must not be empty.")

    chunks = chunk_document(document, chunk_size, overlap)

    if not chunks:
        raise ValueError("Chunks cannot be empty.")

    document_hash = hashlib.sha256(document.encode()).hexdigest()

    with get_connection() as conn:

        db_hash = get_document_hash(source, conn)

    if db_hash == document_hash:
        print("Document unchanged. Skipping re-index.")
        return 0

    print("Reindexing document.")

    try:
        chunk_embedding = []

        for chunk in chunks:

            result = client.models.embed_content(
                model="gemini-embedding-2",
                contents=chunk,
                config=types.EmbedContentConfig(output_dimensionality=1536)
            )

            if not result.embeddings:
                raise HTTPException(status_code=404, detail="No embeddings found")

            [embedding_obj] = result.embeddings

            chunk_embedding.append((chunk, Vector(embedding_obj.values)))

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=502, detail="Embedding generation failed") from e

    with get_connection() as conn:

        deleted_chunks = delete_document(source, conn)

        cursor = conn.cursor()

        for chunk_id, (chunk, embedding) in enumerate(chunk_embedding, 1):

            cursor.execute(
                """
                INSERT INTO rag.documents
                    (content, embedding, source, chunk_id, page, content_hash)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (chunk, embedding, source, chunk_id, 1, document_hash)
            )

    print(f"Deleted {deleted_chunks} chunks.")

    print(f"Inserted {len(chunks)} new chunks.")

    return len(chunks)

def get_document_hash(source, conn):

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT content_hash FROM rag.documents
        WHERE source = %s
        """,
        (source,)
    )

    db_hash = cursor.fetchone()

    if not db_hash:
        return None

    return db_hash[0]
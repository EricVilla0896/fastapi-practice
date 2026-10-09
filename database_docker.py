import psycopg, os
from pgvector.psycopg import register_vector
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L6-v2")

def get_connection():
    conn = psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "api_practice"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )
    register_vector(conn)
    return conn

def search_documents(query_embedding, top_k=2, max_distance=0.3, source=None):
    with (get_connection() as conn):
        cursor = conn.cursor()
        source_filter = "AND source = %s" if source else ""
        values = [
                query_embedding, query_embedding,
                max_distance
            ]
        if source:
            values.append(source)

        values.extend([
            query_embedding,
            top_k
        ])
        cursor.execute(
            f"""
            SELECT content, embedding <=> %s AS distance, source, chunk_id, page
            FROM rag.documents
            WHERE embedding <=> %s <= %s {source_filter}
            ORDER BY embedding <=> %s
            LIMIT %s;
            """,
            values
        )
        results = cursor.fetchall()
    print(results)
    return results

def rerank_results(question, search_results, top_k=2):
    pairs = [
        (question, content)
        for content, distance, source, chunk_id, page in search_results
    ]

    scores = reranker.predict(pairs)

    ranked_results = sorted(
        zip(scores, search_results),
        key=lambda x: x[0],
        reverse=True
    )

    return [result for score, result in ranked_results[:top_k]]
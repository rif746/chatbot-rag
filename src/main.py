import sqlite3
from pathlib import Path

import pandas as pd
import sqlite_vec
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import ChatOllama, OllamaEmbeddings
from sqlite_vec import serialize_float32

# 1. Konfigurasi Path Proyek (relatif terhadap root proyek)
BASE_DIR = Path(__file__).resolve().parent.parent
FILES_DIR = BASE_DIR / "files"
CSV_PATH = FILES_DIR / "faq_data.csv"
DB_PATH = FILES_DIR / "faq_rag.db"

# 2. Konfigurasi Model
EMBEDDING_MODEL = "bge-m3"  # Dimensi vektor bge-m3 = 1024 (nomic-embed-text = 768)
EMBEDDING_DIM = 1024
LLM_MODEL = "llama3.2:1b"

embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
llm = ChatOllama(model=LLM_MODEL, temperature=0)


def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    # Pastikan direktori files/ ada sebelum membuka SQLite
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(str(db_path))
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    db.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS faq_vectors USING vec0(
            embedding float[{EMBEDDING_DIM}] distance_metric=cosine,
            +pertanyaan TEXT,
            +konten TEXT
        )
        """)
    return db


def ingest_csv_if_empty(db: sqlite3.Connection, csv_path: Path = CSV_PATH):
    count = db.execute("SELECT count(*) FROM faq_vectors").fetchone()[0]
    if count > 0:
        print(f"Database sudah berisi {count} FAQ. Melewati proses embedding.")
        return

    if not csv_path.exists():
        raise FileNotFoundError(f"File dataset tidak ditemukan di: {csv_path}")

    print(f"Memuat data FAQ dari {csv_path.name} dan membuat vektor ke SQLite...")
    df = pd.read_csv(csv_path).fillna("")
    df["konten"] = "Pertanyaan: " + df["Pertanyaan"] + "\nJawaban: " + df["Jawaban"]

    pertanyaan_list = df["Pertanyaan"].tolist()
    vectors = embeddings.embed_documents(pertanyaan_list)

    with db:
        for row, vec in zip(df.itertuples(), vectors):
            db.execute(
                """
                INSERT INTO faq_vectors (embedding, pertanyaan, konten)
                VALUES (?, ?, ?)
                """,
                (serialize_float32(vec), row.Pertanyaan, row.konten),
            )
    print(f"Berhasil menyimpan {len(df)} data FAQ ke {DB_PATH}.")


def retrieve_faq(db: sqlite3.Connection, query: str, k: int = 3) -> list[Document]:
    query_vec = serialize_float32(embeddings.embed_query(query))
    rows = db.execute(
        """
        SELECT pertanyaan, konten, distance
        FROM faq_vectors
        WHERE embedding MATCH ?
          AND k = ?
        ORDER BY distance
        """,
        (query_vec, k),
    ).fetchall()

    return [
        Document(
            page_content=konten,
            metadata={"Pertanyaan": pertanyaan, "distance": round(distance, 4)},
        )
        for pertanyaan, konten, distance in rows
    ]


# 3. Prompt & LCEL Chain
system_prompt = (
    "Anda adalah asisten layanan pelanggan yang ramah. "
    "Jawablah pertanyaan pengguna berdasarkan informasi pada Konteks berikut. "
    "Jika informasi benar-benar tidak ada di Konteks, katakan Anda tidak tahu.\n\n"
    "Konteks:\n{context}"
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)


def format_docs(docs: list[Document]) -> str:
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


def ask_faq(db: sqlite3.Connection, pertanyaan: str, k: int = 3) -> dict:
    docs = retrieve_faq(db, pertanyaan, k=k)
    chain = (
        {
            "context": lambda _: format_docs(docs),
            "input": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    answer = chain.invoke(pertanyaan)
    return {"answer": answer, "context": docs}


if __name__ == "__main__":
    conn = init_db()
    ingest_csv_if_empty(conn)

    print("\n=== Chatbot FAQ Lokal Siap (Ketik 'keluar' untuk berhenti) ===")
    while True:
        pertanyaan = input("\nAnda : ")
        if pertanyaan.strip().lower() in ["keluar", "exit", "quit"]:
            break
        if not pertanyaan.strip():
            continue

        hasil = ask_faq(conn, pertanyaan, k=3)

        # --- BAGIAN DEBUG UNTUK PENELITIAN ---
        print("\n[DEBUG - Dokumen yang ditemukan oleh Retriever]:")
        for i, doc in enumerate(hasil["context"], 1):
            dist = doc.metadata.get("distance", "N/A")
            print(f"  {i}. [dist={dist}] {doc.metadata.get('Pertanyaan', 'N/A')}")
        print("-" * 50)

        print(f"Bot  : {hasil['answer']}")

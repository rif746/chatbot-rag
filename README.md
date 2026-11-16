# Chatbot RAG FAQ Lokal dengan `sqlite-vec` & Ollama

Proyek ini adalah implementasi sistem **Retrieval-Augmented Generation (RAG)** lokal untuk menjawab pertanyaan layanan pelanggan berdasarkan dataset FAQ (`CSV`). Sistem ini berjalan 100% secara lokal tanpa bergantung pada API berbayar, menggunakan **Ollama** untuk *embedding* serta *Large Language Model (LLM)*, dan **`sqlite-vec`** sebagai *vector store* persisten berbasis satu file SQLite.

---

## Fitur Utama

* **100% Lokal & Privat:** Menggunakan Ollama (`bge-m3` untuk embedding Bahasa Indonesia dan `llama3.2:1b` untuk generasi jawaban).
* **Penyimpanan Vektor Persisten (`sqlite-vec`):** Vektor disimpan di disk (`files/faq_rag.db`) sehingga proses *embedding* hanya berjalan sekali saat inisialisasi pertama.
* **Asymmetric Question-Only Indexing:** Hanya kolom `Pertanyaan` yang diubah menjadi vektor untuk meningkatkan presisi pencarian semantik, sementara pasangan `Pertanyaan + Jawaban` disimpan sebagai kolom *auxiliary* (`+konten`).
* **Environment Reproducible:** Dikonfigurasi secara deklaratif menggunakan **Nix Flakes** dan **`uv`**.
* **Telemetri Debug:** Menampilkan skor *cosine distance* dari top-$k$ dokumen yang diambil oleh *retriever* untuk kebutuhan evaluasi dan riset.

---

## Struktur Proyek

```text
.
├── files/
│   ├── faq_data.csv      # Dataset sumber FAQ (kolom: Pertanyaan, Jawaban)
│   └── faq_rag.db        # Database SQLite + sqlite-vec (otomatis dibuat saat run pertama)
├── src/
│   └── main.py           # Kode utama ingestion, retrieval, dan antarmuka CLI chatbot
├── flake.nix             # Konfigurasi environment Nix
├── flake.lock            # Lockfile dependensi Nix
├── requirements.txt      # Daftar pustaka Python
└── README.md             # Dokumentasi proyek
```

---

## Prasyarat

1. **Nix Package Manager** (dengan fitur `flakes` aktif) — *atau Python 3.12+ & `uv` jika menjalankan tanpa Nix.*
2. **Ollama** terinstal dan berjalan di latar belakang (`ollama serve`).

Unduh model Ollama yang digunakan sebelum menjalankan aplikasi:

```bash
ollama pull bge-m3
ollama pull llama3.2:1b
```

---

## Cara Instalasi & Menjalankan

### 1. Masuk ke Environment Pengembangan (Nix + `uv`)

Dari direktori utama proyek, jalankan:

```bash
nix develop
```

Perintah ini akan menyiapkan Python 3.12, SQLite CLI, dan virtual environment `.venv`. Selanjutnya, instal dependensi Python:

```bash
uv pip install -r requirements.txt
```

### 2. Siapkan Dataset FAQ

Pastikan file `files/faq_data.csv` tersedia dengan format minimal dua kolom berikut:

```csv
Pertanyaan,Jawaban
"Bagaimana cara reset kata sandi?","Klik menu Lupa Kata Sandi di halaman login dan ikuti instruksi via email."
"Berapa lama proses pengiriman pesanan?","Pengiriman reguler membutuhkan waktu 2–4 hari kerja."
```

### 3. Jalankan Chatbot

Jalankan program dari direktori root proyek:

```bash
python src/main.py
```

* **Saat pertama kali dijalankan:** Sistem akan membaca `files/faq_data.csv`, membuat vektor embedding menggunakan `bge-m3`, dan menyimpannya ke `files/faq_rag.db`.
* **Saat dijalankan berikutnya:** Sistem akan langsung memuat database yang sudah ada dalam hitungan milidetik.

---

## Pembaruan Dataset & Konfigurasi Model

* **Memperbarui Data CSV:** Jika Anda menambah atau mengubah isi `files/faq_data.csv`, hapus file database lama agar sistem melakukan *re-indexing*:
  ```bash
  rm files/faq_rag.db
  python src/main.py
  ```
* **Mengganti Model Embedding:** Nilai `EMBEDDING_DIM` di `src/main.py` harus sesuai dengan dimensi output model yang dipilih:
  * `bge-m3` $\rightarrow$ `EMBEDDING_DIM = 1024`
  * `nomic-embed-text` $\rightarrow$ `EMBEDDING_DIM = 768`

---

## Contoh Output Debug

```text
Anda : berapa hari paket saya sampai?

[DEBUG - Dokumen yang ditemukan oleh Retriever]:
  1. [dist=0.2841] Berapa lama proses pengiriman pesanan?
  2. [dist=0.5112] Bagaimana cara melacak nomor resi pengiriman?
  3. [dist=0.6034] Apakah tersedia pengiriman instan di hari yang sama?
--------------------------------------------------
Bot  : Pengiriman reguler membutuhkan waktu 2–4 hari kerja.
```
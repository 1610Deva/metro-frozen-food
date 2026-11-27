# METRO AI Service (bagian AI Engineer)

Tiga fitur dalam satu service FastAPI:

| Fitur | Endpoint | Cara kerja |
|---|---|---|
| Cabang terdekat sesuai stok | `POST /v1/branches/recommend`, `GET /v1/products/search`, `GET /v1/areas` | Urut jarak (OSRM, cadangan haversine) + cek stok. Satu pesanan satu cabang |
| AI Smart Shopping Assistant | `POST /v1/assistant/chat` | Router intent berbasis aturan, penyusun budget, resep, RAG (BM25 + Gemini opsional), handoff WhatsApp |
| Rute pengantaran admin | `POST /v1/routes/optimize` | Held-Karp (eksak sampai 12 titik), di atas itu nearest neighbour + 2-opt |

Pengelompokan batch dan estimasi ongkir adalah bagian Data Science. Tarif di `data/delivery_rules.json` hanya placeholder.

## Menjalankan
```bash
cd ai-service
python -m venv .venv
# Windows: .venv\Scripts\activate    Mac/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # Windows: copy .env.example .env
uvicorn app.main:app --reload --port 8000
```
- Uji lewat browser: http://localhost:8000/docs
- Chat di terminal: `python chat_cli.py`
- Tes: `python -m pytest`
- Evaluasi: `python -m eval.evaluate`

## Katalog
344 produk dari postingan Instagram toko; stok, cabang, dan ongkir masih dummy. Lihat `docs/DATA.md`.
Mengubah data: edit `data/sumber/katalog_instagram.csv`, jalankan `python tools/build_catalog.py`, lalu `python -m pytest`.

## Alur assistant
1. Pesan dinormalisasi (singkatan chat).
2. Aturan eskalasi dicek lebih dulu (partai/bisnis, nego, komplain, halal/alergi, minta owner) lalu diberi link WhatsApp. LLM tidak memutuskan bagian ini.
3. Budget: kode mencari kombinasi produk yang tidak melebihi budget dan stok. Resep diambil dari `data/recipes.json`.
4. Harga, stok, dan resep dijawab dari data terstruktur.
5. Pertanyaan lain: retrieval BM25 lalu Gemini menjawab hanya dari konteks. Jawaban ditolak bila memuat nominal Rp yang tidak ada di konteks. Penjaga ini hanya memeriksa nominal, bukan semua jenis klaim.
6. Tanpa jawaban: diarahkan ke owner (topik toko) atau ditolak sopan (di luar topik).

Tanpa `GEMINI_API_KEY`, semua fitur tetap berjalan dengan jawaban template dan FAQ.

## Privasi dan batasan
- Tier gratis Gemini: isi prompt dapat dipakai Google untuk pengembangan produknya. Email dan nomor telepon disamarkan, tetapi nama atau alamat dalam teks bebas tidak. Beri tahu pengguna di widget chat. LLM hanya dipakai pada langkah 5.
- Server publik OSRM adalah demo tanpa jaminan layanan dan menerima koordinat yang dikirim. Untuk produksi, host sendiri atau pakai penyedia lain. Profilnya mobil, bukan motor.
- Lalu lintas dan jendela waktu per pesanan tidak dioptimalkan. ETA hanya diberi peringatan bila melewati slot.
- Panggilan ke OSRM dan Gemini baru diuji dengan respons tiruan. Uji dengan layanan asli sebelum demo.

## Evaluasi
- `eval/hasil_baseline.txt`: percobaan pertama, aturan 0,636 vs TF-IDF+LogReg 0,782 (akurasi).
- `eval/hasil_setelah_perbaikan.txt`: setelah aturan diperbaiki memakai kesalahan tersebut. **Bukan skor uji.**
- Semua data latih dan uji adalah sintetis, dibuat dengan bantuan AI oleh penulis yang sama.
- Untuk skor yang sah: minta anggota tim lain menulis pertanyaan baru tanpa melihat aturan, ganti `eval/intent_test.csv`, jalankan sekali.
- Model yang dipakai aplikasi saat ini adalah A (aturan). Tentukan pilihan final setelah uji dengan data baru.

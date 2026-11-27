# Kontrak integrasi (untuk Full-stack dan DS)

React -> Express (`/api/ai/*`) -> AI service (`:8000`). Browser tidak memanggil AI service langsung.

## Express
Salin `contoh-express/aiRoutes.js`. Env server: `AI_SERVICE_URL`, `INTERNAL_API_KEY` (sama dengan AI service).

## Lokasi di React (gratis, tanpa API key Google)
```js
navigator.geolocation.getCurrentPosition(
  ({ coords }) => setLocation({ latitude: coords.latitude, longitude: coords.longitude }),
  () => setShowManualArea(true), // pakai GET /api/ai/areas
  { enableHighAccuracy: true, timeout: 10000 },
);
```
Geolocation hanya berjalan di HTTPS atau localhost.

## Contoh request
`POST /api/ai/branches/recommend`
```json
{"latitude": -7.29, "longitude": 112.79, "method": "direct_delivery",
 "items": [{"product_id": "<uuid>", "quantity": 2}]}
```
`status`: `NEAREST_AVAILABLE`, `ALTERNATIVE_BRANCH` (tampilkan pop-up bila `requires_confirmation`), `OUT_OF_RANGE`, `UNAVAILABLE`.
Backend tetap wajib memvalidasi stok dan menghitung ongkir sendiri saat checkout.

`GET /api/ai/products/search?q=nugget&branch_id=<uuid>` -> `availability`: `AVAILABLE_HERE`, `OTHER_BRANCH_ONLY`, `AVAILABLE`, `OUT_OF_STOCK`.

`POST /api/ai/chat`
```json
{"message": "budget 50 ribu buat 3 hari", "context": {}, "latitude": -7.29, "longitude": 112.79}
```
Response: `answer` (tampilkan dengan `white-space: pre-line`, sebagai teks, bukan HTML), `intent`, `products`, `recipes`, `plan`, `handoff.url` (tombol WhatsApp, bisa null), `suggestions`.
Simpan `context` dari response dan kirim lagi di pesan berikutnya.

`POST /api/ai/routes/optimize` (admin)
```json
{"branch_id": "<uuid>", "slot_start": "15:00", "slot_end": "17:00", "return_to_branch": false,
 "stops": [{"order_code": "MFF-00125", "latitude": -7.329, "longitude": 112.779}]}
```
Maksimal 25 titik. Kirim pesanan dari satu cabang (biasanya isi satu batch dari DS, atau pesanan hari itu yang dipilih admin).
`google_maps_links` dipecah maksimal 3 waypoint per link.

## Data asli: endpoint snapshot (dibuat FS)
Set `BACKEND_SNAPSHOT_URL`. Express membalas, setelah mengecek header `x-internal-key` (tolak bila key kosong):
```json
{"categories": [], "products": [], "branches": [], "branch_stock": []}
```
Nama kolom mengikuti PDM. Jangan sertakan data pelanggan. Bila endpoint gagal, AI service membalas 503, tidak diam-diam memakai dummy.
ID data asli berbeda dari ID dummy; frontend harus memakai ID dari sumber yang sama.

## Kolom yang belum ada di PDM (diskusikan dengan pemilik database)
`products`: `sku`, `weight_gram`, `servings_per_pack`, `is_lauk`, `low_stock_threshold`, `aliases` (opsional).
Tambahan: `recipe_type`, `brand`, `carton_qty`, `price_posted_at` (opsional).
**Tanpa `is_lauk` dan `servings_per_pack`, penyusun budget tidak merekomendasikan apa pun** (supaya saus tidak dianggap lauk). Tanpa `recipe_type`, resep tidak muncul; tanpa `aliases`, pencarian jenis di chat jauh lebih lemah. Ambang stok default 10.
Seeder database bisa mengambil nilai-nilai ini dari `ai-service/data/products.json`.
Katalog berisi 344 produk, jadi halaman katalog dan hasil pencarian perlu paginasi.
Desain menampilkan SKU dan ambang minimum per produk, jadi dashboard stok juga membutuhkannya.

# Data

**Katalog produk berasal dari postingan Instagram toko. Stok, cabang, ongkir, dan resep masih dummy atau draf.** Jangan sajikan yang dummy sebagai data operasional UMKM.

## Katalog dari Instagram @ridwanfrozenfood.sby
Sumber: 348 screenshot postingan yang dikumpulkan tim. Nama, harga, ukuran, isi karton, dan tanggal dibaca dari caption.
Harga dicek silang dengan OCR: 347 cocok; no.287 (teks terpotong) hanya dibaca manual. Nama produk hanya dibaca manual.

- `sumber/katalog_instagram.csv`: satu baris per screenshot, termasuk nama file dan catatan. **Ubah data di sini**, lalu jalankan `python tools/build_catalog.py`. Menjalankannya juga membuat ulang stok dummy.
- 4 postingan duplikat digabung, hasilnya 344 produk. Dipakai postingan terbaru (Shifudo flower twister: 23.000, harga lama 27.000).
- Tahun postingan: 113 dari 2026, 120 dari 2025, 109 dari 2024, 2 tanpa tanggal. Setiap postingan menulis harga bisa berubah, dan belum diketahui apakah produk lama masih dijual. Tanggal disimpan di `price_posted_at`.
- 7 produk ditandai SATUAN PERLU DICEK (CSV no.198 dan 327-332). Tetap tampil dengan peringatan, tidak dipakai penyusun budget.
- Mungkin produk yang sama atau varian, belum digabung: no.4 dan 55, 154 dan 155, 104 dan 346, 245 dan 340.
- Caption hanya memuat alamat Jl. Dukuh Setro 3A No. 1A. Dua nomor muncul: 08133344630 (bio, CSV no.1-7, 18, dan 117-120) dan 082320500100 (sebagian besar postingan lain). Dibaca dengan OCR.
- Banyak postingan menyebut potongan harga grosir pada jumlah tertentu, tanpa angka potongannya. Pertanyaan grosir diteruskan ke owner.

### Turunan dan asumsi AE (bukan dari Instagram)
| Kolom | Cara mengisi |
|---|---|
| category_id | Kolom `kategori` di CSV: Nugget, Sosis, Bakso, Seafood, Saus & Bumbu, Dimsum, Daging & Ayam, Kentang & Sayur, Camilan, Pelengkap, Lainnya. Diisi awal dengan aturan kata kunci; boleh diubah tangan |
| servings_per_pack | **Perkiraan**: 100 g = 1 porsi; tanpa berat memakai jumlah biji |
| is_lauk | Kategori protein dengan porsi yang bisa diperkirakan (171 produk). Saus, sayur, camilan, pelengkap, ceker, usus, kulit tidak dipakai |
| recipe_type, brand, aliases | Dari kata kunci pada nama |
| low_stock_threshold | 10 |

Produk lauk tanpa ukuran dan jumlah biji tidak ikut penyusun budget. Isi `ukuran` di CSV bila sudah diketahui.

## Dari bio Instagram
Diambil dari cuplikan hasil pencarian pada 28 Nov 2026, jadi bisa saja sudah berubah.
- WhatsApp 0813-3344-630 (di `.env.example`)
- Ecer dan grosir; pengiriman dalam kota, luar kota, luar pulau (`faq.md`)
- Buka setiap hari 07.00-21.00, Sabtu tutup 20.00 (`faq.md`). Belum jelas berlaku untuk semua cabang.

Belum didapat: stok, berat sebagian produk, tarif ongkir, pembayaran, status halal, daftar cabang.

| File | Asal | Perlu diganti dengan |
|---|---|---|
| products.json, categories.json | Instagram + turunan di atas | Katalog yang dikonfirmasi owner |
| branches.json | **Dummy**: 5 nama cabang dari Figma; koordinat perkiraan kecamatan | Alamat dan pin Google Maps asli |
| branch_stock.json | **Dummy**: acak tetap per produk dan cabang (sekitar 12% kosong, 13% menipis) | Stok asli / dari database |
| areas.json | Perkiraan titik kecamatan | Cukup untuk pilihan lokasi manual |
| delivery_rules.json | **Dummy**: 25.000 dan 10.000 dari Figma; Rp2.000/km dan radius 25 km asumsi | Aturan owner + formula DS |
| recipes.json | Draf buatan AI, per jenis produk. Belum dicoba | Dicoba/disetujui tim atau owner |
| faq.md | Dari flowchart, use case, desain, bio IG | Jawaban resmi owner |
| orders_sample.json | Nama fiktif, titik acak | Pesanan dari database |

Katalog ini berbeda dari produk, harga, dan angka stok di Figma. Beri tahu tim desain dan FS.

## Pertanyaan untuk owner
1. Metro Frozen Food dan Ridwan Frozen Food (akun Instagram di laporan) hubungannya apa? Nama mana yang dipakai di website?
2. Daftar cabang aktif: alamat, link Google Maps, jam buka.
3. Produk: mana yang masih dijual dan harga terbarunya, ukuran yang belum tertulis, 7 produk yang satuannya belum jelas, foto dan izin memakainya.
4. Stok per cabang (boleh contoh), dan siapa yang memperbaruinya.
5. Ongkir: tarif, radius, minimal order, jadwal batch, boleh tidak kirim dari cabang yang lebih jauh.
6. Pembayaran yang diterima.
7. Nomor WhatsApp untuk pelanggan: 08133344630 atau 082320500100?
8. Mulai berapa pack dianggap grosir?
9. Status halal/izin edar per produk (sebelum ada data resmi, asisten meneruskan ke owner).

# Alur GitHub (kamu sudah fork repo kelompok)

`origin` = fork kamu. `upstream` = repo kelompok.

## Sekali di awal
```bash
git clone https://github.com/USERNAME-KAMU/NAMA-REPO.git
cd NAMA-REPO
git remote add upstream https://github.com/PEMILIK-REPO/NAMA-REPO.git
git remote -v
git fetch upstream
git switch -c feat/ai-service upstream/main
```
Salin isi zip: folder `ai-service/` ditaruh di root repo (menimpa folder `ai-service` yang kosong).

## Commit dan push
```bash
cd ai-service
python -m pytest
cd ..
git status            # pastikan TIDAK ada .env, .venv, atau PDF laporan
git add ai-service
git commit -m "feat(ai): add branch recommendation, shopping assistant, route optimizer"
git push -u origin feat/ai-service
```
Boleh dipecah jadi beberapa commit (data, cabang, asisten, rute) agar mudah direview.

## Pull Request
Di GitHub buka fork kamu, klik "Compare & pull request".
Base: repo kelompok, branch `main` (atau `dev` bila tim memakainya; tanya leader). Compare: `feat/ai-service`.
Minta satu anggota FS mereview.

## Kalau repo kelompok sudah berubah
```bash
git fetch upstream
git merge upstream/main
git push
```

## Pembagian kerja yang disarankan (sepakati dengan tim)
| Pekerjaan | PIC |
|---|---|
| ai-service: 3 fitur, katalog dari Instagram, stok dummy, tes, evaluasi, dokumentasi API | AE |
| Route Express, widget chat, UI cabang dan rute, autentikasi admin, database, endpoint snapshot | FS |
| Pengelompokan batch, estimasi ongkir, rekomendasi produk, analitik | DS |
| Uji integrasi dan deploy | AE + FS (+ DS) |

"""Router intent berbasis aturan. Eskalasi ke owner sengaja deterministik, bukan keputusan LLM."""
import re
from . import text as T

INTENTS = ["eskalasi_owner", "rekomendasi_budget", "resep", "info_produk", "info_layanan", "sapaan", "lainnya"]

ESCALATION = {
    "pembelian_partai": r"\b(grosir|partai besar|jumlah (?:yang )?(?:banyak|besar)|borong|reseller|dropship\w*|agen|distributor|supplier|suplai|pasok\w*)\b|\bpesan(?:an)? (?:dalam )?(?:jumlah )?banyak\b",
    "kebutuhan_bisnis": r"\b(bisnis|usaha|jualan|dijual (?:lagi|kembali)|warung|kafe|cafe|katering|catering|restoran|kantin|acara|hajatan|arisan|event)\b",
    "negosiasi_kerjasama": r"\b(nego|negosiasi|diskon|potongan harga|harga khusus|kerja ?sama|kemitraan|mitra|franchise|sponsor\w*|invoice|faktur|tempo|kontrak)\b",
    "komplain": r"\b(komplain|keluhan|kecewa|rusak|basi|bau|berjamur|jamuran|busuk|dikembalikan|dibatalkan|belum (?:juga )?(?:dikirim|nyampe)|kadaluarsa|kedaluwarsa|expired|refund|retur|uang (?:saya )?kembali|salah kirim|belum (?:sampai|datang|diterima)|tidak sesuai|batalkan pesanan|cancel)\b",
    "keamanan_pangan": r"\b(halal(?:nya)?|bpom|pirt|alergi|alergen|pengawet|komposisi|kandungan|gizi|kalori|hamil|bayi|keracunan|sakit perut)\b",
    "minta_manusia": r"\b(owner(?:nya)?|pemilik(?:nya)?|bicara (?:dengan )?(?:admin|orang|cs)|hubungi (?:admin|penjual)|chat admin|nomor (?:wa|whatsapp|admin))\b",
}
SERVICE = r"\b(cara (?:pesan|order|beli|bayar|simpan|menyimpan)|pengiriman|dikirim|kirim|antar|ongkir|ongkos|gabungan|batch|ambil (?:di )?(?:toko|sendiri|cabang)|pickup|pick up|bayar|pembayaran|transfer|tunai|cod|qris|cabang|lokasi|alamat toko|nota|id pesanan|checkout|freezer|disimpan|menyimpan|simpan|jam (?:buka|tutup|berapa)|buka|tutup)\b"
PRODUCT_Q = r"\b(harga|berapa|stok|ready|tersedia|ada (?:tidak|gak)?|masih ada|jual|katalog|produk|menu apa|termurah|paling murah|termahal|berat|isi)\b"
RECIPE = r"\b(resep|cara masak|cara memasak|masak apa|dimasak|olah|diolah|olahan|mau masak|cara (?:goreng|kukus)|menu masakan|dibikin apa|enaknya)\b"
BUDGET = r"\b(budget|bujet|modal|duit|uang|anggaran|dana)\b"
GREETING = r"^(halo|hallo|hai|hi|hello|pagi|siang|sore|malam|selamat (?:pagi|siang|sore|malam)|permisi|assalamualaikum|assalamu alaikum|p|terima ?kasih|makasih|thanks|ok|oke)(?: (?:kak|min|admin|ya|gan))*[ !.?,]*$"


def classify(message, products=(), bulk_pack_threshold=20, bulk_budget_threshold=1_000_000):
    """-> (intent, alasan|None)."""
    t = T.normalize(message)
    for reason, pattern in ESCALATION.items():
        if re.search(pattern, t):
            return "eskalasi_owner", reason
    qty, budget = T.parse_pack_qty(t), T.parse_budget(t)
    if (qty and qty >= bulk_pack_threshold) or (budget and budget >= bulk_budget_threshold):
        return "eskalasi_owner", "pembelian_partai"
    if re.search(GREETING, t):
        return "sapaan", None
    mentioned = T.find_products(t, products)
    shopping = re.search(r"\b(beli|makan|rekomendasi|rekomen|saran|cocok|dapat apa|belanja|stok untuk)\b", t)
    if re.search(BUDGET, t) or (budget and shopping):
        return "rekomendasi_budget", None
    if re.search(RECIPE, t):
        return "resep", None
    if re.search(r"\b(rekomendasi|rekomen)\b", t) or (shopping and T.parse_days(t)):
        return "rekomendasi_budget", None
    stem = re.sub(r"(?<=\w{4})nya\b", "", t)  # "pengirimannya" -> "pengiriman"
    if budget and not mentioned and not re.search(SERVICE, stem):
        return "rekomendasi_budget", None
    if re.search(SERVICE, stem) and not (mentioned and re.search(r"\b(harga|stok|ready)\b", t)):
        return "info_layanan", None
    if mentioned or re.search(PRODUCT_Q, t):
        return "info_produk", None
    return "lainnya", None

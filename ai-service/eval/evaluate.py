"""Jalankan dari folder ai-service: python -m eval.evaluate"""
import csv
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import make_pipeline

from app import repository
from app.assistant.intent import classify
from app.assistant.retriever import BM25, faq_docs
from app.assistant.text import normalize
from app.config import settings

HERE = Path(__file__).parent


def read(name):
    return list(csv.DictReader(open(HERE / name, encoding="utf-8")))


def tfidf():
    return TfidfVectorizer(preprocessor=normalize, analyzer="char_wb", ngram_range=(3, 5))


train, test = read("intent_train.csv"), read("intent_test.csv")
assert not {r["text"] for r in train} & {r["text"] for r in test}, "data latih dan uji tumpang tindih"
y = [r["intent"] for r in test]
products = repository.load_catalog().products
model = make_pipeline(tfidf(), LogisticRegression(C=10, max_iter=2000, class_weight="balanced"))
model.fit([r["text"] for r in train], [r["intent"] for r in train])
preds = {"A. Aturan (regex)": [classify(r["text"], products)[0] for r in test],
         "B. TF-IDF char + LogReg": list(model.predict([r["text"] for r in test]))}

print(f"INTENT (latih={len(train)}, uji={len(test)}, sintetis)")
print(f"{'konfigurasi':28}{'accuracy':>10}{'macro F1':>10}{'recall eskalasi':>17}")
for name, p in preds.items():
    esc = recall_score(y, p, labels=["eskalasi_owner"], average="macro", zero_division=0)
    print(f"{name:28}{accuracy_score(y, p):10.3f}{f1_score(y, p, average='macro', zero_division=0):10.3f}{esc:17.3f}")
print("\nSalah klasifikasi konfigurasi A:")
for r, p in zip(test, preds["A. Aturan (regex)"]):
    if p != r["intent"]:
        print(f"  '{r['text']}': {r['intent']} -> {p}")

docs, queries = faq_docs(settings.data_dir / "faq.md"), read("retrieval_test.csv")
vec = tfidf()
matrix = vec.fit_transform([d["title"] + " " + d["text"] for d in docs])
bm25 = BM25(docs)


def by_tfidf(q):
    sims = cosine_similarity(vec.transform([q]), matrix)[0]
    return [docs[i]["id"] for i in sims.argsort()[::-1]]


print(f"\nRETRIEVAL FAQ (dokumen={len(docs)}, query={len(queries)})")
print(f"{'konfigurasi':28}{'hit@1':>10}{'hit@3':>10}")
for name, search in (("A. BM25 + sinonim", lambda q: [d["id"] for d in bm25.search(q, 3)]), ("B. TF-IDF char cosine", by_tfidf)):
    ranked = [(r["doc"], search(r["query"])) for r in queries]
    print(f"{name:28}" + "".join(f"{sum(d in got[:k] for d, got in ranked) / len(ranked):10.3f}" for k in (1, 3)))

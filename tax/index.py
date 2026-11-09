# Publication 17 in Chroma, two ways:
# - sections: one node per section, long ones split under it, each part headed by its heading path
#   ("Chapter 3. Dependents > Qualifying Child > Age Test")
# - chunks: the baseline, fixed-size chunks over the publication's running text, with no headings,
#   that know which sections they overlap only for scoring
# The same nodes and embeddings also go to Pinecone serverless (free Starter plan), behind the same
# retriever, so comparing the two compares only the store. Embeddings come from a local model, on
# CPU, through a cache on disk, so rebuilding an index or loading Pinecone doesn't embed again.
#
# Usage: uv run python -m tax.index [--rebuild] [--pinecone]

import functools
import hashlib
import os
import sys
from pathlib import Path

import chromadb
import numpy as np
from dotenv import load_dotenv
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode, Document, MetadataMode, NodeWithScore, QueryBundle, TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.vector_stores.pinecone import PineconeVectorStore

from tax import pub17

load_dotenv(".env")

EMBED_MODEL = os.environ.get("TAX_EMBED_MODEL", "BAAI/bge-base-en-v1.5")
SLUG = EMBED_MODEL.split("/")[-1]
STORAGE = Path("storage")
CHUNK_SIZE = 512  # tokens; bge truncates past its own 512
CHUNK_OVERLAP = 64
CORPORA = ("sections", "chunks")


def section_nodes(sections: dict[str, pub17.Section]) -> list[TextNode]:
    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    nodes = []
    for s in sections.values():
        head = f"[{s.id}] {s.heading}"
        parts = splitter.split_text_metadata_aware(s.text, head) if s.text else [""]
        for i, part in enumerate(parts):
            nodes.append(
                TextNode(
                    id_=f"s{s.id}-{i}",
                    text=f"{head}\n{part}",
                    # Chroma takes only scalars, so the cross-references are a string
                    metadata={"section": s.id, "chapter": s.chapter, "see": " ".join(s.see), "part": i, "parts": len(parts)},
                    excluded_embed_metadata_keys=["section", "chapter", "see", "part", "parts"],
                    excluded_llm_metadata_keys=["section", "chapter", "see", "part", "parts"],
                )
            )
    return nodes


def chunk_nodes(sections: dict[str, pub17.Section]) -> list[TextNode]:
    text, starts = "", []
    for s in sections.values():
        starts.append((len(text), s.id))
        text += s.text + "\n"
    chunks = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP).get_nodes_from_documents([Document(text=text)])
    nodes = []
    for i, chunk in enumerate(chunks):
        start, end = chunk.start_char_idx, chunk.end_char_idx
        covered = [id for at, id in starts if at <= start][-1:] + [id for at, id in starts if start < at < end]
        nodes.append(
            TextNode(
                id_=f"c{i:04d}",
                text=chunk.text,
                metadata={"sections": " ".join(covered)},
                excluded_embed_metadata_keys=["sections"],
                excluded_llm_metadata_keys=["sections"],
            )
        )
    return nodes


def nodes(corpus: str) -> list[TextNode]:
    return (section_nodes if corpus == "sections" else chunk_nodes)(pub17.load())


@functools.cache
def embed_model() -> BaseEmbedding:
    # bge is trained with this instruction on queries and none on passages
    return HuggingFaceEmbedding(model_name=EMBED_MODEL, query_instruction="Represent this sentence for searching relevant passages: ", embed_batch_size=32, max_length=512)


class EmbeddingCache:
    """Embeddings by kind (document or query) and text, in one .npz file per model"""

    def __init__(self, path: Path = STORAGE / f"embeddings-{SLUG}.npz"):
        self.path = path
        self.vectors: dict[str, np.ndarray] = {}
        if path.exists():
            data = np.load(path)
            self.vectors = dict(zip(data["keys"].tolist(), data["vectors"]))

    @staticmethod
    def key(kind: str, text: str) -> str:
        return hashlib.sha1(f"{kind}\n{text}".encode()).hexdigest()

    def embed(self, texts: list[str], kind: str = "document") -> list[list[float]]:
        missing = list(dict.fromkeys(t for t in texts if self.key(kind, t) not in self.vectors))
        if missing:
            model = embed_model()
            vectors = model.get_text_embedding_batch(missing, show_progress=len(missing) > 100) if kind == "document" else [model.get_query_embedding(t) for t in missing]
            self.vectors.update((self.key(kind, t), np.asarray(v, dtype=np.float32)) for t, v in zip(missing, vectors))
            self.path.parent.mkdir(parents=True, exist_ok=True)
            np.savez(self.path, keys=np.array(list(self.vectors)), vectors=np.stack(list(self.vectors.values())))
        return [self.vectors[self.key(kind, t)].tolist() for t in texts]


def embed_nodes(items: list[BaseNode], cache: EmbeddingCache) -> None:
    texts = [n.get_content(metadata_mode=MetadataMode.EMBED) for n in items]
    for node, vector in zip(items, cache.embed(texts)):
        node.embedding = vector


def chroma(corpus: str, rebuild: bool = False) -> VectorStoreIndex:
    """The corpus's index in Chroma on disk, built the first time"""
    client = chromadb.PersistentClient(path=str(STORAGE / "chroma"))
    items = nodes(corpus)
    name = f"{corpus}-{SLUG}"
    collection = client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})
    if collection.count() == len(items) and not rebuild:
        return VectorStoreIndex.from_vector_store(ChromaVectorStore(chroma_collection=collection), embed_model=embed_model())
    embed_nodes(items, EmbeddingCache())
    client.delete_collection(name)
    store = ChromaVectorStore(chroma_collection=client.create_collection(name, metadata={"hnsw:space": "cosine"}))
    return VectorStoreIndex(items, storage_context=StorageContext.from_defaults(vector_store=store), embed_model=embed_model())


def pinecone(corpus: str, rebuild: bool = False) -> VectorStoreIndex:
    """The corpus's index in Pinecone serverless, upserted the first time from the cached embeddings"""
    from pinecone import Pinecone, ServerlessSpec

    client = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    name = f"irs-{corpus}-{SLUG}".lower().replace(".", "-")
    items = nodes(corpus)
    if rebuild and client.has_index(name):
        client.delete_index(name)
    if not client.has_index(name):
        # The Starter plan serves only AWS us-east-1
        client.create_index(name, spec=ServerlessSpec(cloud="aws", region="us-east-1"), dimension=len(EmbeddingCache().embed(["dimension"], kind="query")[0]), metric="cosine")
    store = PineconeVectorStore(pinecone_index=client.Index(name))
    if client.Index(name).describe_index_stats().total_vector_count == len(items):
        return VectorStoreIndex.from_vector_store(store, embed_model=embed_model())
    embed_nodes(items, EmbeddingCache())
    return VectorStoreIndex(items, storage_context=StorageContext.from_defaults(vector_store=store), embed_model=embed_model())


STORES = {"chroma": chroma, "pinecone": pinecone}


def sections(node: NodeWithScore) -> list[str]:
    """The sections a node holds: its own, or for a chunk, every one it overlaps"""
    meta = node.node.metadata
    return [meta["section"]] if "section" in meta else meta["sections"].split()


class Search:
    """Top k nodes for a query, embedding the query through the cache"""

    def __init__(self, corpus: str = "sections", k: int = 5, store: str = "chroma"):
        self.corpus, self.cache = corpus, EmbeddingCache()
        self.retriever = STORES[store](corpus).as_retriever(similarity_top_k=k)

    def __call__(self, query: str) -> list[NodeWithScore]:
        [vector] = self.cache.embed([query], kind="query")
        return self.retriever.retrieve(QueryBundle(query_str=query, embedding=vector))


if __name__ == "__main__":
    store = "pinecone" if "--pinecone" in sys.argv else "chroma"
    for corpus in CORPORA:
        STORES[store](corpus, rebuild="--rebuild" in sys.argv)
        print(f"{store} {corpus}: built")

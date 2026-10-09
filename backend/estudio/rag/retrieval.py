"""Recuperación híbrida: pgvector (coseno) + BM25 (tsvector) fusionadas con RRF,
más expansión por grafo de conceptos. Filtros por tema y por documento.
Anti-alucinación: el generador solo ve los fragmentos devueltos aquí."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from estudio.config import get_settings
from estudio.rag.embeddings import embedir_query, vector_a_pg
from estudio.rag.grafo import entidades_en_texto

K_RRF = 60  # constante estándar de Reciprocal Rank Fusion


@dataclass
class Fragmento:
    id: int
    texto: str
    pagina: str
    archivo: str
    tipo: str
    titulo: str
    score: float = 0.0
    origen: str = "híbrido"  # híbrido | grafo


def _rrf(rankings: list[list[int]], extra: dict[int, float] | None = None) -> dict[int, float]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for pos, cid in enumerate(ranking):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (K_RRF + pos + 1)
    if extra:
        for cid, s in extra.items():
            scores[cid] = scores.get(cid, 0.0) + s
    return scores


async def recuperar(
    db: AsyncSession,
    pregunta: str,
    k: int | None = None,
    document_id: str | None = None,
    tema_id: str | None = None,
) -> list[Fragmento]:
    """Top-k fragmentos híbridos (vector + BM25 + grafo).

    tema_id/documeto_id None o vacío ⇒ sin filtro (todos los temas).
    """
    s = get_settings()
    k = k or s.retrieval_k
    emb = embedir_query(pregunta)
    vec = vector_a_pg(emb)

    filtro = ""
    if tema_id:
        filtro += " AND dd.tema_id = :tema"
    if document_id:
        filtro += " AND c.document_id = :doc"
    params_v: dict = {"vec": vec, "kv": s.retrieval_k_vector}
    params_b: dict = {"q": pregunta, "kb": s.retrieval_k_bm25}
    for p in (params_v, params_b):
        if tema_id:
            p["tema"] = tema_id
        if document_id:
            p["doc"] = document_id

    res_v = await db.execute(
        text(
            "SELECT c.id FROM chunks c JOIN documents dd ON dd.id = c.document_id "
            f"WHERE TRUE{filtro} ORDER BY c.embedding <=> CAST(:vec AS vector) LIMIT :kv"
        ),
        params_v,
    )
    res_b = await db.execute(
        text(
            "SELECT c.id FROM chunks c JOIN documents dd ON dd.id = c.document_id "
            "WHERE c.tsv @@ plainto_tsquery('simple', :q)"
            f"{filtro} ORDER BY ts_rank(c.tsv, plainto_tsquery('simple', :q)) DESC LIMIT :kb"
        ),
        params_b,
    )
    ids_vec = [r[0] for r in res_v.fetchall()]
    ids_bm = [r[0] for r in res_b.fetchall()]
    if not ids_vec and not ids_bm:
        return []

    # ---- expansión por grafo: nodos nombrados en la pregunta → chunks hermanos
    extra: dict[int, float] = {}
    conceptos = entidades_en_texto(pregunta)
    if conceptos:
        res_n = await db.execute(text("SELECT nombre FROM nodos"))
        existentes = {r[0] for r in res_n.fetchall()}
        matcheados = [c for c in conceptos if c in existentes]
        if matcheados:
            res_g = await db.execute(
                text(
                    "SELECT DISTINCT ar.chunk_id FROM aristas ar "
                    "JOIN nodos n ON n.id = ar.nodo_a OR n.id = ar.nodo_b "
                    "JOIN chunks c2 ON c2.id = ar.chunk_id "
                    "JOIN documents dd ON dd.id = c2.document_id "
                    "WHERE n.nombre = ANY(:nombres) AND ar.chunk_id IS NOT NULL"
                    + (" AND dd.tema_id = :tema" if tema_id else "")
                ),
                {"nombres": matcheados, **({"tema": tema_id} if tema_id else {})},
            )
            for (cid,) in res_g.fetchall():
                if cid not in ids_vec and cid not in ids_bm:
                    extra[cid] = 0.5 / K_RRF  # boost suave, no desplaza al híbrido

    scores = _rrf([ids_vec, ids_bm], extra)
    top = sorted(scores.items(), key=lambda x: -x[1])[:k]
    if not top:
        return []
    ids_finales = [cid for cid, _ in top]

    res = await db.execute(
        text(
            "SELECT c.id, c.texto, c.pagina, d.ruta, d.tipo, d.titulo "
            "FROM chunks c JOIN documents d ON d.id = c.document_id "
            "WHERE c.id = ANY(:ids)"
        ),
        {"ids": ids_finales},
    )
    por_id = {r[0]: r for r in res.fetchall()}
    fragmentos: list[Fragmento] = []
    for cid, score in top:
        r = por_id.get(cid)
        if r is None:
            continue
        fragmentos.append(
            Fragmento(
                id=r[0], texto=r[1], pagina=r[2] or "", archivo=r[3], tipo=r[4],
                titulo=r[5] or r[3], score=round(score, 5),
                origen="grafo" if cid in extra else "híbrido",
            )
        )
    return fragmentos


async def chunk_menos_cubierto(db: AsyncSession, n: int = 1, tema_id: str | None = None) -> list[int]:
    """Chunks menos usados por tips (cobertura por tema); aleatorio en el mínimo."""
    filtro_tema = "JOIN documents dd ON dd.id = c.document_id AND dd.tema_id = :tema" if tema_id else ""
    res = await db.execute(
        text(
            f"SELECT c.id, COUNT(tc.tip_id) AS usos FROM chunks c {filtro_tema} "
            "LEFT JOIN tips_chunks tc ON tc.chunk_id = c.id "
            "GROUP BY c.id ORDER BY usos ASC, RANDOM() LIMIT :n"
        ),
        {"n": n, **({"tema": tema_id} if tema_id else {})},
    )
    return [r[0] for r in res.fetchall()]


async def similitud_maxima(
    db: AsyncSession, vec: list[float], tabla: str = "tips", tema_id: str | None = None
) -> tuple[float, str | None]:
    """(máx similitud coseno, id) contra una tabla con embedding; dedupe por tema."""
    v = vector_a_pg(vec)
    filtro = " WHERE tema_id = :tema" if tema_id else ""
    res = await db.execute(
        text(f"SELECT id, 1 - (embedding <=> CAST(:v AS vector)) AS sim FROM {tabla}{filtro} "
             "ORDER BY embedding <=> CAST(:v AS vector) LIMIT 1"),
        {"v": v, **({"tema": tema_id} if tema_id else {})},
    )
    fila = res.fetchone()
    if fila is None:
        return 0.0, None
    return float(fila[1]), fila[0]

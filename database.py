"""Camada de persistência do portal Derby Synthetica no MongoDB.

Conecta ao MongoDB (local ou remoto via MONGO_URI) na base `derby-synthetica`
e coleção `colecao`, onde os dados de categorias e conteúdos residem.

Preserva exatamente as assinaturas e o contrato esperado pelo `main.py`,
incluindo a derivação dos campos de categoria e todos os métodos do CRUD.
"""

import json
import os
from pathlib import Path
from typing import List, Optional
from pymongo import MongoClient

ARQUIVO_SEED = Path(__file__).parent / "dados_iniciais.json"

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB", "derby-synthetica")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION", "colecao")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
db = client[MONGO_DB_NAME]
collection = db[MONGO_COLLECTION_NAME]


def _obter_documento() -> dict:
    """Busca o documento principal com categorias e conteúdos."""
    doc = collection.find_one({}, {"_id": 0})
    return doc if doc else {"categorias": [], "conteudos": []}


def _obter_proximo_id() -> int:
    """Calcula o próximo id a partir do maior id de conteúdo existente."""
    doc = _obter_documento()
    conteudos = doc.get("conteudos", [])
    return max((c["id"] for c in conteudos), default=0) + 1


def carregar_dados() -> None:
    """Inicializa os dados caso a coleção do MongoDB esteja vazia.

    Chamada no startup do FastAPI (lifespan em main.py). Se o MongoDB
    já tiver dados (como o seed importado no Compass), preserva os dados existentes.
    """
    try:
        if collection.count_documents({}) == 0:
            dados = json.loads(ARQUIVO_SEED.read_text(encoding="utf-8"))
            collection.insert_one(dados)
            print("[MongoDB] Dados iniciais inseridos com sucesso!")
        else:
            print("[MongoDB] Conectado com sucesso! Colecao já possui dados.")
    except Exception as e:
        print(f"[MongoDB] Aviso ao conectar/carregar dados: {e}")


# --------------------------------------------------------------- categorias


def listar_categorias(trilha: Optional[str] = None) -> List[dict]:
    """Lista as categorias, opcionalmente filtrando por trilha."""
    doc = _obter_documento()
    categorias = doc.get("categorias", [])
    if trilha is None:
        return list(categorias)
    return [c for c in categorias if c.get("trilha") == trilha]


def buscar_categoria(categoria_id: int) -> Optional[dict]:
    """Devolve a categoria pelo id, ou None se ela não existir."""
    doc = _obter_documento()
    return next((c for c in doc.get("categorias", []) if c.get("id") == categoria_id), None)


# ---------------------------------------------------------------- conteúdos


def _com_derivados(conteudo: dict) -> dict:
    """Acrescenta `categoria_slug`, `categoria_nome` e `trilha` ao conteúdo."""
    categoria = buscar_categoria(conteudo["categoria_id"])
    if not categoria:
        return {
            **conteudo,
            "categoria_slug": "",
            "categoria_nome": "",
            "trilha": "",
        }
    return {
        **conteudo,
        "categoria_slug": categoria["slug"],
        "categoria_nome": categoria["nome"],
        "trilha": categoria["trilha"],
    }


def listar_conteudos(
    trilha: Optional[str] = None,
    categoria_id: Optional[int] = None,
    busca: Optional[str] = None,
) -> List[dict]:
    """Lista os conteúdos com campos derivados e filtros acumulativos."""
    doc = _obter_documento()
    conteudos = doc.get("conteudos", [])
    resultado = [_com_derivados(c) for c in conteudos]

    if trilha is not None:
        resultado = [c for c in resultado if c.get("trilha") == trilha]

    if categoria_id is not None:
        resultado = [c for c in resultado if c.get("categoria_id") == categoria_id]

    if busca:
        termo = busca.strip().lower()
        resultado = [
            c
            for c in resultado
            if termo in c.get("titulo", "").lower()
            or termo in c.get("subtitulo", "").lower()
            or termo in c.get("resumo", "").lower()
        ]

    return resultado


def buscar_conteudo(conteudo_id: int) -> Optional[dict]:
    """Devolve o conteúdo pelo id, com derivados, ou None."""
    doc = _obter_documento()
    bruto = next((c for c in doc.get("conteudos", []) if c.get("id") == conteudo_id), None)
    return _com_derivados(bruto) if bruto is not None else None


def buscar_conteudo_por_slug(slug: str) -> Optional[dict]:
    """Devolve o conteúdo pelo slug, com derivados, ou None."""
    doc = _obter_documento()
    bruto = next((c for c in doc.get("conteudos", []) if c.get("slug") == slug), None)
    return _com_derivados(bruto) if bruto is not None else None


def slug_em_uso(slug: str, ignorar_id: Optional[int] = None) -> bool:
    """Diz se o slug já pertence a algum conteúdo."""
    doc = _obter_documento()
    return any(
        c.get("slug") == slug and c.get("id") != ignorar_id
        for c in doc.get("conteudos", [])
    )


def criar_conteudo(dados: dict) -> dict:
    """Insere um conteúdo novo no MongoDB e devolve com id e derivados."""
    novo_id = _obter_proximo_id()
    novo = {"id": novo_id, **dados}
    collection.update_one({}, {"$push": {"conteudos": novo}})
    return _com_derivados(novo)


def atualizar_conteudo(conteudo_id: int, dados: dict) -> Optional[dict]:
    """Substitui um conteúdo por inteiro no MongoDB, preservando o id."""
    conteudo_atualizado = {"id": conteudo_id, **dados}
    resultado = collection.update_one(
        {"conteudos.id": conteudo_id},
        {"$set": {"conteudos.$": conteudo_atualizado}},
    )
    if resultado.matched_count == 0:
        return None
    return _com_derivados(conteudo_atualizado)


def remover_conteudo(conteudo_id: int) -> bool:
    """Remove o conteúdo pelo id no MongoDB."""
    resultado = collection.update_one(
        {},
        {"$pull": {"conteudos": {"id": conteudo_id}}},
    )
    return resultado.modified_count > 0

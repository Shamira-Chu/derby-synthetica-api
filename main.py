"""API do portal Derby Synthetica.

FastAPI com dados em memória, servindo o CRUD de conteúdos editoriais e a
leitura das categorias. O contrato (rotas, campos e códigos de erro) está
descrito no CLAUDE.md do repositório do portal.

Para rodar:
    uvicorn main:app --reload
Documentação interativa em http://127.0.0.1:8000/docs
"""

import os
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

import database
from models import Categoria, Conteudo, ConteudoAtualizar, ConteudoCriar, Erro, Trilha


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Carrega o seed no startup, para o portal nunca responder vazio."""
    database.carregar_dados()
    yield


app = FastAPI(
    title="Derby Synthetica API",
    description=(
        "Backend do portal Derby Synthetica. Dados em memória, recarregados "
        "do seed a cada startup. A trilha pertence à categoria e é derivada "
        "na leitura de cada conteúdo, nunca armazenada."
    ),
    version="1.0.0",
    lifespan=ciclo_de_vida,
)

# CORS. Em desenvolvimento o front do Next roda em localhost:3000; no deploy
# ele ganha uma URL pública, que chega por FRONTEND_URL. Sem isso o navegador
# bloqueia as respostas e a tela fica vazia sem erro visível no servidor.
origens_liberadas = ["http://localhost:3000", "http://127.0.0.1:3000"]

_url_do_front = os.getenv("FRONTEND_URL")
if _url_do_front:
    origens_liberadas.append(_url_do_front.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origens_liberadas,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _exigir_categoria(categoria_id: int) -> None:
    """Recusa com 422 uma categoria que não existe.

    Vale para POST e PUT: sem essa checagem seria possível gravar um conteúdo
    órfão, e aí a derivação da trilha na leitura quebraria.
    """
    if database.buscar_categoria(categoria_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"A categoria {categoria_id} não existe.",
        )


def _exigir_slug_livre(slug: str, ignorar_id: Optional[int] = None) -> None:
    """Recusa com 409 um slug que já pertence a outro conteúdo.

    `ignorar_id` é passado no PUT para o conteúdo poder manter o próprio slug.
    """
    if database.slug_em_uso(slug, ignorar_id=ignorar_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"O slug '{slug}' já está em uso por outro conteúdo.",
        )


@app.get("/", tags=["Saúde"])
def raiz():
    """Ponto de checagem simples, usado pelo health check do deploy."""
    return {"servico": "Derby Synthetica API", "documentacao": "/docs"}


# ---------------------------------------------------------------- categorias


@app.get("/categorias", response_model=List[Categoria], tags=["Categorias"])
def listar_categorias(
    trilha: Optional[Trilha] = Query(None, description="Filtra pela trilha"),
):
    """Lista as categorias do portal, opcionalmente filtrando por trilha."""
    return database.listar_categorias(trilha.value if trilha else None)


# ----------------------------------------------------------------- conteúdos


@app.get("/conteudos", response_model=List[Conteudo], tags=["Conteúdos"])
def listar_conteudos(
    trilha: Optional[Trilha] = Query(None, description="Filtra pela trilha"),
    categoria_id: Optional[int] = Query(None, description="Filtra pela categoria"),
    busca: Optional[str] = Query(None, description="Procura em título, subtítulo e resumo"),
):
    """Lista os conteúdos. Os filtros são opcionais e se acumulam."""
    return database.listar_conteudos(
        trilha=trilha.value if trilha else None,
        categoria_id=categoria_id,
        busca=busca,
    )


# Esta rota precisa ser declarada ANTES de /conteudos/{conteudo_id}. O FastAPI
# resolve caminhos na ordem em que foram registrados, então, se a de id viesse
# primeiro, ela casaria com /conteudos/slug e tentaria converter "slug" em int.
@app.get(
    "/conteudos/slug/{slug}",
    response_model=Conteudo,
    responses={404: {"model": Erro}},
    tags=["Conteúdos"],
)
def buscar_conteudo_por_slug(slug: str):
    """Detalha um conteúdo pelo slug, que é como o portal monta a URL."""
    conteudo = database.buscar_conteudo_por_slug(slug)
    if conteudo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum conteúdo com o slug '{slug}'.",
        )
    return conteudo


@app.get(
    "/conteudos/{conteudo_id}",
    response_model=Conteudo,
    responses={404: {"model": Erro}},
    tags=["Conteúdos"],
)
def buscar_conteudo(conteudo_id: int):
    """Detalha um conteúdo pelo id."""
    conteudo = database.buscar_conteudo(conteudo_id)
    if conteudo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum conteúdo com o id {conteudo_id}.",
        )
    return conteudo


@app.post(
    "/conteudos",
    response_model=Conteudo,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": Erro}, 422: {"model": Erro}},
    tags=["Conteúdos"],
)
def criar_conteudo(payload: ConteudoCriar):
    """Cadastra um conteúdo novo.

    Recusa com 422 categoria inexistente e com 409 slug já em uso.
    """
    _exigir_categoria(payload.categoria_id)
    _exigir_slug_livre(payload.slug)
    return database.criar_conteudo(payload.model_dump())


@app.put(
    "/conteudos/{conteudo_id}",
    response_model=Conteudo,
    responses={404: {"model": Erro}, 409: {"model": Erro}, 422: {"model": Erro}},
    tags=["Conteúdos"],
)
def atualizar_conteudo(conteudo_id: int, payload: ConteudoAtualizar):
    """Atualiza um conteúdo por inteiro, preservando o id.

    O slug do próprio conteúdo é ignorado na checagem de duplicidade, senão
    reenviar o registro sem mexer no slug devolveria 409.
    """
    if database.buscar_conteudo(conteudo_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum conteúdo com o id {conteudo_id}.",
        )

    _exigir_categoria(payload.categoria_id)
    _exigir_slug_livre(payload.slug, ignorar_id=conteudo_id)

    return database.atualizar_conteudo(conteudo_id, payload.model_dump())


@app.delete(
    "/conteudos/{conteudo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": Erro}},
    tags=["Conteúdos"],
)
def remover_conteudo(conteudo_id: int):
    """Remove um conteúdo pelo id. Responde 204 sem corpo quando dá certo."""
    if not database.remover_conteudo(conteudo_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum conteúdo com o id {conteudo_id}.",
        )

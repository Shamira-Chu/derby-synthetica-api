"""Base em memória do portal Derby Synthetica.

Os dados vivem em duas listas de dicionários deste módulo, carregadas do
`dados_iniciais.json` no startup da aplicação. Como o seed recarrega a cada
boot, o portal nunca aparece vazio.

Nenhuma rota toca nas listas diretamente: tudo passa pelas funções daqui.
A intenção é que trocar por um banco real signifique reescrever só este
arquivo, sem encostar no main.py.
"""

import json
from pathlib import Path
from typing import List, Optional

ARQUIVO_SEED = Path(__file__).parent / "dados_iniciais.json"

# Estado do módulo. O underscore marca que ninguém de fora deve ler direto.
_categorias: List[dict] = []
_conteudos: List[dict] = []
_proximo_id: int = 1


def carregar_dados() -> None:
    """Recarrega as listas a partir do JSON de seed.

    Chamada no startup. Recalcula o próximo id a partir do maior id existente
    para que um POST logo após o boot não colida com o seed.
    """
    global _categorias, _conteudos, _proximo_id

    dados = json.loads(ARQUIVO_SEED.read_text(encoding="utf-8"))
    _categorias = list(dados["categorias"])
    _conteudos = list(dados["conteudos"])
    _proximo_id = max((c["id"] for c in _conteudos), default=0) + 1


# --------------------------------------------------------------- categorias


def listar_categorias(trilha: Optional[str] = None) -> List[dict]:
    """Lista as categorias, opcionalmente filtrando por trilha."""
    if trilha is None:
        return list(_categorias)
    return [c for c in _categorias if c["trilha"] == trilha]


def buscar_categoria(categoria_id: int) -> Optional[dict]:
    """Devolve a categoria pelo id, ou None se ela não existir."""
    return next((c for c in _categorias if c["id"] == categoria_id), None)


# ---------------------------------------------------------------- conteúdos


def _com_derivados(conteudo: dict) -> dict:
    """Acrescenta `categoria_slug`, `categoria_nome` e `trilha` ao conteúdo.

    Os três saem da categoria e nunca são gravados no conteúdo. Derivar na
    leitura é exatamente o que impede a trilha de um conteúdo divergir da
    trilha da sua categoria depois que alguém edita uma das duas.

    A categoria sempre existe aqui porque criar e atualizar recusam com 422
    uma `categoria_id` inexistente.
    """
    categoria = buscar_categoria(conteudo["categoria_id"])
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
    """Lista os conteúdos já com os campos derivados.

    Os três filtros são opcionais e se acumulam. A busca é case insensitive e
    varre título, subtítulo e resumo, que é o que a tela de acervo pesquisa.
    """
    resultado = [_com_derivados(c) for c in _conteudos]

    if trilha is not None:
        resultado = [c for c in resultado if c["trilha"] == trilha]

    if categoria_id is not None:
        resultado = [c for c in resultado if c["categoria_id"] == categoria_id]

    if busca:
        termo = busca.strip().lower()
        resultado = [
            c
            for c in resultado
            if termo in c["titulo"].lower()
            or termo in c["subtitulo"].lower()
            or termo in c["resumo"].lower()
        ]

    return resultado


def buscar_conteudo(conteudo_id: int) -> Optional[dict]:
    """Devolve o conteúdo pelo id, com derivados, ou None."""
    bruto = next((c for c in _conteudos if c["id"] == conteudo_id), None)
    return _com_derivados(bruto) if bruto is not None else None


def buscar_conteudo_por_slug(slug: str) -> Optional[dict]:
    """Devolve o conteúdo pelo slug, com derivados, ou None."""
    bruto = next((c for c in _conteudos if c["slug"] == slug), None)
    return _com_derivados(bruto) if bruto is not None else None


def slug_em_uso(slug: str, ignorar_id: Optional[int] = None) -> bool:
    """Diz se o slug já pertence a algum conteúdo.

    `ignorar_id` existe por causa do PUT: na edição o conteúdo costuma manter
    o próprio slug, e ele não pode contar como duplicata de si mesmo.
    """
    return any(c["slug"] == slug and c["id"] != ignorar_id for c in _conteudos)


def criar_conteudo(dados: dict) -> dict:
    """Insere um conteúdo novo e devolve ele já com id e derivados."""
    global _proximo_id

    novo = {"id": _proximo_id, **dados}
    _proximo_id += 1
    _conteudos.append(novo)
    return _com_derivados(novo)


def atualizar_conteudo(conteudo_id: int, dados: dict) -> Optional[dict]:
    """Substitui um conteúdo por inteiro, preservando o id.

    Devolve None se o id não existir, para a rota poder responder 404.
    """
    for indice, atual in enumerate(_conteudos):
        if atual["id"] == conteudo_id:
            _conteudos[indice] = {"id": conteudo_id, **dados}
            return _com_derivados(_conteudos[indice])
    return None


def remover_conteudo(conteudo_id: int) -> bool:
    """Remove o conteúdo pelo id. False quando não havia nada para remover."""
    for indice, atual in enumerate(_conteudos):
        if atual["id"] == conteudo_id:
            del _conteudos[indice]
            return True
    return False

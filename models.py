"""Schemas Pydantic do portal Derby Synthetica.

Os nomes de campo estão em português porque seguem o MER da disciplina de
Database Application. A tradução para os nomes em inglês que o front usa
acontece na camada de services do Next, de propósito: assim a API não fica
amarrada ao vocabulário da interface.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Trilha(str, Enum):
    """As duas trilhas do portal.

    Herda de str para que o valor serialize como texto no JSON e possa ser
    comparado direto com o que vem do query string.
    """

    VELOCIDADE = "velocidade"
    EXPRESSAO = "expressao"


class Secao(BaseModel):
    """Bloco de texto de um ensaio.

    Só `texto` é obrigatório: título, citação e destaque são recursos
    editoriais que nem toda seção usa.
    """

    titulo: Optional[str] = None
    texto: str
    citacao: Optional[str] = None
    destaque: Optional[str] = None


class Categoria(BaseModel):
    """Categoria editorial.

    A trilha pertence a ela, não ao conteúdo. Os conteúdos herdam a trilha
    na leitura, o que impede que as duas divirjam depois de uma edição.
    """

    id: int
    slug: str
    nome: str
    descricao_curta: str
    trilha: Trilha


class ConteudoBase(BaseModel):
    """Campos que o cliente envia ao cadastrar ou editar um conteúdo.

    Não inclui `id`, que é do servidor, nem `categoria_slug`, `categoria_nome`
    e `trilha`, que são derivados da categoria na hora da leitura.
    """

    slug: str = Field(..., min_length=1, description="Identificador da URL, único")
    titulo: str = Field(..., min_length=1)
    subtitulo: str
    categoria_id: int = Field(..., description="Chave estrangeira para Categoria")
    resumo: str
    tempo_leitura: str = Field(..., examples=["4 min"])
    data: str = Field(..., examples=["10 Outubro 2025"])
    autor: str
    autor_cargo: str
    destaque: bool = False
    selo_editorial: Optional[str] = None
    arquetipo_grafico: str = Field(..., examples=["wheel"])
    aprendizados: List[str] = []
    secoes: List[Secao] = []
    slugs_relacionados: List[str] = []


class ConteudoCriar(ConteudoBase):
    """Corpo do POST /conteudos."""


class ConteudoAtualizar(ConteudoBase):
    """Corpo do PUT /conteudos/{id}.

    Tem os mesmos campos do POST porque o contrato define atualização por
    inteiro, não parcial: quem edita manda o conteúdo completo de volta.
    """


class Conteudo(ConteudoBase):
    """Conteúdo como a API devolve, já com id e os três campos derivados."""

    id: int
    categoria_slug: str
    categoria_nome: str
    trilha: Trilha


class Erro(BaseModel):
    """Formato das respostas de erro, para aparecer documentado no /docs."""

    detail: str

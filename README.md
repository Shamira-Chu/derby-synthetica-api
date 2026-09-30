# Derby Synthetica API

Backend do portal **Derby Synthetica**, entrega de Framework Application do
challenge FIAP "O Mundo de Synthetica" (2026).

## Integrantes

| Nome | RM |
|---|---|
| Denise Shamira Chuquimia | 563714 |
| Tandara Sartore Perez de Azevedo | 566455 |
| Álvaro Milantonio | 561652 |
| Leonardo Henrique | 564231 |

API REST em **FastAPI** com os quatro verbos do CRUD sobre conteúdos
editoriais, mais a leitura das categorias. Os dados ficam em memória e são
recarregados do `dados_iniciais.json` a cada startup, então o portal nunca
aparece vazio.

O frontend que consome esta API é um projeto Next separado, em outro
repositório: https://github.com/leonardohb7/syntheticafrontend. A entrega são os
dois juntos. Quem escreve no acervo é o painel editorial do portal, em
`/editorial`, que é onde o POST, o PUT e o DELETE daqui são exercitados pela
interface.

## Publicados

| Serviço | URL |
|---|---|
| API (Render) | https://syntheticabackend.onrender.com |
| Documentação interativa | https://syntheticabackend.onrender.com/docs |
| Portal (Vercel) | https://frontend-three-fawn-51.vercel.app |

O `/docs` é o caminho mais curto para demonstrar os quatro verbos: ele monta o
formulário de cada rota sozinho, sem precisar de cliente HTTP.

## Como rodar

Requer Python 3.10 ou superior (testado no 3.14).

```bash
# 1. ambiente virtual


# Windows
.venv\Scripts\activate
# Linux ou macOS
source .venv/bin/activate

# 2. dependências
pip install -r requirements.txt

# 3. servidor
uvicorn main:app --reload
```

A API sobe em **http://127.0.0.1:8000** e a documentação interativa fica em
**http://127.0.0.1:8000/docs**, que é por onde dá para testar tudo sem escrever
uma linha de código.

## Endpoints

Base local: `http://127.0.0.1:8000`

| Método | Rota | Função |
|---|---|---|
| GET | `/categorias` | Lista as categorias. Filtro: `trilha` |
| GET | `/conteudos` | Lista conteúdos. Filtros: `trilha`, `categoria_id`, `busca` |
| GET | `/conteudos/{id}` | Detalha pelo id |
| GET | `/conteudos/slug/{slug}` | Detalha pelo slug, que é como o portal monta a URL |
| POST | `/conteudos` | Cadastra. Devolve 201 |
| PUT | `/conteudos/{id}` | Atualiza por inteiro |
| DELETE | `/conteudos/{id}` | Remove. Devolve 204 |
| GET | `/` | Checagem de saúde, usada pelo deploy |

### Códigos de erro

| Código | Quando acontece |
|---|---|
| 404 | Id ou slug que não existe |
| 409 | Slug já usado por outro conteúdo |
| 422 | Payload inválido ou `categoria_id` inexistente |

### Exemplos

```bash
# listar tudo
curl http://127.0.0.1:8000/conteudos

# filtrar por trilha
curl "http://127.0.0.1:8000/conteudos?trilha=velocidade"

# buscar por texto
curl "http://127.0.0.1:8000/conteudos?busca=jammer"

# detalhar pelo slug
curl http://127.0.0.1:8000/conteudos/slug/a-roda-que-sente-o-piso

# cadastrar, editar e remover pelo /docs, que monta o formulário sozinho
```

## Modelo de dados

Os nomes de campo estão em português porque seguem o MER da disciplina de
Database Application. O frontend traduz para inglês na própria camada de
services, de propósito, para a API não ficar amarrada ao vocabulário da
interface.

```
Categoria                      Conteudo
  id               int           id                  int
  slug             str           slug                str  único
  nome             str           titulo              str
  descricao_curta  str           subtitulo           str
  trilha           enum          categoria_id        int  FK
                                 resumo              str
                                 tempo_leitura       str
                                 data                str
                                 autor               str
                                 autor_cargo         str
                                 destaque            bool
                                 selo_editorial      str  opcional
                                 arquetipo_grafico   str
                                 aprendizados        list[str]
                                 secoes              list[Secao]
                                 slugs_relacionados  list[str]
```

`Secao`: `texto` obrigatório, mais `titulo`, `citacao` e `destaque` opcionais.

`trilha`: `velocidade` ou `expressao`.

### A trilha pertence à categoria

`categoria_slug`, `categoria_nome` e `trilha` **são derivados na leitura e
nunca gravados no conteúdo**. Uma função privada do `database.py` acrescenta
os três a partir da categoria antes de devolver a resposta.

Essa é a razão de existir da regra: se a trilha fosse copiada para dentro do
conteúdo, editar a categoria depois faria as duas divergirem em silêncio.
Derivando na leitura, trocar a `categoria_id` de um conteúdo faz a trilha dele
acompanhar sozinha, e mandar `trilha` no corpo de um POST não tem efeito
nenhum, porque o schema de entrada simplesmente não tem esse campo.

## Arquitetura

| Arquivo | Responsabilidade |
|---|---|
| `main.py` | Aplicação FastAPI, CORS e rotas |
| `models.py` | Schemas Pydantic e validação |
| `database.py` | Base em memória e todas as regras de acesso |
| `dados_iniciais.json` | Seed: 6 categorias e 9 conteúdos |

Nenhuma rota lê as listas de dados diretamente: tudo passa pelas funções do
`database.py`. A intenção é que trocar a memória por um banco real signifique
reescrever só esse arquivo, sem encostar no `main.py`.

## CORS

O middleware libera, por padrão, `http://localhost:3000` e
`http://127.0.0.1:3000`, que é onde o Next roda em desenvolvimento.

No deploy, defina a variável de ambiente **`FRONTEND_URL`** com a URL pública
do frontend. Ela é acrescentada à lista de origens no startup. No serviço atual
o valor é `https://frontend-three-fawn-51.vercel.app`:

```bash
FRONTEND_URL=https://frontend-three-fawn-51.vercel.app uvicorn main:app
```

Sem isso o navegador bloqueia as respostas e a tela fica vazia sem nenhum erro
aparecer no log do servidor, que é a falha mais comum nesse tipo de entrega.

O `main.py` aplica `.rstrip("/")` no valor, então barra sobrando no fim não
quebra a comparação. O que precisa bater exatamente é o resto: protocolo,
subdomínio e domínio. Origem no CORS não aceita curinga parcial, então uma URL
de preview da Vercel, que tem outro subdomínio, não é liberada por esta
variável.

Para conferir sem abrir o portal:

```bash
curl -s -o /dev/null -D - \
  -H "Origin: https://frontend-three-fawn-51.vercel.app" \
  https://syntheticabackend.onrender.com/categorias | grep -i access-control
```

A resposta precisa trazer `access-control-allow-origin` com a URL do portal.

## Deploy no Render

O serviço está no ar em https://syntheticabackend.onrender.com, criado como Web
Service pelo painel, com os valores abaixo. O `render.yaml` na raiz descreve o
mesmo serviço e serve tanto para recriar por Blueprint quanto como referência do
que preencher à mão:

| Campo | Valor usado |
|---|---|
| Runtime | Python |
| Plano | Free |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/` |
| Variável de ambiente | `FRONTEND_URL` = `https://frontend-three-fawn-51.vercel.app` |

### O start command é a parte que costuma quebrar

`--host 0.0.0.0` não é detalhe. Sem ele o uvicorn escuta apenas em `127.0.0.1`,
de dentro do contêiner, e o roteador do Render nunca alcança a aplicação: o
deploy trava em "no open ports detected" enquanto o log mostra o servidor
subindo normalmente, que é o que torna essa falha difícil de ler.

A porta também não pode ser fixada em 8000. Ela vem de `$PORT`, que o Render
define a cada boot.

### Versão do Python

O arquivo `.python-version` fixa o **3.14**, que é onde as dependências foram
testadas. Se o build reclamar que a versão não está disponível na plataforma,
esse arquivo é o único lugar a mudar: baixar para `3.13` funciona, porque
nenhuma dependência do projeto exige recurso exclusivo do 3.14.

### Duas consequências do plano gratuito

**O serviço hiberna.** Depois de um tempo sem tráfego, o Render derruba a
instância, e a primeira requisição seguinte espera o boot, que leva dezenas de
segundos. É por isso que o portal busca os dados no cliente, e nunca em Server
Component: com SSR, essa espera viraria tela branca longa ou falha de build.

**Os dados voltam ao seed a cada restart.** A base é uma lista em memória, então
tudo que for cadastrado pelo painel editorial desaparece quando a instância
hiberna, quando o serviço reinicia ou quando sai um deploy novo. O acervo nunca
fica vazio, porque o `dados_iniciais.json` recarrega no startup, mas conteúdo
criado na demonstração não sobrevive à pausa. Para gravar e mostrar o vídeo
pitch, o caminho previsível é rodar tudo local, ou fazer a demonstração inteira
na mesma sessão, sem deixar o serviço ocioso no meio.

## Pendências da entrega

- [x] `FRONTEND_URL` preenchida com a URL real do deploy
- [x] Link do repositório do portal, no topo deste arquivo
- [x] Link da API publicada

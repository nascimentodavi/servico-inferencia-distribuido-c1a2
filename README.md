# Serviço de Inferência Distribuído

Trabalho C1.A2 — Sistemas Distribuídos e Computação em Nuvem.

Serviço que recebe um texto, executa uma inferência de análise de sentimento
(positivo / negativo / neutro) e devolve o resultado, exposto por duas
interfaces de comunicação (REST e gRPC) e processado de forma assíncrona
através de uma fila.

## Arquitetura

```
                 ┌───────────────┐        ┌───────────────┐
  cliente REST → │   app/rest.py │        │ app/grpc_server│ ← cliente gRPC
                 │   (FastAPI)   │        │   (gRPC)      │
                 └───────┬───────┘        └───────┬───────┘
                         │                        │
                         ▼                        ▼
                     app/servico.py  (lógica de negócio única)
                                 │
                                 ▼
                          app/fila.py  (fila + estado dos jobs no Redis)
                                 │
                        ┌────────┴────────┐
                        ▼                 ▼
                     Redis          app/worker.py
                (fila:tarefas,    (consome a fila, chama
                 job:<id>)         app/modelo.py e grava
                                    o resultado de volta)
```

- **`app/modelo.py`** — modelo de ML (TF-IDF + Regressão Logística,
  scikit-learn), treinado uma única vez e persistido em disco. É carregado
  uma vez por processo (na inicialização do worker), nunca a cada requisição.
- **`app/fila.py`** — único módulo que fala com o Redis. Usa uma lista
  (`fila:tarefas`) como fila FIFO e chaves (`job:<id>`) para guardar o
  status/resultado de cada job.
- **`app/servico.py`** — lógica de negócio compartilhada (validação,
  criação de tarefa, consulta de resultado). **REST e gRPC chamam apenas
  este módulo**, nunca a fila ou o modelo diretamente — é isso que garante
  que as duas interfaces produzam exatamente o mesmo resultado para a
  mesma entrada.
- **`app/rest.py`** — interface REST (FastAPI).
- **`app/grpc_server.py`** + **`proto/inferencia.proto`** — interface gRPC.
- **`app/worker.py`** — processo separado que consome a fila, executa a
  inferência e grava o resultado (ou o erro) no Redis. Pode ser executado
  em mais de uma instância simultânea (elas competem pela mesma fila).

### Fluxo assíncrono

1. Cliente chama a rota/rpc de submissão → o texto é validado e colocado
   na fila do Redis → o cliente recebe imediatamente um `job_id`.
2. Um worker (processo separado) consome a fila, roda a inferência e
   grava o resultado no Redis, marcando o job como `concluido` ou `erro`.
3. Cliente consulta o resultado pelo `job_id` a qualquer momento, pelas
   rotas/rpc de consulta. Possíveis status: `pendente`, `concluido`,
   `erro`, `nao_encontrado`.

### Tratamento de erros e logs

- Toda entrada inválida (texto vazio, job_id vazio) é rejeitada de forma
  explícita: HTTP 400 na REST, `INVALID_ARGUMENT` no gRPC.
- Falhas do worker ao processar uma tarefa não derrubam o processo: o job
  é marcado com `status: erro` e a mensagem fica disponível na consulta.
- Cada requisição recebida (REST e gRPC) é logada com um id de correlação,
  status/resultado e duração.

## Como executar do zero

Pré-requisitos: Python 3.12+, Docker (para o Redis).

```bash
# 1. Clonar o repositório e entrar na pasta
git clone <url-do-repositorio>
cd servico-inferencia-distribuido-c1a2

# 2. Criar e ativar um ambiente virtual
python3 -m venv .virtual-environment
source .virtual-environment/bin/activate

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Subir o Redis
docker compose up -d
```

A partir daqui, abra **três terminais separados** (todos com o venv
ativado e na raiz do projeto):

```bash
# Terminal 1 — worker (processa a fila)
python -m app.worker

# Terminal 2 — API REST, em http://localhost:8000
uvicorn app.rest:app --port 8000

# Terminal 3 — servidor gRPC, em localhost:50051
python -m app.grpc_server
```

### Testando a REST

```bash
# Submeter uma inferência
curl -X POST http://localhost:8000/inferencias \
  -H "Content-Type: application/json" \
  -d '{"texto": "o atendimento foi otimo, recomendo"}'
# -> {"job_id": "..."}

# Consultar o resultado (troque <job_id> pelo valor recebido acima)
curl http://localhost:8000/inferencias/<job_id>
# -> {"status": "concluido", "resultado": {"texto": "...", "sentimento": "positivo", "confianca": 0.76}}
```

### Testando o gRPC

Um cliente de exemplo já está incluso:

```bash
python -m app.grpc_client_exemplo "o atendimento foi otimo, recomendo"
```

Ele cria o job, faz polling do resultado e imprime a resposta — que deve
ser idêntica à obtida pela REST para o mesmo texto.

### Regerando o código gRPC a partir do .proto

O código gerado já está commitado em `app/grpc_gen/`. Caso o contrato
`proto/inferencia.proto` seja alterado, regenere com:

```bash
python -m grpc_tools.protoc -I proto \
  --python_out=app/grpc_gen --grpc_python_out=app/grpc_gen \
  proto/inferencia.proto
```

(depois de regenerar, ajuste o import em `inferencia_pb2_grpc.py` para
`from app.grpc_gen import inferencia_pb2 as inferencia__pb2`, pois o
protoc gera um import absoluto que não funciona dentro do pacote `app`).

## Rodando mais de um worker (extensão opcional)

Como os workers competem pela mesma fila no Redis, basta abrir outro
terminal e rodar novamente `python -m app.worker` — as tarefas serão
divididas entre as instâncias automaticamente. Para distinguir os logs
de cada um, defina `WORKER_ID`:

```bash
WORKER_ID=worker-2 python -m app.worker
```

## Estrutura do repositório

```
app/
  modelo.py              # modelo de ML
  fila.py                # comunicação com o Redis
  servico.py             # lógica de negócio compartilhada (REST + gRPC)
  rest.py                # interface REST (FastAPI)
  grpc_server.py         # interface gRPC
  grpc_client_exemplo.py # cliente gRPC de teste manual
  worker.py              # worker assíncrono
  grpc_gen/              # código gerado a partir do .proto
  logging_config.py      # configuração de log compartilhada
proto/
  inferencia.proto       # contrato gRPC
docker-compose.yml       # sobe o Redis
requirements.txt
```

"""
Módulo da fila.

Responsabilidade única: falar com o Redis. Ninguém fora deste módulo deve
saber que existe um Redis por trás — REST, gRPC e worker só chamam estas
funções.

Duas estruturas do Redis são usadas:
  - uma LISTA ("fila:tarefas") funcionando como fila FIFO (LPUSH / BRPOP);
  - CHAVES simples ("job:<id>") guardando o status/resultado de cada job,
    como uma string JSON.
"""

import json
import logging
import uuid

import redis

logger = logging.getLogger(__name__)

NOME_FILA = "fila:tarefas"
PREFIXO_JOB = "job:"
TEMPO_EXPIRACAO_SEGUNDOS = 60 * 60 * 24  # resultados expiram em 24h

_cliente_redis: redis.Redis | None = None


def conectar(host: str = "localhost", port: int = 6379) -> redis.Redis:
    """Cria (uma vez) e devolve o cliente Redis, reaproveitando a conexão."""
    global _cliente_redis
    if _cliente_redis is None:
        _cliente_redis = redis.Redis(host=host, port=port, decode_responses=True)
    return _cliente_redis


def enfileirar(texto: str) -> str:
    """Cria um job novo, grava status 'pendente' e coloca na fila.

    Devolve o job_id gerado, para o cliente consultar o resultado depois.
    """
    job_id = str(uuid.uuid4())
    cliente = conectar()

    # Grava o status ANTES de enfileirar, para que uma consulta muito rápida
    # (feita logo após o LPUSH) sempre encontre pelo menos "pendente",
    # nunca um job_id "inexistente".
    _salvar_estado(cliente, job_id, {"status": "pendente", "texto": texto})

    tarefa = json.dumps({"job_id": job_id, "texto": texto})
    cliente.lpush(NOME_FILA, tarefa)

    logger.info("Tarefa enfileirada: job_id=%s", job_id)
    return job_id


def consumir_proxima_tarefa(timeout_segundos: int = 5) -> dict | None:
    """Bloqueia esperando a próxima tarefa da fila (usado pelo worker).

    Devolve None se o tempo limite passar sem nenhuma tarefa chegar — isso
    permite ao worker checar periodicamente se deve continuar rodando, em
    vez de bloquear para sempre.
    """
    cliente = conectar()
    resultado = cliente.brpop([NOME_FILA], timeout=timeout_segundos)
    if resultado is None:
        return None

    _, tarefa_json = resultado
    return json.loads(tarefa_json)


def salvar_resultado(job_id: str, resultado: dict) -> None:
    """Marca um job como concluído, gravando o resultado da inferência."""
    cliente = conectar()
    _salvar_estado(cliente, job_id, {"status": "concluido", "resultado": resultado})
    logger.info("Resultado salvo: job_id=%s", job_id)


def salvar_erro(job_id: str, mensagem_erro: str) -> None:
    """Marca um job como falho, gravando a mensagem de erro."""
    cliente = conectar()
    _salvar_estado(cliente, job_id, {"status": "erro", "erro": mensagem_erro})
    logger.warning("Job marcado como erro: job_id=%s erro=%s", job_id, mensagem_erro)


def consultar_estado(job_id: str) -> dict | None:
    """Consulta o status/resultado atual de um job pelo id.

    Devolve None se o job_id não existir (nunca foi criado, ou já expirou).
    """
    cliente = conectar()
    bruto = cliente.get(PREFIXO_JOB + job_id)
    if bruto is None:
        return None
    return json.loads(bruto)


def _salvar_estado(cliente: redis.Redis, job_id: str, estado: dict) -> None:
    """Função interna: serializa e grava o estado de um job, com expiração."""
    chave = PREFIXO_JOB + job_id
    cliente.set(chave, json.dumps(estado), ex=TEMPO_EXPIRACAO_SEGUNDOS)


if __name__ == "__main__":
    # Teste manual rápido: python -m app.fila
    logging.basicConfig(level=logging.INFO)

    job_id = enfileirar("o atendimento foi otimo")
    print("Job criado:", job_id)
    print("Estado logo após criar:", consultar_estado(job_id))

    tarefa = consumir_proxima_tarefa()
    print("Tarefa consumida pelo 'worker':", tarefa)

    salvar_resultado(job_id, {"sentimento": "positivo", "confianca": 0.91})
    print("Estado após salvar resultado:", consultar_estado(job_id))

    print("Consulta de job inexistente:", consultar_estado("id-que-nao-existe"))

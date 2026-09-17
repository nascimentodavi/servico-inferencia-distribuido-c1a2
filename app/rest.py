"""Interface REST (FastAPI) do serviço de inferência.

Só fala com `app.servico` — nunca diretamente com a fila ou com o modelo —
para garantir que REST e gRPC produzam exatamente o mesmo resultado.

Uso: uvicorn app.rest:app --reload --port 8000
"""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import servico
from app.logging_config import configurar_logging

configurar_logging("rest")
logger = logging.getLogger(__name__)

app = FastAPI(title="Serviço de Inferência Distribuído — REST")


@app.middleware("http")
async def log_requisicoes(request: Request, call_next):
    """Registra cada requisição recebida, com um id próprio para correlação,
    e o tempo total de processamento, mesmo em caso de erro."""
    requisicao_id = str(uuid.uuid4())[:8]
    inicio = time.perf_counter()
    logger.info("req=%s %s %s", requisicao_id, request.method, request.url.path)
    try:
        resposta = await call_next(request)
    except Exception:
        duracao_ms = (time.perf_counter() - inicio) * 1000
        logger.exception("req=%s falhou após %.1fms", requisicao_id, duracao_ms)
        raise
    duracao_ms = (time.perf_counter() - inicio) * 1000
    logger.info("req=%s status=%s duracao=%.1fms", requisicao_id, resposta.status_code, duracao_ms)
    return resposta


@app.exception_handler(servico.TextoInvalidoError)
async def tratar_texto_invalido(request: Request, exc: servico.TextoInvalidoError):
    return JSONResponse(status_code=400, content={"erro": str(exc)})


class PedidoInferencia(BaseModel):
    texto: str


class RespostaJobCriado(BaseModel):
    job_id: str


@app.post("/inferencias", response_model=RespostaJobCriado, status_code=202)
def criar_inferencia(pedido: PedidoInferencia):
    """Enfileira uma nova inferência e devolve o identificador do job."""
    job_id = servico.criar_tarefa(pedido.texto)
    return RespostaJobCriado(job_id=job_id)


@app.get("/inferencias/{job_id}")
def consultar_inferencia(job_id: str):
    """Consulta o status/resultado de um job pelo identificador."""
    return servico.consultar_resultado(job_id)


@app.get("/saude")
def saude():
    """Endpoint simples de health-check."""
    return {"status": "ok"}

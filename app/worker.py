"""Worker que consome a fila de tarefas e executa a inferência.

Roda em loop infinito: espera a próxima tarefa (bloqueando com timeout),
executa a inferência com o modelo carregado uma única vez na inicialização,
e grava o resultado (ou o erro) de volta no Redis.

Uso: python -m app.worker
Pode ser executado em mais de uma instância simultânea (ver extensão
opcional de "mais de um worker" do edital) — cada instância compete pela
mesma fila do Redis, então as tarefas são naturalmente divididas entre elas.
"""

import logging
import os

from app import fila, modelo
from app.logging_config import configurar_logging

logger = logging.getLogger(__name__)


def processar_tarefa(modelo_carregado, tarefa: dict) -> None:
    job_id = tarefa["job_id"]
    texto = tarefa["texto"]
    logger.info("Processando job_id=%s", job_id)
    try:
        resultado = modelo.inferir(modelo_carregado, texto)
        fila.salvar_resultado(job_id, resultado)
        logger.info("Job concluído: job_id=%s sentimento=%s", job_id, resultado["sentimento"])
    except ValueError as e:
        fila.salvar_erro(job_id, str(e))
        logger.warning("Job falhou: job_id=%s erro=%s", job_id, e)
    except Exception as e:
        # Qualquer outra falha inesperada também é registrada no job,
        # em vez de derrubar o worker.
        fila.salvar_erro(job_id, f"erro interno: {e}")
        logger.exception("Erro inesperado ao processar job_id=%s", job_id)


def executar(worker_id: str = "worker-1") -> None:
    logger.info("%s iniciado, carregando modelo...", worker_id)
    modelo_carregado = modelo.carregar_modelo()
    logger.info("%s pronto, aguardando tarefas na fila...", worker_id)

    while True:
        tarefa = fila.consumir_proxima_tarefa()
        if tarefa is None:
            continue
        processar_tarefa(modelo_carregado, tarefa)


if __name__ == "__main__":
    configurar_logging("worker")
    executar(worker_id=os.environ.get("WORKER_ID", "worker-1"))

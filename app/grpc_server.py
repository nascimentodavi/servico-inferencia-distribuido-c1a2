"""Interface gRPC do serviço de inferência.

Só fala com `app.servico` — nunca diretamente com a fila ou com o modelo —
para garantir que REST e gRPC produzam exatamente o mesmo resultado para
a mesma entrada.

Uso: python -m app.grpc_server
"""

import logging
import time
import uuid
from concurrent import futures

import grpc

from app import servico
from app.grpc_gen import inferencia_pb2, inferencia_pb2_grpc
from app.logging_config import configurar_logging

logger = logging.getLogger(__name__)


def _resposta_consulta_de(estado: dict) -> inferencia_pb2.RespostaConsulta:
    """Converte o dict devolvido por `servico.consultar_resultado` na
    mensagem protobuf, preenchendo só os campos relevantes ao status."""
    status = estado["status"]
    if status == "concluido":
        resultado = estado["resultado"]
        return inferencia_pb2.RespostaConsulta(
            status=status,
            texto=resultado["texto"],
            sentimento=resultado["sentimento"],
            confianca=resultado["confianca"],
        )
    if status == "erro":
        return inferencia_pb2.RespostaConsulta(status=status, erro=estado["erro"])
    if status == "pendente":
        return inferencia_pb2.RespostaConsulta(status=status, texto=estado["texto"])
    return inferencia_pb2.RespostaConsulta(status=status)


class ServicoInferenciaServicer(inferencia_pb2_grpc.ServicoInferenciaServicer):
    def CriarInferencia(self, request, context):
        requisicao_id = str(uuid.uuid4())[:8]
        inicio = time.perf_counter()
        logger.info("req=%s CriarInferencia", requisicao_id)
        try:
            job_id = servico.criar_tarefa(request.texto)
        except servico.TextoInvalidoError as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            logger.warning("req=%s rejeitado: %s", requisicao_id, e)
            return inferencia_pb2.RespostaJobCriado()
        duracao_ms = (time.perf_counter() - inicio) * 1000
        logger.info("req=%s concluido duracao=%.1fms", requisicao_id, duracao_ms)
        return inferencia_pb2.RespostaJobCriado(job_id=job_id)

    def ConsultarInferencia(self, request, context):
        requisicao_id = str(uuid.uuid4())[:8]
        logger.info("req=%s ConsultarInferencia job_id=%s", requisicao_id, request.job_id)
        try:
            estado = servico.consultar_resultado(request.job_id)
        except servico.TextoInvalidoError as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            logger.warning("req=%s rejeitado: %s", requisicao_id, e)
            return inferencia_pb2.RespostaConsulta()
        return _resposta_consulta_de(estado)


def executar(porta: str = "50051") -> None:
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inferencia_pb2_grpc.add_ServicoInferenciaServicer_to_server(
        ServicoInferenciaServicer(), servidor
    )
    servidor.add_insecure_port(f"[::]:{porta}")
    servidor.start()
    logger.info("Servidor gRPC ouvindo na porta %s", porta)
    servidor.wait_for_termination()


if __name__ == "__main__":
    configurar_logging("grpc")
    executar()

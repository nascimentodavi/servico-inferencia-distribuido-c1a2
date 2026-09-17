"""Cliente gRPC de exemplo, só para teste manual ponta a ponta.

Uso: python -m app.grpc_client_exemplo "seu texto aqui"
"""

import sys
import time

import grpc

from app.grpc_gen import inferencia_pb2, inferencia_pb2_grpc


def main() -> None:
    texto = sys.argv[1] if len(sys.argv) > 1 else "o atendimento foi otimo"

    with grpc.insecure_channel("localhost:50051") as canal:
        stub = inferencia_pb2_grpc.ServicoInferenciaStub(canal)

        resposta = stub.CriarInferencia(inferencia_pb2.PedidoInferencia(texto=texto))
        job_id = resposta.job_id
        print("Job criado:", job_id)

        for _ in range(10):
            estado = stub.ConsultarInferencia(inferencia_pb2.PedidoConsulta(job_id=job_id))
            print("Status:", estado.status)
            if estado.status in ("concluido", "erro"):
                print(estado)
                break
            time.sleep(0.5)


if __name__ == "__main__":
    main()

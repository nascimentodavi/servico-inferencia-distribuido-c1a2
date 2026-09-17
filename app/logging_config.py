"""Configuração de logging compartilhada por REST, gRPC e worker.

Chamar `configurar_logging(nome)` uma vez, no início de cada entrypoint,
para que todo log tenha o mesmo formato e mostre qual processo o gerou.
"""

import logging


def configurar_logging(nome_processo: str) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s [{nome_processo}] %(levelname)s %(name)s: %(message)s",
    )

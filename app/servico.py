"""
Módulo de serviço (lógica de negócio compartilhada).

Este é o único lugar onde a REST e o gRPC devem buscar a lógica de criar
e consultar tarefas. Nenhuma das duas interfaces deve falar diretamente
com `fila.py` — elas só chamam as funções daqui. Isso garante que as duas
produzam exatamente a mesma resposta para a mesma entrada, como exige o
edital.
"""

from app import fila

# Status possíveis de um job, usados tanto aqui quanto pelas interfaces.
STATUS_PENDENTE = "pendente"
STATUS_CONCLUIDO = "concluido"
STATUS_ERRO = "erro"


class TextoInvalidoError(ValueError):
    """Levantado quando o texto recebido do cliente é inválido."""


def criar_tarefa(texto: str) -> str:
    """Valida o texto e enfileira uma nova tarefa de inferência.

    Devolve o job_id para o cliente consultar o resultado depois.
    Levanta TextoInvalidoError se o texto for vazio ou não for string.
    """
    if not isinstance(texto, str) or not texto.strip():
        raise TextoInvalidoError("O campo 'texto' é obrigatório e não pode ser vazio.")

    return fila.enfileirar(texto.strip())


def consultar_resultado(job_id: str) -> dict:
    """Consulta o status/resultado atual de um job.

    Sempre devolve um dicionário com pelo menos a chave 'status':
      - {"status": "nao_encontrado"}                          se o job_id não existe
      - {"status": "pendente", "texto": ...}                  se ainda não foi processado
      - {"status": "concluido", "resultado": {...}}           se já foi processado
      - {"status": "erro", "erro": "..."}                     se o worker falhou ao processar
    """
    if not isinstance(job_id, str) or not job_id.strip():
        raise TextoInvalidoError("O campo 'job_id' é obrigatório e não pode ser vazio.")

    estado = fila.consultar_estado(job_id.strip())
    if estado is None:
        return {"status": "nao_encontrado"}

    return estado


if __name__ == "__main__":
    # Teste manual de ponta a ponta: cria uma tarefa, simula o worker
    # processando-a (sem ainda ter worker.py pronto), e consulta o resultado.
    import logging

    from app import modelo

    logging.basicConfig(level=logging.INFO)

    # 1. Cliente cria a tarefa através do serviço.
    job_id = criar_tarefa("o atendimento foi otimo, recomendo")
    print("Job criado:", job_id)
    print("Consulta logo após criar:", consultar_resultado(job_id))

    # 2. Simulando o que o worker.py vai fazer: consome a fila e processa.
    tarefa = fila.consumir_proxima_tarefa()
    modelo_carregado = modelo.carregar_modelo()
    try:
        resultado = modelo.inferir(modelo_carregado, tarefa["texto"])
        fila.salvar_resultado(tarefa["job_id"], resultado)
    except ValueError as e:
        fila.salvar_erro(tarefa["job_id"], str(e))

    # 3. Cliente consulta de novo, agora já processado.
    print("Consulta após processar:", consultar_resultado(job_id))

    # 4. Testando os casos de erro:
    print("\nConsulta de job inexistente:", consultar_resultado("id-que-nao-existe"))
    try:
        criar_tarefa("")
    except TextoInvalidoError as e:
        print("Erro esperado ao criar com texto vazio:", e)
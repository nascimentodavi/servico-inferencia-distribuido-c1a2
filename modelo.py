"""
Módulo do modelo de IA.

Responsabilidade única: dado um texto, devolver um resultado de sentimento
(positivo / negativo / neutro) com um nível de confiança.

O modelo é treinado UMA VEZ (se ainda não existir um arquivo salvo) e depois
carregado do disco. Quem importar este módulo e chamar `carregar_modelo()`
paga o custo de carregar apenas uma vez por processo — nunca a cada requisição.
"""

import logging
import os

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

CAMINHO_MODELO = os.path.join(os.path.dirname(__file__), "modelo_sentimento.joblib")

# Dataset de exemplo, pequeno e só para fins didáticos.
# Em um cenário real isso viria de um arquivo .csv maior.
TEXTOS_TREINO = [
    "o atendimento foi otimo",
    "adorei o produto, superou minhas expectativas",
    "excelente servico, recomendo muito",
    "fiquei muito satisfeito com a entrega",
    "equipe atenciosa e prestativa",
    "o produto chegou rapido e bem embalado",
    "estou muito feliz com a compra",
    "recomendo esse vendedor, tudo perfeito",
    "otima experiencia de compra, voltarei a comprar",
    "produto excelente, superou expectativas",
    "pessimo atendimento, nao recomendo",
    "o produto veio quebrado e ninguem resolveu",
    "demorou muito e o suporte nao ajudou em nada",
    "experiencia horrivel, nao vou comprar de novo",
    "atendimento arrogante e despreparado",
    "produto de pessima qualidade",
    "estou muito insatisfeito com a compra",
    "nunca mais compro nessa loja, foi terrivel",
    "produto veio com defeito e o suporte ignorou",
    "atendimento pessimo, fui mal tratado",
    "o produto e ok, nada de especial",
    "chegou dentro do prazo, sem grandes surpresas",
    "atendimento mediano, cumpriu o combinado",
    "o produto e razoavel pelo preco",
    "entrega dentro do esperado, nada a reclamar",
    "produto comum, atende ao basico",
]

ROTULOS_TREINO = (
    ["positivo"] * 10
    + ["negativo"] * 10
    + ["neutro"] * 6
)

# _ antes do metodo significa funcao privada
def _treinar_modelo() -> Pipeline:
    """Treina um pipeline simples de TF-IDF + Regressão Logística.

    ngram_range=(1, 2) e um C mais baixo (mais regularização) ajudam o
    modelo a generalizar melhor mesmo com um dataset de treino pequeno.
    """
    logger.info("Nenhum modelo salvo encontrado. Treinando um novo modelo...")
    pipeline = Pipeline([

        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ("clf", LogisticRegression(max_iter=1000, C=5.0)),
        
    ])
    pipeline.fit(TEXTOS_TREINO, ROTULOS_TREINO)
    joblib.dump(pipeline, CAMINHO_MODELO)
    logger.info("Modelo treinado e salvo em %s", CAMINHO_MODELO)
    return pipeline


def carregar_modelo() -> Pipeline:
    """Carrega o modelo do disco se existir; caso contrário, treina um novo.

    Deve ser chamado UMA VEZ por processo (na inicialização da API, do worker
    ou do servidor gRPC) e o resultado guardado em uma variável global.
    """
    if os.path.exists(CAMINHO_MODELO):
        logger.info("Carregando modelo salvo de %s", CAMINHO_MODELO)
        return joblib.load(CAMINHO_MODELO)
    return _treinar_modelo()


def inferir(modelo: Pipeline, texto: str) -> dict:
    """Executa a inferência de sentimento sobre um texto.

    Levanta ValueError se o texto for inválido (vazio ou None), para que
    quem chamar trate o erro explicitamente.
    """
    if not texto or not texto.strip():
        raise ValueError("texto vazio ou inválido")

    rotulo = modelo.predict([texto])[0]
    probabilidades = modelo.predict_proba([texto])[0]
    confianca = max(probabilidades)

    return {
        "texto": texto,
        "sentimento": str(rotulo),
        "confianca": round(float(confianca), 4),
    }


if __name__ == "__main__":
    # Teste manual rápido: python -m app.modelo
    logging.basicConfig(level=logging.INFO)
    modelo = carregar_modelo()
    for exemplo in [
        "o atendimento foi otimo",
        "o produto veio com defeito e ninguem respondeu",
        "chegou no prazo, sem mais",
        "",
    ]:
        try:
            print(inferir(modelo, exemplo))
        except ValueError as e:
            print(f"Erro esperado para texto={exemplo!r}: {e}")

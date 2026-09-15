# Tfidvectorizer
## fit(): Aprende o vocabulário (olha as frases e monta a lista de palavras únicas) e devolve o próprio vetorizador já "treinado".

### exemplo:
```python3
phrases = [
   "o gato subiu no telhado",
    "o cachorro correu no parque",
    "o gato dormiu no sofa", 
]

vectorizer = TfidfVectorizer()

vectorizer.fit(phrases)
```

## transform(): Transforma objeto vetorizador do fit em matriz de números
### exemplo:
```python3
from sklearn.feature_extraction.text import TfidfVectorizer

phrases = [
   "o gato subiu no telhado",
    "o cachorro correu no parque",
    "o gato dormiu no sofa", 
]

vectorizer = TfidfVectorizer()

vectorizer.fit(phrases)

teste_transformado = vectorizer.transform(phrases)
print(teste_transformado.toarray())
```

### resultado esperado:
[
  [0. 0. 0. 0.44451431 0.34520502 0. 0. 0.5844829 0.5844829][0.54645401 0.54645401 0. 0. 0.32274454 0.54645401 0. 0. 0.][0. 0. 0.5844829 0.44451431 0.34520502 0. 0.5844829 0. 0.]
]

Observação: O valor é calculado de acordo com a relevância da palavra na frase em questão. Quanto maior o valor, mais relevante

Os valores são diferentes entre si por conta do IDF -Inverse Document Frequency, a segunda metade da sigla TF-IDF.
A ideia central é: Uma palavra que aparece em quase todas as frases carrega pouca informação útil pra diferenciar uma frase da outra. Uma palavra que aparece em poucas frases é mais "especial" — ela ajuda a identificar do que aquela frase específica trata.
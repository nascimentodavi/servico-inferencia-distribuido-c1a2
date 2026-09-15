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
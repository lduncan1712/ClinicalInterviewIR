from typing import List

from python_venv.models import embedding_model

def get_embeddings(texts:List[str]) -> List[List[float]]:
    """
    Encodes a list of strings into sentence embeddings

    Arguments:
        texts: A list of strings to be encoded

    Returns: A list of embedding vectors corrasponding to each input string
    """
    embeddings = embedding_model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True
    )
    return embeddings.tolist()

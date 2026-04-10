from __future__ import annotations

from typing import List, Dict, Tuple
import math


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def create_similarity_matrix(users: List[Dict]) -> List[List[float]]:
    n = len(users)
    matrix: List[List[float]] = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            s = cosine_similarity(users[i]["vector_description"], users[j]["vector_description"])  # type: ignore[index]
            matrix[i][j] = s
            matrix[j][i] = s
    return matrix


def greedy_matching(matrix: List[List[float]]) -> List[Tuple[int, int]]:
    n = len(matrix)
    used = [False] * n
    pairs: List[Tuple[int, int]] = []

    # Flatten upper triangle with scores
    edges: List[Tuple[float, int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            edges.append((matrix[i][j], i, j))
    edges.sort(reverse=True)

    for score, i, j in edges:
        if not used[i] and not used[j] and score > 0:
            used[i] = used[j] = True
            pairs.append((i, j))
    return pairs


def generate_user_pairs(users: List[Dict]) -> List[Tuple[int, int]]:
    if len(users) < 2:
        return []
    sim = create_similarity_matrix(users)
    idx_pairs = greedy_matching(sim)
    return [(users[i]["user_id"], users[j]["user_id"]) for i, j in idx_pairs]





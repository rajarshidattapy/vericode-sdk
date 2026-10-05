from .diff_analysis import behavior


def behavioral_distance(a: list[dict], b: list[dict]) -> float:
    if not a:
        return 0.0
    return sum(behavior(x) != behavior(y) for x, y in zip(a, b)) / len(a)


def distance_matrix(results: list[list[dict]]) -> list[list[float]]:
    return [[behavioral_distance(a, b) for b in results] for a in results]


def cluster_candidates(matrix: list[list[float]], threshold: float = 0.0) -> list[list[int]]:
    clusters: list[list[int]] = []
    for i in range(len(matrix)):
        for group in clusters:
            if all(matrix[i][j] <= threshold for j in group):
                group.append(i)
                break
        else:
            clusters.append([i])
    return clusters


def medoid(group: list[int], matrix: list[list[float]]) -> int:
    return min(group, key=lambda i: sum(matrix[i][j] for j in group))


def select_candidate(analysis: dict, threshold: float = 0.0) -> dict:
    matrix = distance_matrix(analysis["results"])
    clusters = cluster_candidates(matrix, threshold)
    largest = max(clusters, key=len)
    selected = medoid(largest, matrix)
    return {
        "matrix": matrix,
        "clusters": clusters,
        "largest": largest,
        "selected": selected,
        "code": analysis["candidates"][selected],
        "func_name": analysis["func_name"],
    }

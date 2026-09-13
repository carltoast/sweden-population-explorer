from itertools import product
import pandas as pd


def jsonstat_to_dataframe(data):
    dimensions = data["id"]
    categories = {}

    for dimension in dimensions:
        category = data["dimension"][dimension]["category"]

        # Get category codes in their correct order
        index = category["index"]

        if isinstance(index, dict):
            codes = [
                code
                for code, _ in sorted(index.items(), key=lambda item: item[1])
            ]
        else:
            codes = index

        # Get human-readable labels
        labels = category.get("label", {})

        categories[dimension] = [
            (code, labels.get(code, code))
            for code in codes
        ]

    rows = []

    combinations = product(
        *(categories[dimension] for dimension in dimensions)
    )

    for value, combination in zip(data["value"], combinations):
        row = {}

        for dimension, (code, label) in zip(dimensions, combination):
            row[f"{dimension}_code"] = code
            row[dimension] = label

        row["value"] = value
        rows.append(row)

    return pd.DataFrame(rows)
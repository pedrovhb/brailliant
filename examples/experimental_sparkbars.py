from __future__ import annotations

from brailliant._experimental.sparkbars import get_sparkbar, get_sparkbar_normalized


if __name__ == "__main__":
    print("Raw sparkbars")
    print(get_sparkbar([3, 4, 1]))
    print(get_sparkbar([2, 6, 9, 12], min_width=8))
    print()

    print("Normalized sparkbars")
    print(get_sparkbar_normalized([10, 30, 20], width=10))
    print(get_sparkbar_normalized([-10, 40, 60, 0], width=12, min_data_value=-10, max_data_value=60))

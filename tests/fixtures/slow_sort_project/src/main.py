import sys
sys.path.insert(0, ".")
from src.sorter import bubble_sort
from src.utils import timed_run, result_hash

data = list(range(1000, 0, -1))  # worst case: reverse sorted
elapsed, result = timed_run(bubble_sort, data)
print(f"time={elapsed:.4f}s result_hash={result_hash(result)}")

import time, hashlib, json

def timed_run(fn, *args):
    start = time.time()
    result = fn(*args)
    elapsed = time.time() - start
    return elapsed, result

def result_hash(data):
    return hashlib.md5(json.dumps(sorted(data)).encode()).hexdigest()[:8]

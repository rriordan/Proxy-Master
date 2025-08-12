import sys
if sys.platform.startswith("win"):
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import aiohttp
import asyncio
import csv
import os
from time import perf_counter, time
from tqdm.asyncio import tqdm
from collections import defaultdict, deque

# SETTINGS - Updated to use getproxy.py output files
PROXY_FILE_HTTP     = "http.txt"
PROXY_FILE_SOCKS5   = "socks5.txt"
PROXY_FILE_SOCKS4   = "socks4.txt"
CSV_FILE            = "proxy_benchmark_results.csv"
GOOD_FILE           = "working-fast.txt"
BAD_FILE            = "bad.txt"
TOP_N_FILE          = "TopProxies.txt"
ROTATION_FILE       = "RotationList.txt"
HISTORY_FILE        = "proxy_history.csv"
FAILED_FILE         = "FailedProxies.txt"
RESPONDED_FILE      = "RespondedProxies.txt"

TEST_URL            = "http://ipv4.download.thinkbroadband.com/100MB.zip"
CHUNK_RANGE         = "bytes=0-10485759"  # first 10 MB
TIMEOUT             = 10                  # seconds
CONCURRENT_LIMIT    = 200                 # max simultaneous tasks
TOP_N_COUNT         = 150                 # number of top proxies to select
HISTORY_MAX_RUNS    = 10                  # keep last N runs per proxy
MIN_TESTS_FOR_FAIL  = 3                   # threshold to consider continuous failures

# PRE-SCREENING SETTINGS
PRE_SCREEN_URL      = "http://httpbin.org/ip"  # Lightweight test URL
PRE_SCREEN_TIMEOUT  = 5                   # Quick timeout for pre-screening
PRE_SCREEN_CONCURRENT = 100               # Concurrent limit for pre-screening

# GLOBAL RESULTS
good, bad = [], []
sem = asyncio.Semaphore(CONCURRENT_LIMIT)
pre_screen_sem = asyncio.Semaphore(PRE_SCREEN_CONCURRENT)

async def pre_screen_proxy(session, proxy: str, scheme: str) -> tuple:
    """Quick connectivity test to filter out dead proxies before performance testing."""
    proxy_url = f"{scheme}://{proxy}"
    try:
        async with pre_screen_sem:
            timeout = aiohttp.ClientTimeout(total=PRE_SCREEN_TIMEOUT)
            async with session.get(PRE_SCREEN_URL, proxy=proxy_url, timeout=timeout) as resp:
                if resp.status == 200:
                    return proxy, scheme, True
                else:
                    return proxy, scheme, False
    except Exception:
        return proxy, scheme, False

async def pre_screen_proxies(proxies: list, scheme: str) -> list:
    """Pre-screen proxies to filter out dead ones before performance testing."""
    print(f"Pre-screening {len(proxies)} {scheme.upper()} proxies...")
    
    connector = aiohttp.TCPConnector(ssl=False, limit=None)
    timeout = aiohttp.ClientTimeout(total=PRE_SCREEN_TIMEOUT)
    
    responsive_proxies = []
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [pre_screen_proxy(session, p, scheme) for p in proxies]
        
        for future in tqdm(asyncio.as_completed(tasks),
                           total=len(tasks),
                           desc=f"Pre-screening {scheme.upper()}",
                           unit="proxy"):
            proxy, proxy_scheme, is_responsive = await future
            if is_responsive:
                responsive_proxies.append(proxy)
    
    print(f"Pre-screening complete: {len(responsive_proxies)}/{len(proxies)} {scheme.upper()} proxies are responsive")
    return responsive_proxies

async def try_proxy(session, proxy: str, scheme: str) -> tuple:
    proxy_url = f"{scheme}://{proxy}"
    headers   = {"Range": CHUNK_RANGE}
    try:
        async with sem:
            start = perf_counter()
            async with session.get(TEST_URL, headers=headers, proxy=proxy_url, timeout=TIMEOUT) as resp:
                if resp.status not in (200, 206):
                    raise Exception(f"HTTP {resp.status}")
                total = 0
                async for chunk in resp.content.iter_chunked(65536):
                    total += len(chunk)
                    if total >= 10 * 1024 * 1024:
                        break
                elapsed = perf_counter() - start
                speed   = total / elapsed / 1024 / 1024
                latency = elapsed
                score   = speed / (latency + 0.01)
                good.append(proxy)
                return proxy, scheme, latency, speed, score, True
    except Exception:
        bad.append(proxy)
        return proxy, scheme, None, None, 0.0, False

async def run_tests(proxies: list, scheme: str):
    connector = aiohttp.TCPConnector(ssl=False, limit=None)
    timeout   = aiohttp.ClientTimeout(total=TIMEOUT)
    results   = []
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [try_proxy(session, p, scheme) for p in proxies]
        for future in tqdm(asyncio.as_completed(tasks),
                           total=len(tasks),
                           desc=f"Testing {scheme.upper()}",
                           unit="proxy"):
            res = await future
            results.append(res)
    return results

def load_proxies(path: str):
    try:
        with open(path) as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Warning: {path} not found. Skipping {path.split('.')[0]} proxies.")
        return []

def load_history():
    history = defaultdict(lambda: deque(maxlen=HISTORY_MAX_RUNS))
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            reader = csv.DictReader(f)
            for row in reader:
                proxy = row['Proxy']
                score = float(row['Score'])
                success = row['Success'] == '1'
                history[proxy].append((score, success))
    return history

def save_history(history):
    with open(HISTORY_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Proxy", "Timestamp", "Score", "Success"])
        for proxy, entries in history.items():
            for score, success in entries:
                writer.writerow([proxy, int(time()), f"{score:.2f}", '1' if success else '0'])

async def main():
    print("Starting proxy benchmark...")
    print(f"Loading proxies from: {PROXY_FILE_HTTP}, {PROXY_FILE_SOCKS5}, {PROXY_FILE_SOCKS4}")
    
    t0 = perf_counter()
    http_list   = load_proxies(PROXY_FILE_HTTP)
    socks5_list = load_proxies(PROXY_FILE_SOCKS5)
    socks4_list = load_proxies(PROXY_FILE_SOCKS4)

    total_proxies = len(http_list) + len(socks5_list) + len(socks4_list)
    if total_proxies == 0:
        print("No proxies found! Make sure getproxy.py has been run first.")
        return
    
    print(f"Loaded {len(http_list)} HTTP, {len(socks5_list)} SOCKS5, {len(socks4_list)} SOCKS4 proxies")
    print(f"Total proxies loaded: {total_proxies}")

    # Pre-screen proxies to filter out dead ones
    print("\n=== PRE-SCREENING PHASE ===")
    http_proxies_to_test = await pre_screen_proxies(http_list, "http")
    socks5_proxies_to_test = await pre_screen_proxies(socks5_list, "socks5")
    socks4_proxies_to_test = await pre_screen_proxies(socks4_list, "socks4")

    all_proxies_to_test = http_proxies_to_test + socks5_proxies_to_test + socks4_proxies_to_test
    if not all_proxies_to_test:
        print("No responsive proxies found after pre-screening!")
        return

    print(f"\n=== PERFORMANCE TESTING PHASE ===")
    print(f"Proxies to test: {len(all_proxies_to_test)} (filtered from {total_proxies} total)")
    print(f"Filtered out: {total_proxies - len(all_proxies_to_test)} dead/unresponsive proxies")

    all_results = []
    if http_proxies_to_test:
        all_results += await run_tests(http_proxies_to_test, "http")
    if socks5_proxies_to_test:
        all_results += await run_tests(socks5_proxies_to_test, "socks5")
    if socks4_proxies_to_test:
        all_results += await run_tests(socks4_proxies_to_test, "socks4")

    history = load_history()
    for proxy, scheme, lat, spd, sc, success in all_results:
        history[proxy].append((sc, success))
    save_history(history)

    # Identify failed and responded
    failed = []
    responded = []
    for proxy, entries in history.items():
        if len(entries) >= MIN_TESTS_FOR_FAIL:
            if all(not succ for _, succ in list(entries)[-MIN_TESTS_FOR_FAIL:]):
                failed.append(proxy)
        if any(succ for _, succ in entries):
            responded.append(proxy)

    with open(FAILED_FILE, "w") as f:
        f.write("\n".join(failed))
    with open(RESPONDED_FILE, "w") as f:
        f.write("\n".join(responded))

    # Prepare CSV rows
    rows = []
    for proxy, scheme, lat, spd, sc, success in all_results:
        entries = list(history[proxy])
        lt = sum(score for score, _ in entries) / len(entries) if entries else sc
        rr = sum(1 for _, succ in entries if succ)/len(entries)*100 if entries else (100.0 if success else 0.0)
        ss = [score for score, succ in entries if succ]
        ra = sum(ss)/len(ss) if ss else 0.0
        rows.append((proxy, scheme, lat, spd, sc, lt, rr, ra))

    sorted_rows = sorted(rows, key=lambda r: r[5], reverse=True)

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Proxy","Protocol","Latency (s)","Speed (MB/s)",
            "Current Score","Long-Term Score",
            "Response Rate (%)","Response AVG"
        ])
        for proxy, scheme, lat, spd, sc, lt, rr, ra in sorted_rows:
            writer.writerow([
                proxy, scheme,
                f"{lat:.3f}" if lat else "",
                f"{spd:.2f}" if spd else "",
                f"{sc:.2f}", f"{lt:.2f}",
                f"{rr:.1f}", f"{ra:.2f}"
            ])

    top_n = sorted_rows[:TOP_N_COUNT]
    with open(TOP_N_FILE, "w") as f:
        for proxy, scheme, *_ in top_n:
            f.write(f"{scheme}://{proxy}\n")
    with open(ROTATION_FILE, "w") as f:
        for proxy, scheme, *_ in sorted_rows:
            f.write(f"{scheme}://{proxy}\n")

    elapsed = perf_counter() - t0
    print(f"\n=== BENCHMARK SUMMARY ===")
    print(f"Total time: {elapsed:.2f}s")
    print(f"Pre-screening: Filtered {total_proxies - len(all_proxies_to_test)} dead proxies from {total_proxies} total")
    print(f"Performance testing: {len(good)} good, {len(bad)} bad")
    print(f"Failed proxies:    {len(failed)} → {FAILED_FILE}")
    print(f"Responded proxies: {len(responded)} → {RESPONDED_FILE}")
    print(f"Top {len(top_n)} proxies saved to: {TOP_N_FILE}")
    print(f"All results saved to: {CSV_FILE}")

if __name__ == "__main__":
    asyncio.run(main())

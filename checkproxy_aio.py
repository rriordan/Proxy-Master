import asyncio
import httpx
import csv
import time
from pathlib import Path
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)

CHECK_TIMEOUT_SECONDS = 15
PROXY_FILES = {"http": "http.txt", "socks4": "socks4.txt", "socks5": "socks5.txt"}
OUTPUT_CSV = "checked_proxies.csv"


class Proxy:
    def __init__(self, protocol: str, address: str):
        self.protocol = protocol
        self.address = address.strip()
        self.link = f"{protocol}://{self.address}"


def load_proxies() -> list[Proxy]:
    proxies: list[Proxy] = []
    for proto, fname in PROXY_FILES.items():
        path = Path(fname)
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if line:
                proxies.append(Proxy(proto, line))
    return proxies


async def check_proxy(client: httpx.AsyncClient, proxy: Proxy) -> Proxy | None:
    try:
        resp = await client.get(
            "https://httpbin.org/ip",
            proxies=proxy.link,
            timeout=CHECK_TIMEOUT_SECONDS,
        )
        if resp.status_code == 200:
            return proxy
    except Exception:
        return None


async def run_checker(workers: int):
    proxies = load_proxies()
    total = len(proxies)
    results: dict[str, list[str]] = {p: [] for p in PROXY_FILES}
    start_time = time.time()
    semaphore = asyncio.Semaphore(workers)

    async with httpx.AsyncClient() as client:
        # Use a synchronous context manager for Progress
        with Progress(
            TextColumn("[green]I[/green]:"),
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("• Elapsed:"),
            TimeElapsedColumn(),
            TextColumn("• ETA:"),
            TimeRemainingColumn(),
            TextColumn("• Left: {task.total - task.completed}"),
            TextColumn("• {task.fields[rate]:.2f} req/s"),
        ) as progress:
            task = progress.add_task("Checking proxies...", total=total, rate=0.0)

            async def bound_check(proxy: Proxy):
                async with semaphore:
                    ok = await check_proxy(client, proxy)
                    elapsed = time.time() - start_time
                    rate = progress.tasks[0].completed / max(elapsed, 1e-6)
                    progress.update(task, advance=1, rate=rate)
                    if ok:
                        results[ok.protocol].append(ok.address)

            await asyncio.gather(*(bound_check(p) for p in proxies))

    duration = time.time() - start_time
    avg_rate = total / duration if duration > 0 else 0.0

    # Write CSV with one column per protocol
    protocols = list(PROXY_FILES)
    max_rows = max(len(v) for v in results.values())
    with open(OUTPUT_CSV, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=protocols)
        writer.writeheader()
        for i in range(max_rows):
            row = {proto: (results[proto][i] if i < len(results[proto]) else "")
                   for proto in protocols}
            writer.writerow(row)

    print(f"\nI: Completed in {duration:.2f}s — average {avg_rate:.2f} proxies/s")
    print(f"I: Results written to {OUTPUT_CSV}")


if __name__ == "__main__":
    import sys

    workers = 100
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        workers = int(sys.argv[1])
    print(f"I: Running with {workers} concurrent workers")
    asyncio.run(run_checker(workers))

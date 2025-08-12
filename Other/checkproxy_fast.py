import asyncio
import httpx
import csv
import time
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.console import Console
from rich.table import Table

# Configuration - Optimized for speed
QUICK_TIMEOUT = 3  # Very fast timeout for initial check
SPEED_TIMEOUT = 8  # Moderate timeout for speed test
MAX_WORKERS = 500  # Higher concurrency for faster processing

# Single speed test URL - small but enough to measure speed
SPEED_TEST_URL = "https://httpbin.org/bytes/5120"  # 5KB test

@dataclass
class ProxyResult:
    """Results from proxy testing"""
    protocol: str
    address: str
    is_working: bool = False
    response_time: float = 0.0
    speed_mbps: float = 0.0
    error: str = ""

class Proxy:
    def __init__(self, protocol: str, address: str):
        self.protocol = protocol
        self.address = address.strip()
        self.link = f"{protocol}://{self.address}"

def load_proxies() -> List[Proxy]:
    """Load proxies from text files"""
    proxies: List[Proxy] = []
    proxy_files = {"http": "http.txt", "socks4": "socks4.txt", "socks5": "socks5.txt"}
    
    for proto, filename in proxy_files.items():
        path = Path(filename)
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if line.strip():
                proxies.append(Proxy(proto, line))
    
    return proxies

async def quick_connectivity_check(client: httpx.AsyncClient, proxy: Proxy) -> bool:
    """Ultra-fast connectivity check"""
    try:
        resp = await client.get(
            "https://httpbin.org/ip",
            proxies={"http://": proxy.link, "https://": proxy.link},
            timeout=QUICK_TIMEOUT,
        )
        return resp.status_code == 200
    except Exception:
        return False

async def single_speed_test(client: httpx.AsyncClient, proxy: Proxy) -> Tuple[float, float]:
    """Single speed test - much faster than multiple tests"""
    try:
        start_time = time.time()
        resp = await client.get(
            SPEED_TEST_URL,
            proxies={"http://": proxy.link, "https://": proxy.link},
            timeout=SPEED_TIMEOUT,
        )
        if resp.status_code == 200:
            content_length = len(resp.content)
            test_time = time.time() - start_time
            
            # Calculate speed in Mbps
            if content_length > 0 and test_time > 0:
                speed_mbps = (content_length * 8) / (test_time * 1_000_000)
            else:
                speed_mbps = 0.0
            
            return speed_mbps, test_time
        else:
            return 0.0, float('inf')
    except Exception:
        return 0.0, float('inf')

async def check_proxy_fast(client: httpx.AsyncClient, proxy: Proxy) -> Optional[ProxyResult]:
    """Fast proxy checking - connectivity + single speed test"""
    result = ProxyResult(protocol=proxy.protocol, address=proxy.address)
    
    # Quick connectivity check first
    if not await quick_connectivity_check(client, proxy):
        result.error = "Failed connectivity check"
        return result
    
    # Single speed test for working proxies
    speed_mbps, response_time = await single_speed_test(client, proxy)
    
    if speed_mbps > 0:
        result.is_working = True
        result.response_time = response_time
        result.speed_mbps = speed_mbps
    else:
        result.error = "Failed speed test"
    
    return result

async def run_fast_checker(workers: int = 200):
    """Run the fast proxy checker"""
    console = Console()
    proxies = load_proxies()
    
    if not proxies:
        console.print("[red]No proxy files found! Run getproxy.py first.[/red]")
        return
    
    console.print(f"[green]Loaded {len(proxies):,} proxies to test[/green]")
    console.print(f"[green]Using {workers} concurrent workers[/green]")
    console.print(f"[green]Quick timeout: {QUICK_TIMEOUT}s, Speed timeout: {SPEED_TIMEOUT}s[/green]")
    
    # Shuffle proxies for better distribution
    random.shuffle(proxies)
    
    results: List[ProxyResult] = []
    semaphore = asyncio.Semaphore(workers)
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        with Progress(
            TextColumn("[green]Testing[/green]"),
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("• ETA:"),
            TimeRemainingColumn(),
            TextColumn("• {task.fields[rate]:.1f}/s"),
        ) as progress:
            task = progress.add_task("Checking proxies...", total=len(proxies), rate=0.0)
            
            async def bound_check(proxy: Proxy):
                async with semaphore:
                    result = await check_proxy_fast(client, proxy)
                    if result and result.is_working:
                        results.append(result)
                    
                    # Update progress
                    elapsed = time.time() - start_time
                    rate = progress.tasks[0].completed / max(elapsed, 1e-6)
                    progress.update(task, advance=1, rate=rate)
            
            await asyncio.gather(*(bound_check(p) for p in proxies))
    
    # Sort results by speed (fastest first)
    results.sort(key=lambda x: x.speed_mbps, reverse=True)
    
    # Display results
    display_fast_results(results, console, start_time)
    
    # Save results
    save_fast_results(results)

def display_fast_results(results: List[ProxyResult], console: Console, start_time: float):
    """Display results in a nice table"""
    total_time = time.time() - start_time
    console.print(f"\n[green]Found {len(results)} working proxies in {total_time:.1f}s[/green]")
    
    if not results:
        return
    
    # Create table
    table = Table(title="Top 20 Fastest Proxies")
    table.add_column("Rank", style="cyan")
    table.add_column("Protocol", style="magenta")
    table.add_column("Address", style="green")
    table.add_column("Speed (Mbps)", style="yellow")
    table.add_column("Response Time (s)", style="blue")
    
    for i, result in enumerate(results[:20], 1):
        table.add_row(
            str(i),
            result.protocol.upper(),
            result.address,
            f"{result.speed_mbps:.2f}",
            f"{result.response_time:.3f}"
        )
    
    console.print(table)
    
    # Summary statistics
    if results:
        avg_speed = sum(r.speed_mbps for r in results) / len(results)
        max_speed = max(r.speed_mbps for r in results)
        min_speed = min(r.speed_mbps for r in results)
        
        console.print(f"\n[cyan]Summary:[/cyan]")
        console.print(f"  Working proxies: {len(results):,}")
        console.print(f"  Average Speed: {avg_speed:.2f} Mbps")
        console.print(f"  Fastest Proxy: {max_speed:.2f} Mbps")
        console.print(f"  Slowest Proxy: {min_speed:.2f} Mbps")
        console.print(f"  Processing rate: {len(results)/total_time:.1f} proxies/second")

def save_fast_results(results: List[ProxyResult]):
    """Save results to CSV and text files"""
    if not results:
        return
    
    # Save to CSV with detailed information
    csv_filename = "fast_checked_proxies.csv"
    with open(csv_filename, 'w', newline='') as csvfile:
        fieldnames = ['Protocol', 'Address', 'Speed_Mbps', 'Response_Time_s']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            writer.writerow({
                'Protocol': result.protocol,
                'Address': result.address,
                'Speed_Mbps': f"{result.speed_mbps:.2f}",
                'Response_Time_s': f"{result.response_time:.3f}"
            })
    
    # Save top proxies by protocol to separate files
    for protocol in ['http', 'socks4', 'socks5']:
        protocol_results = [r for r in results if r.protocol == protocol]
        if protocol_results:
            # Sort by speed for this protocol
            protocol_results.sort(key=lambda x: x.speed_mbps, reverse=True)
            
            # Save top 200 to text file (more than enhanced version)
            filename = f"{protocol}_fast_checked.txt"
            with open(filename, 'w') as f:
                for result in protocol_results[:200]:
                    f.write(f"{result.address}\n")
    
    print(f"\n[green]Results saved to:[/green]")
    print(f"  • {csv_filename} (detailed CSV)")
    print(f"  • http_fast_checked.txt (top 200 HTTP proxies)")
    print(f"  • socks4_fast_checked.txt (top 200 SOCKS4 proxies)")
    print(f"  • socks5_fast_checked.txt (top 200 SOCKS5 proxies)")

if __name__ == "__main__":
    import sys
    
    workers = 200
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        workers = int(sys.argv[1])
    
    workers = min(workers, MAX_WORKERS)  # Cap at reasonable limit
    print(f"Fast Proxy Checker for Megabasterd")
    print(f"Workers: {workers}")
    print(f"Quick timeout: {QUICK_TIMEOUT}s")
    print(f"Speed test timeout: {SPEED_TIMEOUT}s")
    print(f"Speed test URL: {SPEED_TEST_URL}")
    
    asyncio.run(run_fast_checker(workers))


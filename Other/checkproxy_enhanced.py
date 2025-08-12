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
    MofNCompleteColumn,
)
from rich.console import Console
from rich.table import Table

# Configuration
FAST_TIMEOUT = 5  # Quick initial check
SLOW_TIMEOUT = 15  # Full speed test timeout
SPEED_TEST_SIZE = 1024 * 1024  # 1MB for speed testing
MAX_WORKERS = 200  # Reasonable concurrency limit

# Test URLs optimized for file hosting services
TEST_URLS = [
    "https://httpbin.org/bytes/1024",  # Small test
    "https://httpbin.org/bytes/10240",  # Medium test
    "https://httpbin.org/stream/100",   # Streaming test
    "https://www.google.com/favicon.ico",  # Real-world small file
    "https://www.cloudflare.com/favicon.ico",  # Another real-world test
]

@dataclass
class ProxyResult:
    """Results from proxy testing"""
    protocol: str
    address: str
    is_working: bool = False
    response_time: float = 0.0
    speed_mbps: float = 0.0
    success_rate: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

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

async def quick_check(client: httpx.AsyncClient, proxy: Proxy) -> bool:
    """Quick connectivity check"""
    try:
        resp = await client.get(
            "https://httpbin.org/ip",
            proxies={"http://": proxy.link, "https://": proxy.link},
            timeout=FAST_TIMEOUT,
        )
        return resp.status_code == 200
    except Exception:
        return False

async def speed_test(client: httpx.AsyncClient, proxy: Proxy) -> Tuple[float, float, List[str]]:
    """Test proxy speed and reliability"""
    errors = []
    successful_tests = 0
    total_tests = len(TEST_URLS)
    total_time = 0.0
    total_bytes = 0
    
    for url in TEST_URLS:
        try:
            start_time = time.time()
            resp = await client.get(
                url,
                proxies={"http://": proxy.link, "https://": proxy.link},
                timeout=SLOW_TIMEOUT,
            )
            if resp.status_code == 200:
                content_length = len(resp.content)
                test_time = time.time() - start_time
                total_time += test_time
                total_bytes += content_length
                successful_tests += 1
            else:
                errors.append(f"HTTP {resp.status_code} for {url}")
        except Exception as e:
            errors.append(f"Error testing {url}: {str(e)}")
    
    success_rate = successful_tests / total_tests if total_tests > 0 else 0
    avg_time = total_time / successful_tests if successful_tests > 0 else float('inf')
    
    # Calculate speed in Mbps
    if total_bytes > 0 and total_time > 0:
        speed_mbps = (total_bytes * 8) / (total_time * 1_000_000)  # Convert to Mbps
    else:
        speed_mbps = 0.0
    
    return speed_mbps, avg_time, errors

async def check_proxy_enhanced(client: httpx.AsyncClient, proxy: Proxy) -> Optional[ProxyResult]:
    """Enhanced proxy checking with speed testing"""
    result = ProxyResult(protocol=proxy.protocol, address=proxy.address)
    
    # Quick connectivity check first
    if not await quick_check(client, proxy):
        result.errors.append("Failed quick connectivity check")
        return result
    
    # If quick check passes, do speed testing
    speed_mbps, response_time, errors = await speed_test(client, proxy)
    
    result.is_working = True
    result.response_time = response_time
    result.speed_mbps = speed_mbps
    result.success_rate = 1.0 - (len(errors) / len(TEST_URLS)) if TEST_URLS else 0.0
    result.errors = errors
    
    return result

async def run_enhanced_checker(workers: int = 100):
    """Run the enhanced proxy checker"""
    console = Console()
    proxies = load_proxies()
    
    if not proxies:
        console.print("[red]No proxy files found! Run getproxy.py first.[/red]")
        return
    
    console.print(f"[green]Loaded {len(proxies)} proxies to test[/green]")
    console.print(f"[green]Using {workers} concurrent workers[/green]")
    
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
                    result = await check_proxy_enhanced(client, proxy)
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
    display_results(results, console)
    
    # Save results
    save_results(results)

def display_results(results: List[ProxyResult], console: Console):
    """Display results in a nice table"""
    console.print(f"\n[green]Found {len(results)} working proxies[/green]")
    
    if not results:
        return
    
    # Create table
    table = Table(title="Top 20 Fastest Proxies")
    table.add_column("Rank", style="cyan")
    table.add_column("Protocol", style="magenta")
    table.add_column("Address", style="green")
    table.add_column("Speed (Mbps)", style="yellow")
    table.add_column("Response Time (s)", style="blue")
    table.add_column("Success Rate", style="green")
    
    for i, result in enumerate(results[:20], 1):
        table.add_row(
            str(i),
            result.protocol.upper(),
            result.address,
            f"{result.speed_mbps:.2f}",
            f"{result.response_time:.3f}",
            f"{result.success_rate:.1%}"
        )
    
    console.print(table)
    
    # Summary statistics
    if results:
        avg_speed = sum(r.speed_mbps for r in results) / len(results)
        max_speed = max(r.speed_mbps for r in results)
        min_speed = min(r.speed_mbps for r in results)
        
        console.print(f"\n[cyan]Summary:[/cyan]")
        console.print(f"  Average Speed: {avg_speed:.2f} Mbps")
        console.print(f"  Fastest Proxy: {max_speed:.2f} Mbps")
        console.print(f"  Slowest Proxy: {min_speed:.2f} Mbps")

def save_results(results: List[ProxyResult]):
    """Save results to CSV and text files"""
    if not results:
        return
    
    # Save to CSV with detailed information
    csv_filename = "enhanced_checked_proxies.csv"
    with open(csv_filename, 'w', newline='') as csvfile:
        fieldnames = ['Protocol', 'Address', 'Speed_Mbps', 'Response_Time_s', 'Success_Rate', 'Errors']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            writer.writerow({
                'Protocol': result.protocol,
                'Address': result.address,
                'Speed_Mbps': f"{result.speed_mbps:.2f}",
                'Response_Time_s': f"{result.response_time:.3f}",
                'Success_Rate': f"{result.success_rate:.1%}",
                'Errors': '; '.join(result.errors) if result.errors else ''
            })
    
    # Save top proxies by protocol to separate files
    for protocol in ['http', 'socks4', 'socks5']:
        protocol_results = [r for r in results if r.protocol == protocol]
        if protocol_results:
            # Sort by speed for this protocol
            protocol_results.sort(key=lambda x: x.speed_mbps, reverse=True)
            
            # Save top 100 to text file
            filename = f"{protocol}_enhanced_checked.txt"
            with open(filename, 'w') as f:
                for result in protocol_results[:100]:
                    f.write(f"{result.address}\n")
    
    print(f"\n[green]Results saved to:[/green]")
    print(f"  • {csv_filename} (detailed CSV)")
    print(f"  • http_enhanced_checked.txt (top HTTP proxies)")
    print(f"  • socks4_enhanced_checked.txt (top SOCKS4 proxies)")
    print(f"  • socks5_enhanced_checked.txt (top SOCKS5 proxies)")

if __name__ == "__main__":
    import sys
    
    workers = 100
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        workers = int(sys.argv[1])
    
    workers = min(workers, MAX_WORKERS)  # Cap at reasonable limit
    print(f"Enhanced Proxy Checker for Megabasterd")
    print(f"Workers: {workers}")
    print(f"Fast timeout: {FAST_TIMEOUT}s")
    print(f"Speed test timeout: {SLOW_TIMEOUT}s")
    
    asyncio.run(run_enhanced_checker(workers))

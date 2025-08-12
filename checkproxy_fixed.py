import asyncio
import httpx
import csv
import time
import random
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
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

# Configuration
QUICK_TIMEOUT = 3  # Connectivity check timeout
SPEED_TIMEOUT = 8  # Speed test timeout
MAX_WORKERS = 300  # Reasonable concurrency

# Speed test URL
SPEED_TEST_URL = "https://httpbin.org/bytes/25600"  # 25KB test

# Performance scoring weights
SPEED_WEIGHT = 0.7
LATENCY_WEIGHT = 0.3

@dataclass
class ProxyResult:
    """Results from proxy testing"""
    protocol: str
    address: str
    is_working: bool = False
    response_time: float = 0.0
    speed_mbps: float = 0.0
    error: str = ""
    performance_score: float = 0.0

@dataclass
class ProxyHistory:
    """Historical performance data for a proxy"""
    address: str
    protocol: str
    first_seen: str
    last_seen: str
    total_tests: int = 0
    successful_tests: int = 0
    avg_speed_mbps: float = 0.0
    avg_response_time: float = 0.0
    best_speed_mbps: float = 0.0
    worst_speed_mbps: float = float('inf')
    long_term_score: float = 0.0
    reliability_rate: float = 0.0

class Proxy:
    def __init__(self, protocol: str, address: str):
        self.protocol = protocol
        self.address = address.strip()
        self.link = f"{protocol}://{self.address}"

class ProxyDatabase:
    """Manages proxy performance history"""
    
    def __init__(self, history_file: str = "proxy_history.json"):
        self.history_file = history_file
        self.history: Dict[str, ProxyHistory] = self.load_history()
    
    def load_history(self) -> Dict[str, ProxyHistory]:
        """Load existing proxy history"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    return {addr: ProxyHistory(**proxy_data) for addr, proxy_data in data.items()}
            except Exception as e:
                print(f"Warning: Could not load history: {e}")
        return {}
    
    def save_history(self):
        """Save proxy history to file"""
        try:
            data = {addr: asdict(proxy) for addr, proxy in self.history.items()}
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save history: {e}")
    
    def update_proxy(self, result: ProxyResult):
        """Update proxy performance history"""
        now = datetime.now().isoformat()
        
        if result.address not in self.history:
            # New proxy
            self.history[result.address] = ProxyHistory(
                address=result.address,
                protocol=result.protocol,
                first_seen=now,
                last_seen=now,
                total_tests=1,
                successful_tests=1 if result.is_working else 0,
                avg_speed_mbps=result.speed_mbps if result.is_working else 0.0,
                avg_response_time=result.response_time if result.is_working else 0.0,
                best_speed_mbps=result.speed_mbps if result.is_working else 0.0,
                worst_speed_mbps=result.speed_mbps if result.is_working else float('inf'),
                reliability_rate=1.0 if result.is_working else 0.0
            )
        else:
            # Existing proxy - update statistics
            proxy = self.history[result.address]
            proxy.last_seen = now
            proxy.total_tests += 1
            
            if result.is_working:
                proxy.successful_tests += 1
                # Update average speed
                proxy.avg_speed_mbps = (
                    (proxy.avg_speed_mbps * (proxy.successful_tests - 1) + result.speed_mbps) 
                    / proxy.successful_tests
                )
                # Update average response time
                proxy.avg_response_time = (
                    (proxy.avg_response_time * (proxy.successful_tests - 1) + result.response_time) 
                    / proxy.successful_tests
                )
                # Update best/worst speeds
                proxy.best_speed_mbps = max(proxy.best_speed_mbps, result.speed_mbps)
                proxy.worst_speed_mbps = min(proxy.worst_speed_mbps, result.speed_mbps)
            
            # Update reliability rate
            proxy.reliability_rate = proxy.successful_tests / proxy.total_tests
        
        # Calculate long-term performance score
        if result.address in self.history:
            proxy = self.history[result.address]
            if proxy.successful_tests > 0:
                # Normalize speed (0-100 scale)
                speed_score = min(100, (proxy.avg_speed_mbps / 50) * 100)  # 50 Mbps = 100 score
                # Normalize latency (0-100 scale, lower is better)
                latency_score = max(0, 100 - (proxy.avg_response_time * 50))  # 2s = 0 score
                # Combine with reliability
                proxy.long_term_score = (
                    (speed_score * SPEED_WEIGHT + latency_score * LATENCY_WEIGHT) * 
                    proxy.reliability_rate
                )
    
    def get_sorted_proxies(self) -> List[ProxyHistory]:
        """Get proxies sorted by long-term performance score"""
        return sorted(
            [proxy for proxy in self.history.values() if proxy.successful_tests > 0],
            key=lambda x: x.long_term_score,
            reverse=True
        )

def load_proxies() -> List[Proxy]:
    """Load proxies from text files"""
    proxies: List[Proxy] = []
    proxy_files = {"http": "http.txt", "socks4": "socks4.txt", "socks5": "socks5.txt"}
    
    for proto, filename in proxy_files.items():
        path = Path(filename)
        if not path.exists():
            print(f"Warning: {filename} not found")
            continue
        try:
            for line in path.read_text().splitlines():
                if line.strip():
                    proxies.append(Proxy(proto, line))
            print(f"Loaded {len([p for p in proxies if p.protocol == proto])} {proto} proxies")
        except Exception as e:
            print(f"Error loading {filename}: {e}")
    
    return proxies

async def test_proxy(proxy: Proxy) -> Optional[ProxyResult]:
    """Test a single proxy with proper httpx configuration"""
    result = ProxyResult(protocol=proxy.protocol, address=proxy.address)
    
    # Configure proxy settings for httpx
    proxy_settings = {
        "http://": proxy.link,
        "https://": proxy.link,
    }
    
    try:
        # Create client with proxy configuration
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        timeout = httpx.Timeout(QUICK_TIMEOUT + SPEED_TIMEOUT, connect=5.0)
        
        async with httpx.AsyncClient(
            proxies=proxy_settings,
            limits=limits,
            timeout=timeout,
            follow_redirects=False
        ) as client:
            # Quick connectivity test
            start_time = time.time()
            resp = await client.get("https://httpbin.org/ip")
            
            if resp.status_code == 200:
                # If connectivity works, do speed test
                speed_start = time.time()
                speed_resp = await client.get(SPEED_TEST_URL)
                
                if speed_resp.status_code == 200:
                    content_length = len(speed_resp.content)
                    speed_time = time.time() - speed_start
                    
                    if content_length > 0 and speed_time > 0:
                        speed_mbps = (content_length * 8) / (speed_time * 1_000_000)
                        result.is_working = True
                        result.response_time = time.time() - start_time
                        result.speed_mbps = speed_mbps
                        
                        # Calculate performance score
                        speed_score = min(100, (speed_mbps / 50) * 100)
                        latency_score = max(0, 100 - (result.response_time * 50))
                        result.performance_score = speed_score * SPEED_WEIGHT + latency_score * LATENCY_WEIGHT
                    else:
                        result.error = "Invalid speed test response"
                else:
                    result.error = f"Speed test failed: HTTP {speed_resp.status_code}"
            else:
                result.error = f"Connectivity failed: HTTP {resp.status_code}"
                
    except Exception as e:
        result.error = f"Error: {str(e)}"
    
    return result

async def run_fixed_checker(workers: int = 200):
    """Run the fixed proxy checker"""
    console = Console()
    proxies = load_proxies()
    
    if not proxies:
        console.print("[red]No proxy files found! Run getproxy.py first.[/red]")
        return
    
    console.print(f"[green]Loaded {len(proxies):,} total proxies to test[/green]")
    console.print(f"[green]Using {workers} concurrent workers[/green]")
    console.print(f"[green]Quick timeout: {QUICK_TIMEOUT}s, Speed timeout: {SPEED_TIMEOUT}s[/green]")
    
    # Initialize proxy database
    db = ProxyDatabase()
    console.print(f"[green]Loaded {len(db.history)} proxies from history[/green]")
    
    # Shuffle proxies for better distribution
    random.shuffle(proxies)
    
    results: List[ProxyResult] = []
    semaphore = asyncio.Semaphore(workers)
    start_time = time.time()
    
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
                result = await test_proxy(proxy)
                if result:
                    # Update database
                    db.update_proxy(result)
                    if result.is_working:
                        results.append(result)
                
                # Update progress
                elapsed = time.time() - start_time
                rate = progress.tasks[0].completed / max(elapsed, 1e-6)
                progress.update(task, advance=1, rate=rate)
        
        await asyncio.gather(*(bound_check(p) for p in proxies))
    
    # Save updated history
    db.save_history()
    
    # Get sorted proxies by long-term performance
    sorted_proxies = db.get_sorted_proxies()
    
    # Display results
    display_fixed_results(results, sorted_proxies, console, start_time)
    
    # Save results
    save_fixed_results(results, sorted_proxies)

def display_fixed_results(results: List[ProxyResult], sorted_proxies: List[ProxyHistory], console: Console, start_time: float):
    """Display results in a nice table"""
    total_time = time.time() - start_time
    console.print(f"\n[green]Found {len(results)} working proxies in {total_time:.1f}s[/green]")
    console.print(f"[green]Total proxies in history: {len(sorted_proxies)}[/green]")
    
    if not sorted_proxies:
        return
    
    # Create table for top performers
    table = Table(title="Top 20 Long-term Performers")
    table.add_column("Rank", style="cyan")
    table.add_column("Protocol", style="magenta")
    table.add_column("Address", style="green")
    table.add_column("Long-term Score", style="yellow")
    table.add_column("Avg Speed (Mbps)", style="blue")
    table.add_column("Avg Latency (s)", style="red")
    table.add_column("Reliability", style="green")
    table.add_column("Tests", style="cyan")
    
    for i, proxy in enumerate(sorted_proxies[:20], 1):
        table.add_row(
            str(i),
            proxy.protocol.upper(),
            proxy.address,
            f"{proxy.long_term_score:.1f}",
            f"{proxy.avg_speed_mbps:.2f}",
            f"{proxy.avg_response_time:.3f}",
            f"{proxy.reliability_rate:.1%}",
            str(proxy.total_tests)
        )
    
    console.print(table)
    
    # Summary statistics
    if sorted_proxies:
        avg_score = sum(p.long_term_score for p in sorted_proxies) / len(sorted_proxies)
        avg_speed = sum(p.avg_speed_mbps for p in sorted_proxies) / len(sorted_proxies)
        avg_reliability = sum(p.reliability_rate for p in sorted_proxies) / len(sorted_proxies)
        
        console.print(f"\n[cyan]Summary:[/cyan]")
        console.print(f"  Working proxies: {len(sorted_proxies):,}")
        console.print(f"  Average Long-term Score: {avg_score:.1f}")
        console.print(f"  Average Speed: {avg_speed:.2f} Mbps")
        console.print(f"  Average Reliability: {avg_reliability:.1%}")
        console.print(f"  Processing rate: {len(results)/total_time:.1f} proxies/second")

def save_fixed_results(results: List[ProxyResult], sorted_proxies: List[ProxyHistory]):
    """Save results to CSV and text files"""
    if not sorted_proxies:
        return
    
    # Save comprehensive CSV with all proxy data
    csv_filename = "fixed_checked_proxies.csv"
    with open(csv_filename, 'w', newline='') as csvfile:
        fieldnames = [
            'Address', 'Protocol', 'Long_term_Score', 'Avg_Speed_Mbps', 'Avg_Response_Time_s',
            'Best_Speed_Mbps', 'Worst_Speed_Mbps', 'Reliability_Rate', 'Total_Tests',
            'Successful_Tests', 'First_Seen', 'Last_Seen'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for proxy in sorted_proxies:
            writer.writerow({
                'Address': proxy.address,
                'Protocol': proxy.protocol,
                'Long_term_Score': f"{proxy.long_term_score:.2f}",
                'Avg_Speed_Mbps': f"{proxy.avg_speed_mbps:.2f}",
                'Avg_Response_Time_s': f"{proxy.avg_response_time:.3f}",
                'Best_Speed_Mbps': f"{proxy.best_speed_mbps:.2f}",
                'Worst_Speed_Mbps': f"{proxy.worst_speed_mbps:.2f}",
                'Reliability_Rate': f"{proxy.reliability_rate:.3f}",
                'Total_Tests': proxy.total_tests,
                'Successful_Tests': proxy.successful_tests,
                'First_Seen': proxy.first_seen,
                'Last_Seen': proxy.last_seen
            })
    
    # Save top proxies by protocol to separate files
    for protocol in ['http', 'socks4', 'socks5']:
        protocol_proxies = [p for p in sorted_proxies if p.protocol == protocol]
        if protocol_proxies:
            filename = f"{protocol}_fixed_checked.txt"
            with open(filename, 'w') as f:
                for proxy in protocol_proxies[:200]:
                    f.write(f"{proxy.address}\n")
    
    # Save all working proxies in single file (sorted by long-term score)
    with open("all_working_proxies.txt", 'w') as f:
        for proxy in sorted_proxies:
            f.write(f"{proxy.address}\n")
    
    print(f"\n[green]Results saved to:[/green]")
    print(f"  • {csv_filename} (comprehensive CSV with history)")
    print(f"  • all_working_proxies.txt (all proxies sorted by long-term score)")
    print(f"  • http_fixed_checked.txt (top 200 HTTP proxies)")
    print(f"  • socks4_fixed_checked.txt (top 200 SOCKS4 proxies)")
    print(f"  • socks5_fixed_checked.txt (top 200 SOCKS5 proxies)")
    print(f"  • proxy_history.json (performance history database)")

if __name__ == "__main__":
    import sys
    
    workers = 200
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        workers = int(sys.argv[1])
    
    workers = min(workers, MAX_WORKERS)  # Cap at reasonable limit
    print(f"Fixed Proxy Checker for Megabasterd")
    print(f"Workers: {workers}")
    print(f"Quick timeout: {QUICK_TIMEOUT}s")
    print(f"Speed test timeout: {SPEED_TIMEOUT}s")
    print(f"Speed test URL: {SPEED_TEST_URL}")
    print(f"Performance weights: Speed {SPEED_WEIGHT}, Latency {LATENCY_WEIGHT}")
    
    asyncio.run(run_fixed_checker(workers))


# Proxy Master

A comprehensive proxy management system that scrapes, validates, and benchmarks free proxies for optimal performance with tools like MegaBasterd.

## Features

- **Proxy Scraping**: Automatically collects proxies from multiple sources (HTTP, SOCKS4, SOCKS5)
- **Proxy Benchmarking**: Tests proxy speed, latency, and reliability
- **Automated Pipeline**: GitHub Actions workflow for continuous proxy updates
- **Performance Tracking**: Historical performance data and scoring system
- **Multiple Output Formats**: CSV reports, ranked lists, and rotation files

## Quick Start

### Prerequisites

```bash
pip install -r requirements.txt
```

### Manual Usage

1. **Scrape proxies only:**
   ```bash
   python getproxy.py
   ```

2. **Benchmark proxies only:**
   ```bash
   python proxy_benchmark.py
   ```

3. **Run complete pipeline:**
   ```bash
   python run_proxy_pipeline.py
   ```

## File Structure

```
Proxy-Master/
├── getproxy.py              # Proxy scraping script
├── proxy_benchmark.py       # Proxy testing and benchmarking
├── run_proxy_pipeline.py    # Combined pipeline runner
├── requirements.txt          # Python dependencies
├── .github/workflows/       # GitHub Actions automation
├── http.txt                 # HTTP proxies (generated)
├── socks4.txt              # SOCKS4 proxies (generated)
├── socks5.txt              # SOCKS5 proxies (generated)
├── proxy_benchmark_results.csv  # Benchmark results
├── TopProxies.txt          # Top 150 performing proxies
├── RotationList.txt        # All proxies ranked by performance
├── working-fast.txt        # Fast working proxies
├── FailedProxies.txt       # Consistently failing proxies
├── RespondedProxies.txt    # Proxies that have responded at least once
└── proxy_history.csv       # Historical performance data
```

## GitHub Actions Automation

The repository includes automated workflows that:

- **Schedule**: Run every 6 hours automatically
- **Manual Trigger**: Allow manual execution with options:
  - `full`: Complete pipeline (scrape + benchmark)
  - `scrape_only`: Just collect new proxies
  - `benchmark_only`: Just test existing proxies
- **Artifacts**: Upload results as downloadable artifacts
- **Auto-commit**: Commit results back to the repository

### Workflow Triggers

- **Automatic**: Every 6 hours via cron schedule
- **Manual**: Via GitHub Actions UI with custom parameters
- **Push**: On every push to main branch

## Configuration

### Proxy Benchmark Settings

Edit `proxy_benchmark.py` to customize:

```python
TIMEOUT             = 10                  # seconds
CONCURRENT_LIMIT    = 200                 # max simultaneous tasks
TOP_N_COUNT         = 150                 # number of top proxies to select
HISTORY_MAX_RUNS    = 10                  # keep last N runs per proxy
MIN_TESTS_FOR_FAIL  = 3                   # threshold for failure marking
```

### Test URL and Range

```python
TEST_URL            = "http://ipv4.download.thinkbroadband.com/100MB.zip"
CHUNK_RANGE         = "bytes=0-10485759"  # first 10 MB
```

## Output Files

### Core Proxy Files
- `http.txt`, `socks4.txt`, `socks5.txt`: Raw proxy lists by protocol

### Benchmark Results
- `proxy_benchmark_results.csv`: Detailed performance metrics
- `TopProxies.txt`: Top 150 proxies formatted for MegaBasterd
- `RotationList.txt`: All proxies ranked by performance
- `working-fast.txt`: Fast working proxies
- `FailedProxies.txt`: Consistently failing proxies
- `RespondedProxies.txt`: Proxies that have responded at least once

### Historical Data
- `proxy_history.csv`: Performance history for trend analysis

## MegaBasterd Integration

The `TopProxies.txt` file is specifically formatted for MegaBasterd:

```
http://proxy1:port1
socks5://proxy2:port2
socks4://proxy3:port3
```

## Performance Metrics

Each proxy is scored based on:
- **Speed**: MB/s download rate
- **Latency**: Response time in seconds
- **Score**: Speed / (Latency + 0.01)
- **Response Rate**: Percentage of successful tests
- **Long-term Performance**: Historical average scores

## Troubleshooting

### Common Issues

1. **No proxies found**: Ensure `getproxy.py` runs first
2. **Benchmark failures**: Check internet connection and firewall settings
3. **GitHub Actions errors**: Verify repository permissions and workflow syntax

### Dependencies

Core requirements:
- `requests`: HTTP requests for proxy scraping
- `aiohttp`: Async HTTP client for benchmarking
- `tqdm`: Progress bars for long operations
- `asyncio`: Async/await support

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Proxy sources: Various free proxy list providers
- MegaBasterd: The target application for proxy optimization
- Open source community: For the libraries and tools used

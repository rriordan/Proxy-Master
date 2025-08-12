# Proxy Master Configuration
# Edit these settings to customize the proxy pipeline behavior

# Proxy Benchmark Settings
BENCHMARK_CONFIG = {
    # Test configuration
    'TEST_URL': "http://ipv4.download.thinkbroadband.com/100MB.zip",
    'CHUNK_RANGE': "bytes=0-10485759",  # first 10 MB
    'TIMEOUT': 10,                       # seconds
    
    # Performance settings
    'CONCURRENT_LIMIT': 512,             # max simultaneous tasks (updated)
    'HISTORY_MAX_RUNS': 10,              # keep last N runs per proxy
    'MIN_TESTS_FOR_FAIL': 3,             # threshold to consider continuous failures
    
    # Pre-screening settings
    'PRE_SCREEN_URL': "http://httpbin.org/ip",
    'PRE_SCREEN_TIMEOUT': 5,             # seconds
    'PRE_SCREEN_CONCURRENT': 512,        # concurrent limit for pre-screening
}

# File naming configuration
FILE_CONFIG = {
    # Input files (from getproxy.py)
    'HTTP_FILE': "http.txt",
    'SOCKS4_FILE': "socks4.txt", 
    'SOCKS5_FILE': "socks5.txt",
    
    # Output directory
    'OUTPUT_DIR': "Output",
    
    # Output files (in Output/ folder)
    'RESULTS_CSV': "proxy_benchmark_results.csv",
    'MB_PROXIES': "MBProxies.txt",
    'HISTORY_FILE': "proxy_history.csv",
}

# GitHub Actions configuration
GITHUB_CONFIG = {
    'SCHEDULE_MINUTES': 30,              # Run every N minutes (updated)
    'ARTIFACT_RETENTION_DAYS': 7,        # Keep artifacts for N days
    'AUTO_COMMIT': True,                 # Auto-commit results
}

# Performance thresholds (updated to match script)
PERFORMANCE_THRESHOLDS = {
    'MIN_SCORE_THRESHOLD': 0,         # Minimum score to be considered "good"
    'MIN_RESPONSE_RATE': 0,           # Minimum response rate percentage
    'MIN_PROXIES_COUNT': 75,             # Minimum number of proxies to include
}

# Logging configuration
LOGGING_CONFIG = {
    'LOG_LEVEL': 'INFO',                  # DEBUG, INFO, WARNING, ERROR
    'CONSOLE_OUTPUT': True,               # Show output in console
}

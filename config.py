# Proxy Master Configuration
# Edit these settings to customize the proxy pipeline behavior

# Proxy Benchmark Settings
BENCHMARK_CONFIG = {
    # Test configuration
    'TEST_URL': "http://ipv4.download.thinkbroadband.com/100MB.zip",
    'CHUNK_RANGE': "bytes=0-10485759",  # first 10 MB
    'TIMEOUT': 10,                       # seconds
    
    # Performance settings
    'CONCURRENT_LIMIT': 200,             # max simultaneous tasks
    'TOP_N_COUNT': 150,                  # number of top proxies to select
    
    # History and tracking
    'HISTORY_MAX_RUNS': 10,              # keep last N runs per proxy
    'MIN_TESTS_FOR_FAIL': 3,             # threshold to consider continuous failures
}

# File naming configuration
FILE_CONFIG = {
    # Input files (from getproxy.py)
    'HTTP_FILE': "http.txt",
    'SOCKS4_FILE': "socks4.txt", 
    'SOCKS5_FILE': "socks5.txt",
    
    # Output files
    'RESULTS_CSV': "proxy_benchmark_results.csv",
    'TOP_PROXIES': "TopProxies.txt",
    'ROTATION_LIST': "RotationList.txt",
    'WORKING_FAST': "working-fast.txt",
    'FAILED_PROXIES': "FailedProxies.txt",
    'RESPONDED_PROXIES': "RespondedProxies.txt",
    'HISTORY_FILE': "proxy_history.csv",
}

# GitHub Actions configuration
GITHUB_CONFIG = {
    'SCHEDULE_HOURS': 6,                 # Run every N hours
    'ARTIFACT_RETENTION_DAYS': 7,        # Keep artifacts for N days
    'AUTO_COMMIT': True,                 # Auto-commit results
}

# Proxy source priorities (for getproxy.py)
PROXY_SOURCE_PRIORITY = {
    'http': ['proxyscrape', 'proxy-list.download', 'openproxylist.xyz'],
    'socks4': ['proxyscrape', 'proxy-list.download', 'openproxylist.xyz'],
    'socks5': ['proxyscrape', 'proxy-list.download', 'openproxylist.xyz']
}

# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    'MIN_SPEED_MBPS': 0.1,              # Minimum acceptable speed
    'MAX_LATENCY_SEC': 30.0,             # Maximum acceptable latency
    'MIN_SUCCESS_RATE': 50.0,            # Minimum success rate percentage
}

# Logging configuration
LOGGING_CONFIG = {
    'LOG_LEVEL': 'INFO',                  # DEBUG, INFO, WARNING, ERROR
    'LOG_FILE': 'proxy_pipeline.log',     # Log file name
    'CONSOLE_OUTPUT': True,               # Show output in console
    'SAVE_LOGS': True,                    # Save logs to file
}

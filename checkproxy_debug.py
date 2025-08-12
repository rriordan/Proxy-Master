import asyncio
import httpx
import time

async def test_single_proxy():
    """Test a single proxy to debug the issue"""
    proxy_address = "1.0.171.213:8080"  # First proxy from the list
    proxy_link = f"http://{proxy_address}"
    
    print(f"Testing proxy: {proxy_address}")
    print(f"Proxy link: {proxy_link}")
    
    # Configure proxy settings
    proxy_settings = {
        "http://": proxy_link,
        "https://": proxy_link,
    }
    
    print(f"Proxy settings: {proxy_settings}")
    
    try:
        # Configure httpx client
        limits = httpx.Limits(max_keepalive_connections=100, max_connections=1000)
        timeout = httpx.Timeout(30.0, connect=10.0)
        
        async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
            print("Testing connectivity...")
            
            # Test connectivity
            start_time = time.time()
            resp = await client.get(
                "https://httpbin.org/ip",
                proxies=proxy_settings,
                timeout=3.0,
                follow_redirects=False
            )
            print(f"Connectivity response status: {resp.status_code}")
            print(f"Connectivity response time: {time.time() - start_time:.2f}s")
            
            if resp.status_code == 200:
                print("Connectivity test passed!")
                print(f"Response content: {resp.text[:200]}...")
                
                # Test speed
                print("Testing speed...")
                speed_start = time.time()
                speed_resp = await client.get(
                    "https://httpbin.org/bytes/25600",
                    proxies=proxy_settings,
                    timeout=8.0,
                    follow_redirects=False
                )
                print(f"Speed response status: {speed_resp.status_code}")
                
                if speed_resp.status_code == 200:
                    content_length = len(speed_resp.content)
                    speed_time = time.time() - speed_start
                    print(f"Speed test passed!")
                    print(f"Content length: {content_length} bytes")
                    print(f"Speed test time: {speed_time:.2f}s")
                    
                    if content_length > 0 and speed_time > 0:
                        speed_mbps = (content_length * 8) / (speed_time * 1_000_000)
                        print(f"Speed: {speed_mbps:.2f} Mbps")
                    else:
                        print("Invalid speed test response")
                else:
                    print(f"Speed test failed: HTTP {speed_resp.status_code}")
            else:
                print(f"Connectivity test failed: HTTP {resp.status_code}")
                
    except Exception as e:
        print(f"Error testing proxy: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Debug Proxy Tester")
    print("=" * 50)
    asyncio.run(test_single_proxy())

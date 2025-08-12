import asyncio
import httpx
import time

async def test_proxy_manual(proxy_address: str, protocol: str = "http"):
    """Manually test a single proxy"""
    proxy_link = f"{protocol}://{proxy_address}"
    
    print(f"Testing {protocol.upper()} proxy: {proxy_address}")
    print(f"Proxy link: {proxy_link}")
    
    proxy_settings = {
        "http://": proxy_link,
        "https://": proxy_link,
    }
    
    try:
        # Create client with proxy configuration
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        timeout = httpx.Timeout(10.0, connect=5.0)
        
        async with httpx.AsyncClient(
            proxies=proxy_settings,
            limits=limits,
            timeout=timeout,
            follow_redirects=False
        ) as client:
            print("Testing connectivity...")
            start_time = time.time()
            
            resp = await client.get("https://httpbin.org/ip")
            print(f"Response status: {resp.status_code}")
            print(f"Response time: {time.time() - start_time:.2f}s")
            
            if resp.status_code == 200:
                print("✅ Connectivity test PASSED!")
                print(f"Response: {resp.text[:200]}...")
                
                # Test speed
                print("Testing speed...")
                speed_start = time.time()
                speed_resp = await client.get("https://httpbin.org/bytes/25600")
                
                if speed_resp.status_code == 200:
                    content_length = len(speed_resp.content)
                    speed_time = time.time() - speed_start
                    speed_mbps = (content_length * 8) / (speed_time * 1_000_000)
                    
                    print(f"✅ Speed test PASSED!")
                    print(f"Speed: {speed_mbps:.2f} Mbps")
                    print(f"Content length: {content_length} bytes")
                    print(f"Speed test time: {speed_time:.2f}s")
                    return True
                else:
                    print(f"❌ Speed test failed: HTTP {speed_resp.status_code}")
            else:
                print(f"❌ Connectivity test failed: HTTP {resp.status_code}")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    return False

async def test_multiple_proxies():
    """Test multiple proxies from the list"""
    # Test first few proxies from each file
    test_proxies = [
        ("1.0.171.213:8080", "http"),
        ("1.1.189.58:8080", "http"),
        ("1.1.220.100:8080", "http"),
        ("1.10.194.178:8080", "http"),
        ("1.117.233.135:443", "http"),
    ]
    
    working_count = 0
    total_count = len(test_proxies)
    
    for proxy_address, protocol in test_proxies:
        print("\n" + "="*60)
        if await test_proxy_manual(proxy_address, protocol):
            working_count += 1
        print("="*60)
    
    print(f"\n📊 Results: {working_count}/{total_count} proxies working ({working_count/total_count*100:.1f}%)")

if __name__ == "__main__":
    print("Manual Proxy Tester")
    print("Testing first 5 HTTP proxies from the list...")
    asyncio.run(test_multiple_proxies())


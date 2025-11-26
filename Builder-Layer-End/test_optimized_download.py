"""
Test optimized image download with all strategies enabled
"""
import sys
import json
import asyncio
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.analytics.cv_analysis_agent import CVAnalysisAgent

async def test_optimized_download():
    """Test the optimized image downloader"""
    
    print("=" * 100)
    print("🚀 TESTING OPTIMIZED IMAGE DOWNLOAD")
    print("=" * 100)
    print()
    
    # Load config to show optimization settings
    import yaml
    with open('config/cv_config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    cv_config = config.get('cv_analysis', {})
    conn_config = cv_config.get('connection', {})
    cache_config = cv_config.get('cache', {})
    
    print("📋 OPTIMIZATION SETTINGS:")
    print("-" * 100)
    print(f"  Batch Size: {cv_config.get('batch_size', 'N/A')}")
    print(f"  Timeout: {cv_config.get('timeout', 'N/A')}s")
    print(f"  Max Retries: {cv_config.get('max_retries', 'N/A')}")
    print(f"  Retry Delay: {cv_config.get('retry_delay', 'N/A')}s")
    print()
    print("  🔌 Connection Optimization:")
    print(f"    - Pool Size: {conn_config.get('pool_size', 'N/A')}")
    print(f"    - Keepalive Timeout: {conn_config.get('keepalive_timeout', 'N/A')}s")
    print(f"    - DNS Cache TTL: {conn_config.get('dns_cache_ttl', 'N/A')}s")
    print(f"    - Exponential Backoff: {conn_config.get('exponential_backoff', 'N/A')}")
    print(f"    - Backoff Factor: {conn_config.get('backoff_factor', 'N/A')}")
    print(f"    - Browser Headers: {conn_config.get('use_browser_headers', 'N/A')}")
    print()
    print("  💾 Cache Settings:")
    print(f"    - Enabled: {cache_config.get('enabled', 'N/A')}")
    print(f"    - Directory: {cache_config.get('directory', 'N/A')}")
    print(f"    - TTL: {cache_config.get('ttl_minutes', 'N/A')} minutes")
    print(f"    - Max Size: {cache_config.get('max_size_mb', 'N/A')} MB")
    print()
    print("=" * 100)
    print()
    
    # Load cameras
    try:
        with open('data/cameras_updated.json', 'r', encoding='utf-8') as f:
            cameras = json.load(f)
        
        if not cameras:
            print("❌ No cameras found!")
            return
        
        # Test with first 3 cameras only
        test_cameras = cameras[:3]
        print(f"📹 Testing with {len(test_cameras)} cameras:")
        for i, cam in enumerate(test_cameras, 1):
            print(f"  {i}. {cam.get('id')}: {cam.get('name')}")
        print()
        print("=" * 100)
        print()
        
        # Initialize agent
        print("🔧 Initializing CV Analysis Agent...")
        agent = CVAnalysisAgent('config/cv_config.yaml')
        print("✅ Agent initialized successfully")
        print()
        
        # Test download
        print("📥 Starting optimized download test...")
        print("-" * 100)
        start_time = time.time()
        
        # Prepare URLs
        urls = [
            (cam['id'], cam.get('image_url_x4', cam.get('imageSnapshot', '')))
            for cam in test_cameras
        ]
        
        # Download
        images = await agent.downloader.download_batch(urls)
        
        elapsed = time.time() - start_time
        
        print()
        print("=" * 100)
        print("📊 RESULTS:")
        print("-" * 100)
        
        success_count = sum(1 for img in images.values() if img is not None)
        fail_count = len(images) - success_count
        
        print(f"  Total Cameras: {len(test_cameras)}")
        print(f"  ✅ Successful: {success_count} ({success_count/len(test_cameras)*100:.1f}%)")
        print(f"  ❌ Failed: {fail_count} ({fail_count/len(test_cameras)*100:.1f}%)")
        print(f"  ⏱️  Total Time: {elapsed:.2f}s")
        print(f"  ⚡ Average Time: {elapsed/len(test_cameras):.2f}s per image")
        print()
        
        # Show individual results
        print("  📋 Individual Results:")
        for camera_id, image in images.items():
            if image:
                print(f"    ✅ {camera_id}: {image.size} pixels, mode: {image.mode}")
            else:
                print(f"    ❌ {camera_id}: Failed")
        print()
        
        # Cache statistics
        if cache_config.get('enabled'):
            cache_dir = Path(cache_config.get('directory', 'data/cache/images'))
            if cache_dir.exists():
                cache_files = list(cache_dir.glob('*.jpg'))
                cache_size_mb = sum(f.stat().st_size for f in cache_files) / (1024 * 1024)
                print(f"  💾 Cache Statistics:")
                print(f"    - Files: {len(cache_files)}")
                print(f"    - Size: {cache_size_mb:.2f} MB")
                print()
        
        print("=" * 100)
        
        if success_count > 0:
            print("🎉 SUCCESS! Optimization strategies are working!")
            print()
            print("💡 Next steps:")
            print("  1. Run full pipeline: python orchestrator.py")
            print("  2. Monitor cache hits in logs")
            print("  3. Check observations.json for results")
        else:
            print("⚠️  WARNING! All downloads failed.")
            print()
            print("💡 Possible causes:")
            print("  1. Server is completely down")
            print("  2. Network connectivity issues")
            print("  3. URLs are invalid or expired")
            print("  4. Firewall/proxy blocking requests")
            print()
            print("💡 Try:")
            print("  1. Test URL in browser first")
            print("  2. Check network connection")
            print("  3. Run: python test_image_download.py")
        
        print("=" * 100)
        
    except FileNotFoundError:
        print("❌ File not found: data/cameras_updated.json")
        print("   Please run image_refresh_agent first!")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_optimized_download())

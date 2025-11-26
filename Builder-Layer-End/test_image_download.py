"""
Test if we can download images from the government server
"""
import asyncio
import aiohttp
import io
from PIL import Image
import time

async def test_download(url: str, timeout: int = 120):
    """Test downloading an image from URL"""
    print(f"🔍 Testing URL: {url[:80]}...")
    print(f"⏱️  Timeout set to: {timeout}s")
    print(f"🚀 Starting download...")
    
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as response:
                elapsed = time.time() - start_time
                
                print(f"📡 Response status: {response.status}")
                print(f"⏰ Response received in: {elapsed:.2f}s")
                
                if response.status == 200:
                    print(f"📥 Reading image data...")
                    image_data = await response.read()
                    download_time = time.time() - start_time
                    
                    print(f"✅ Downloaded {len(image_data)} bytes in {download_time:.2f}s")
                    
                    # Try to open as image
                    image = Image.open(io.BytesIO(image_data))
                    print(f"🖼️  Image opened successfully: {image.size} pixels, mode: {image.mode}")
                    
                    # Save test image
                    test_path = "test_downloaded_image.jpg"
                    image.save(test_path)
                    print(f"💾 Saved test image to: {test_path}")
                    
                    return True
                else:
                    print(f"❌ HTTP Error: {response.status}")
                    return False
                    
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        print(f"⏰ TIMEOUT after {elapsed:.2f}s")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ ERROR after {elapsed:.2f}s: {type(e).__name__}: {e}")
        return False

async def main():
    # Test với URL từ hình ảnh của bạn
    # URL pattern: giaothong.hochiminhcity.gov.vn/render/ImageHandler.ashx?id=...&zoom=...
    
    # Đọc một URL thực từ cameras_updated.json để test
    import json
    
    print("=" * 80)
    print("🧪 IMAGE DOWNLOAD TEST")
    print("=" * 80)
    
    try:
        with open('data/cameras_updated.json', 'r', encoding='utf-8') as f:
            cameras = json.load(f)
        
        if cameras:
            # Test camera đầu tiên
            camera = cameras[0]
            camera_id = camera.get('id', 'unknown')
            url = camera.get('image_url_x4', '')
            
            print(f"\n📹 Camera: {camera_id}")
            print(f"🔗 URL: {url}")
            print()
            
            if url:
                success = await test_download(url, timeout=120)
                
                print()
                print("=" * 80)
                if success:
                    print("✅ RESULT: Image download SUCCESSFUL!")
                    print("💡 The code CAN download images from this URL")
                else:
                    print("❌ RESULT: Image download FAILED!")
                    print("💡 The code CANNOT download images from this URL")
                    print("   Possible reasons:")
                    print("   - Server is slow/unresponsive")
                    print("   - Network connectivity issues")
                    print("   - URL expired or invalid")
                print("=" * 80)
            else:
                print("❌ No URL found in camera data!")
        else:
            print("❌ No cameras found in cameras_updated.json!")
            
    except FileNotFoundError:
        print("❌ File not found: data/cameras_updated.json")
        print("   Please run image_refresh_agent first!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

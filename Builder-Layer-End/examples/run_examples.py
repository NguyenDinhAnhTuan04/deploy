"""
Example: Running Image Refresh Agent

This script demonstrates how to use the Image Refresh Agent
for different domains without any code changes.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.data_collection.image_refresh_agent import ImageRefreshAgent


async def example_1_cameras():
    """Example 1: Refresh traffic camera images (geography domain)."""
    print("=" * 60)
    print("EXAMPLE 1: Traffic Cameras (Geography Domain)")
    print("=" * 60)
    
    agent = ImageRefreshAgent(
        config_path="config/data_sources.yaml",
        domain="cameras"
    )
    
    await agent.run_once()
    print("\n✅ Camera images refreshed successfully!")


async def example_2_healthcare():
    """Example 2: Refresh medical device endpoints (healthcare domain)."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Medical Devices (Healthcare Domain)")
    print("=" * 60)
    
    # First, you would add this to config/data_sources.yaml:
    # medical_devices:
    #   source_file: "data/devices_raw.json"
    #   output_file: "data/devices_updated.json"
    #   ...
    
    print("To run this example:")
    print("1. Add 'medical_devices' section to config/data_sources.yaml")
    print("2. Create data/devices_raw.json with device endpoints")
    print("3. Run: python examples/run_examples.py --example healthcare")
    
    # Uncomment when config is ready:
    # agent = ImageRefreshAgent(
    #     config_path="config/data_sources.yaml",
    #     domain="medical_devices"
    # )
    # await agent.run_once()


async def example_3_commerce():
    """Example 3: Refresh product inventory images (commerce domain)."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Product Inventory (Commerce Domain)")
    print("=" * 60)
    
    print("To run this example:")
    print("1. Add 'inventory_images' section to config/data_sources.yaml")
    print("2. Create data/inventory_raw.json with product image URLs")
    print("3. Run: python examples/run_examples.py --example commerce")


async def main():
    """Run all examples."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Image Refresh Agent Examples")
    parser.add_argument(
        "--example",
        choices=["cameras", "healthcare", "commerce", "all"],
        default="cameras",
        help="Which example to run"
    )
    
    args = parser.parse_args()
    
    if args.example == "cameras" or args.example == "all":
        await example_1_cameras()
    
    if args.example == "healthcare" or args.example == "all":
        await example_2_healthcare()
    
    if args.example == "commerce" or args.example == "all":
        await example_3_commerce()


if __name__ == "__main__":
    asyncio.run(main())

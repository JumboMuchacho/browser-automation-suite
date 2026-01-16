#!/usr/bin/env python3
"""
Cleanup script to remove old profile directories and prepare for fresh automation profiles.
"""

import os
import shutil
import sys

def cleanup_old_profiles():
    """Remove old profile directories and prepare for fresh automation"""
    print("🧹 Cleaning up old profile directories...")
    
    # Directories to remove
    old_dirs = [
        "chrome_profile_copy",
        "automation_profile"
    ]
    
    for dir_name in old_dirs:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"✅ Removed old directory: {dir_name}")
            except Exception as e:
                print(f"⚠️ Failed to remove {dir_name}: {e}")
        else:
            print(f"ℹ️ Directory not found: {dir_name}")
    
    print("\n🎉 Cleanup complete!")
    print("📝 Next time you run the automation scripts, they will:")
    print("   - Create a fresh automation profile on first run")
    print("   - Persist any new data for reuse on subsequent runs")
    print("   - No longer copy your existing Chrome profiles")

if __name__ == "__main__":
    cleanup_old_profiles() 
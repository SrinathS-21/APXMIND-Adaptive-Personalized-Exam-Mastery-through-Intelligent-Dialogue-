#!/usr/bin/env python3
"""
Browser Profile Cleanup Script
Searches for and removes test browser profiles created by automation tools
"""
import os
import shutil
from pathlib import Path

# Common profile locations
CHROME_PROFILE_PATHS = [
    Path(os.environ.get('LOCALAPPDATA', '')) / 'Google' / 'Chrome' / 'User Data',
    Path(os.environ.get('APPDATA', '')) / 'Google' / 'Chrome' / 'User Data',
]

# Playwright profile locations
PLAYWRIGHT_PATHS = [
    Path.home() / 'AppData' / 'Local' / 'ms-playwright',
    Path('.') / 'playwright',
]

# Test profile name patterns
TEST_PATTERNS = [
    'smoke_',
    'postfix_',
    'allcheck_',
    'apitest_',
    'test_profile_',
    '_testing_profile_',
]


def find_test_profiles(base_path: Path):
    """Find all test profiles in the given directory"""
    if not base_path.exists():
        return []

    test_profiles = []
    try:
        for item in base_path.iterdir():
            if item.is_dir():
                name = item.name.lower()
                if any(pattern in name for pattern in TEST_PATTERNS):
                    test_profiles.append(item)
    except PermissionError:
        print(f"⚠️  Permission denied: {base_path}")

    return test_profiles


def get_dir_size(path: Path):
    """Calculate directory size in MB"""
    total = 0
    try:
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
    except (PermissionError, FileNotFoundError):
        pass
    return total / (1024 * 1024)  # Convert to MB


def main():
    print("=" * 70)
    print("Browser Profile Cleanup Tool")
    print("=" * 70)
    print()

    all_test_profiles = []

    # Search Chrome profiles
    print("🔍 Searching for Chrome test profiles...")
    for chrome_path in CHROME_PROFILE_PATHS:
        if chrome_path.exists():
            print(f"   Checking: {chrome_path}")
            profiles = find_test_profiles(chrome_path)
            all_test_profiles.extend(profiles)

    # Search Playwright profiles
    print("\n🔍 Searching for Playwright test profiles...")
    for playwright_path in PLAYWRIGHT_PATHS:
        if playwright_path.exists():
            print(f"   Checking: {playwright_path}")
            profiles = find_test_profiles(playwright_path)
            all_test_profiles.extend(profiles)

    # Search current project directory
    print("\n🔍 Searching current project...")
    project_profiles = find_test_profiles(Path('.'))
    all_test_profiles.extend(project_profiles)

    if not all_test_profiles:
        print("\n✅ No test profiles found!")
        return

    print(f"\n📊 Found {len(all_test_profiles)} test profile(s):")
    print("-" * 70)

    total_size = 0
    for i, profile in enumerate(all_test_profiles, 1):
        size = get_dir_size(profile)
        total_size += size
        print(f"{i:2}. {profile.name}")
        print(f"    Path: {profile}")
        print(f"    Size: {size:.2f} MB")
        print()

    print("-" * 70)
    print(f"💾 Total space to recover: {total_size:.2f} MB")
    print()

    # Confirm deletion
    response = input("❓ Do you want to delete these profiles? (yes/no): ").strip().lower()

    if response == 'yes':
        print("\n🗑️  Deleting profiles...")
        deleted_count = 0
        failed_count = 0

        for profile in all_test_profiles:
            try:
                print(f"   Deleting: {profile.name}...", end=" ")
                shutil.rmtree(profile, ignore_errors=False)
                print("✅")
                deleted_count += 1
            except Exception as e:
                print(f"❌ Failed: {e}")
                failed_count += 1

        print()
        print("=" * 70)
        print(f"✅ Successfully deleted: {deleted_count} profile(s)")
        if failed_count > 0:
            print(f"❌ Failed to delete: {failed_count} profile(s)")
        print(f"💾 Recovered approximately: {total_size:.2f} MB")
        print("=" * 70)
    else:
        print("\n❌ Cleanup cancelled.")


if __name__ == '__main__':
    main()

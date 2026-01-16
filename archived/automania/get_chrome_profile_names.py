#!/usr/bin/env python3
"""
Script to list all Chrome profile directories and their visible profile names (account names) on Linux.
"""
import os
import json

# Default Chrome user data directory for Linux
chrome_user_data_dir = os.path.expanduser('~/.config/google-chrome')

# Read Local State to get profile info
local_state_path = os.path.join(chrome_user_data_dir, 'Local State')
if not os.path.exists(local_state_path):
    print(f"Local State file not found at {local_state_path}")
    exit(1)

with open(local_state_path, 'r', encoding='utf-8') as f:
    local_state = json.load(f)

profiles = local_state.get('profile', {}).get('info_cache', {})

print("Profile directory : Profile name")
print("-------------------------------")
for profile_dir, info in profiles.items():
    name = info.get('name', profile_dir)
    print(f"{profile_dir} : {name}") 
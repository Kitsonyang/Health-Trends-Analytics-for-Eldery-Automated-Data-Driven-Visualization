#!/usr/bin/env python3
"""
Retrieve Power BI Workspace ID and Dataset ID.

Usage:
    cd backend
    python -m scripts.get_powerbi_ids

Prerequisites:
    - Configure PBI_TENANT_ID, PBI_CLIENT_ID, PBI_CLIENT_SECRET in .env
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import requests
from config import load_powerbi_config

def get_access_token(config):
    """Get Power BI access token"""
    url = f"https://login.microsoftonline.com/{config.tenant_id}/oauth2/v2.0/token"
    
    data = {
        'grant_type': 'client_credentials',
        'client_id': config.client_id,
        'client_secret': config.client_secret,
        'scope': 'https://analysis.windows.net/powerbi/api/.default'
    }
    
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()['access_token']


def list_workspaces(token):
    """List all workspaces"""
    url = "https://api.powerbi.com/v1.0/myorg/groups"
    headers = {'Authorization': f'Bearer {token}'}
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['value']


def list_datasets(token, workspace_id):
    """List all datasets in the specified workspace"""
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets"
    headers = {'Authorization': f'Bearer {token}'}
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['value']


def main():
    print("=" * 80)
    print("Power BI Workspace and Dataset ID Finder")
    print("=" * 80)
    print()
    
    try:
        # Load configuration
        print("Loading configuration...")
        config = load_powerbi_config()
        print(f"✅ Tenant ID: {config.tenant_id}")
        print(f"✅ Client ID: {config.client_id}")
        print()
        
        # Retrieve access token
        print("Retrieving access token...")
        token = get_access_token(config)
        print("✅ Token retrieved successfully")
        print()
        
        # List Workspaces
        print("Fetching workspaces...")
        workspaces = list_workspaces(token)
        print(f"✅ Found {len(workspaces)} workspace(s)")
        print()
        
        if not workspaces:
            print("Warning: No workspace found")
            return
        
        # Show workspaces
        print("-" * 80)
        for i, ws in enumerate(workspaces, 1):
            print(f"{i}. Workspace: {ws.get('name', 'Unnamed')}")
            print(f"   ID: {ws['id']}")
            print(f"   Type: {ws.get('type', 'Unknown')}")
            print()
        
        # Select workspace
        if len(workspaces) == 1:
            selected_ws = workspaces[0]
            print(f"Auto-selected the only Workspace: {selected_ws.get('name', 'Unnamed')}")
        else:
            while True:
                try:
                    choice = input(f"Please select a workspace (1-{len(workspaces)}): ").strip()
                    idx = int(choice) - 1
                    if 0 <= idx < len(workspaces):
                        selected_ws = workspaces[idx]
                        break
                    else:
                        print(f"Error: Please enter a number between 1 and {len(workspaces)}")
                except ValueError:
                    print("Error: Please enter a valid number")
        
        print()
        print("-" * 80)
        
        # List datasets
        workspace_id = selected_ws['id']
        print(f"Fetching datasets in workspace '{selected_ws.get('name', 'Unnamed')}'...")
        datasets = list_datasets(token, workspace_id)
        print(f"Found {len(datasets)} dataset(s)")
        print()
        
        if not datasets:
            print("Warning: No dataset found in this workspace")
            print()
            print("📋 Configuration:")
            print(f"PBI_WORKSPACE_ID={workspace_id}")
            return
        
        # Show datasets
        print("-" * 80)
        for i, ds in enumerate(datasets, 1):
            print(f"{i}. Dataset: {ds.get('name', 'Unnamed')}")
            print(f"   ID: {ds['id']}")
            print(f"   Configured By: {ds.get('configuredBy', 'Unknown')}")
            if ds.get('isRefreshable'):
                print("   Refreshable")
            else:
                print("   Not refreshable")
            print()
        
        # Select dataset
        if len(datasets) == 1:
            selected_ds = datasets[0]
            print(f"Auto-selected the only Dataset: {selected_ds.get('name', 'Unnamed')}")
        else:
            while True:
                try:
                    choice = input(f"Please select a dataset (1-{len(datasets)}): ").strip()
                    idx = int(choice) - 1
                    if 0 <= idx < len(datasets):
                        selected_ds = datasets[idx]
                        break
                    else:
                        print(f"Error: Please enter a number between 1 and {len(datasets)}")
                except ValueError:
                    print("Error: Please enter a valid number")
        
        dataset_id = selected_ds['id']
        
        # Output configuration
        print()
        print("=" * 80)
        print("Configuration")
        print("=" * 80)
        print()
        print("Add the following to your .env file:")
        print()
        print(f"PBI_WORKSPACE_ID={workspace_id}")
        print(f"PBI_DATASET_ID={dataset_id}")
        print()
        print("Full example:")
        print("-" * 80)
        print(f"# Power BI Configuration")
        print(f"PBI_TENANT_ID={config.tenant_id}")
        print(f"PBI_CLIENT_ID={config.client_id}")
        print(f"PBI_CLIENT_SECRET=your-client-secret")
        print(f"")
        print(f"# Power BI Dataset and Workspace")
        print(f"PBI_WORKSPACE_ID={workspace_id}")
        print(f"PBI_DATASET_ID={dataset_id}")
        print("-" * 80)
        
    except Exception as e:
        print(f"Error: {e}")
        print()
        print("Please ensure:")
        print("1. .env is configured correctly")
        print("2. Network connectivity is OK")
        print("3. Power BI credentials are valid")


if __name__ == "__main__":
    main()


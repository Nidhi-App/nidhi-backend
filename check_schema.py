#!/usr/bin/env python3
"""
Script to check Supabase schema using the REST API and service role key
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Headers for Supabase REST API
headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

def get_schema_info():
    """Get schema information from Supabase"""

    # Query to get all tables (using PostgREST introspection)
    # We'll use the Supabase REST API to query information_schema

    print("=" * 80)
    print("SUPABASE DATABASE SCHEMA")
    print("=" * 80)
    print(f"\nProject: {SUPABASE_URL}")
    print("\n" + "=" * 80)

    # Try to query each known table to understand structure
    tables = ['accounts', 'transactions', 'users', 'institutions', 'connections', 'providers']

    for table in tables:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/{table}?limit=1",
                headers=headers
            )

            if response.status_code == 200:
                print(f"\n✅ Table: {table}")
                print(f"   Status: EXISTS")

                # Try to get count
                count_response = requests.get(
                    f"{SUPABASE_URL}/rest/v1/{table}?select=count",
                    headers={**headers, 'Prefer': 'count=exact'}
                )

                if 'content-range' in count_response.headers:
                    count = count_response.headers['content-range'].split('/')[-1]
                    print(f"   Rows: {count}")

                # Show sample data structure
                if response.json():
                    sample = response.json()[0]
                    print(f"   Columns: {', '.join(sample.keys())}")

            elif response.status_code == 404:
                print(f"\n❌ Table: {table}")
                print(f"   Status: NOT FOUND")
            else:
                print(f"\n⚠️  Table: {table}")
                print(f"   Status: ERROR ({response.status_code})")

        except Exception as e:
            print(f"\n⚠️  Table: {table}")
            print(f"   Error: {str(e)}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    get_schema_info()

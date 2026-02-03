"""
Quick test script to verify Apollo API key is working.
Run with: python -m pytest tests/test_apollo_key.py -v -s
Or directly: python tests/test_apollo_key.py
"""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx


async def test_apollo_api_key():
    """
    Test Apollo API key by making a direct API call.

    This tests:
    1. API key is configured
    2. API key is valid (not expired/revoked)
    3. API returns expected response structure
    """
    api_key = os.getenv("APOLLO_API_KEY")

    if not api_key:
        print("❌ APOLLO_API_KEY not set in environment")
        print("   Set it with: export APOLLO_API_KEY=your_key")
        return False

    print(f"✓ Apollo API key found: {api_key[:8]}...")

    # Test email - use a common pattern that should exist
    test_email = "contact@microsoft.com"

    print(f"\nTesting Apollo API with: {test_email}")
    print("-" * 50)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "https://api.apollo.io/v1/people/match",
                headers={"Content-Type": "application/json"},
                json={
                    "api_key": api_key,
                    "email": test_email,
                    "reveal_personal_emails": False
                }
            )

            print(f"HTTP Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                person = data.get("person")

                if person:
                    print("✓ Apollo API WORKING - returned person data:")
                    print(f"  Name: {person.get('first_name')} {person.get('last_name')}")
                    print(f"  Title: {person.get('title')}")
                    print(f"  Company: {person.get('organization', {}).get('name')}")
                    print(f"  LinkedIn: {person.get('linkedin_url')}")

                    # Check for phone numbers (we should NOT be pulling these)
                    if person.get('phone_numbers'):
                        print("⚠️  WARNING: Phone numbers present in response")
                        print("     (but our code doesn't extract them)")
                    else:
                        print("✓ No phone numbers in response (as expected)")

                    return True
                else:
                    print("⚠️ Apollo API returned empty person (email not found in database)")
                    print("   This is normal for unknown emails")
                    print("   Response keys:", list(data.keys()))
                    return True  # API is working, just no data for this email

            elif response.status_code == 401:
                print("❌ Apollo API key is INVALID or EXPIRED")
                print(f"   Response: {response.text[:200]}")
                return False

            elif response.status_code == 403:
                print("❌ Apollo API key FORBIDDEN - check permissions")
                print(f"   Response: {response.text[:200]}")
                return False

            elif response.status_code == 429:
                print("⚠️ Apollo API RATE LIMITED")
                print(f"   Response: {response.text[:200]}")
                return False

            else:
                print(f"❌ Unexpected status: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                return False

        except httpx.TimeoutException:
            print("❌ Apollo API request TIMED OUT")
            return False
        except Exception as e:
            print(f"❌ Error testing Apollo API: {e}")
            return False


if __name__ == "__main__":
    result = asyncio.run(test_apollo_api_key())
    sys.exit(0 if result else 1)

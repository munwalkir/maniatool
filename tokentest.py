import requests
import json

TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI0Mjk1NyIsImp0aSI6ImFjOGFiMGQwMWFlMmI1YWJhMzNjMmFkNWM0YTljZGJjMzE1OTFmZGZlYjU4OGEyZTRjODU3OTUwNzRjZDE0YTE5MDg5YjlmZTUwY2E5YTc3IiwiaWF0IjoxNzU0NDIyNjkyLjg3NTk0NCwibmJmIjoxNzU0NDIyNjkyLjg3NTk0OCwiZXhwIjoxNzU0NTA5MDkyLjg0NzM2Nywic3ViIjoiMzc1MTU3NDUiLCJzY29wZXMiOlsiaWRlbnRpZnkiLCJwdWJsaWMiXX0.MFemalvFePZOQXmHNBe20bp4q2vSrWHfmlWgCyGNYLu9JW58nxCdUWktJNvQfQV86NZluGZZ7Y9lZnW8Wi5VP0fg1J36qrBL1WvMyMXWlR05kBfar4eMmR5BooqxMpfaQ3rbnL-CPjuYd7UVS1DsjggmqTLdtyC_OdLDddKkFGUSCpKmSQXmsMWLO5qsmFNnAdC0oz88YL_RmDPYREZXopj71o4BEm91yYIQ0f1FGGioeerZgvLNFo-bohq96eLNrY3PLXxPhnQCNQme-u6nLS0QkrttnG1MBwFgFck83b7FX2ByhU0S7EaPdcfl21JWSopGrzLFqox0yNZT6vKB0toEggGLfyOuqbHaTrH6HJFgBQXuUS4DHAacWFYAYCQHsZeZ9C5SA98bkhALqGyEC1WFI0OCUUSIyyo5Lp2mJg2nMyVMJkqwIMDkFODWqeMvPfQ5mz3ZKQyXajrW14ugz0YNIi_sSS2QXrlHOsyQn9xOawzX1_KNi-JX1Ij_pCto_O2wmnWkKm_Vblnd3MXdueT0b-WOAot4Kah6MMmqP7on2ja7vik_2RksewILIocTAFztt7Vt31dRiiTErf_Ljg7VwQg16Mqd4CYa2zNctl6r_h5zUSHECW_OQ5D5viP_5_HU3eM8y-kTygGQ0aVb4amBeh0VKdBV5AZhDu9pT6M"

def test_token():
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    print("Testing token...")
    print(f"Token: {TOKEN[:20]}..." if TOKEN else "No token provided")
    print("-" * 50)

    try:
        response = requests.get("https://osu.ppy.sh/api/v2/me", headers=headers)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Token is working!")
            print(f"Username: {data['username']}")
            print(f"User ID: {data['id']}")
            print(f"Country: {data['country']['name']}")

            # Pretty print the full response
            print("\n📄 Full Response:")
            print(json.dumps(data, indent=2))

        elif response.status_code == 401:
            print("❌ Token is invalid or expired")
            print("Response:", response.text)

        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print("Response:", response.text)

    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_mania_stats():
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    print("\n" + "="*50)
    print("Testing mania-specific stats...")
    print("="*50)

    try:
        response = requests.get("https://osu.ppy.sh/api/v2/me/mania", headers=headers)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Mania stats available!")

            stats = data.get('statistics', {})
            print(f"PP: {stats.get('pp', 'N/A')}")
            print(f"Global Rank: #{stats.get('global_rank', 'N/A')}")
            print(f"Country Rank: #{stats.get('country_rank', 'N/A')}")
            print(f"Accuracy: {stats.get('hit_accuracy', 'N/A')}%")

            print("\n📄 Full Mania Response:")
            print(json.dumps(data, indent=2))

        else:
            print(f"❌ Failed to get mania stats: {response.status_code}")
            print("Response:", response.text)

    except Exception as e:
        print(f"❌ Mania request failed: {e}")

if __name__ == "__main__":
    if not TOKEN or TOKEN == "your_token_here":
        print("❌ Please set your token in the TOKEN variable")
        exit(1)

    test_token()
    test_mania_stats()
    input("Press Enter to exit")

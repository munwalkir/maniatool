import requests
import json
import time
from typing import List, Dict, Optional, Set
from datetime import datetime
import os
import pickle

class OsuUserScoresScraper:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://osu.ppy.sh/api/v2"
        self.session = requests.Session()


    def get_rate_from_mods(self, mods: List[str]) -> float:
        if 'DT' in mods:
            return 1.5
        elif 'HT' in mods:
            return 0.75
        return 1.0

    def make_api_request(self, endpoint: str, params: Dict = None) -> Dict:
        if not self.access_token:
            raise Exception("No access token provided")

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        url = f"{self.base_url}{endpoint}"

        # rate limit
        time.sleep(0.1)

        response = self.session.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_user_info(self, user_id: int) -> Dict:
        endpoint = f"/users/{user_id}/mania"
        return self.make_api_request(endpoint)

    def parse_mods(self, mods: List[str]) -> str:
        relevant_mods = []
        for mod in mods:
            if mod in ['HT', 'DT']:
                relevant_mods.append(mod)

        if not relevant_mods:
            return 'NM'  # No mods
        return '+'.join(relevant_mods)

    def get_user_scores(self, user_id: int, score_type: str = 'best', limit: int = 100) -> List[Dict]:
        all_scores = []
        offset = 0

        while len(all_scores) < 1000:  # limit
            endpoint = f"/users/{user_id}/scores/{score_type}"
            params = {
                'mode': 'mania',
                'limit': min(limit, 50),
                'offset': offset
            }

            try:
                scores = self.make_api_request(endpoint, params)

                if not scores:
                    break

                # 4k filter
                filtered_scores = []
                for score in scores:
                    beatmap = score.get('beatmap', {})
                    if beatmap.get('mode_int') == 3: # 3: mania
                        cs = beatmap.get('cs', 0)  # cs: keycount
                        if cs == 4:
                            filtered_scores.append(score)

                all_scores.extend(filtered_scores)

                if len(scores) < params['limit']:
                    break

                offset += len(scores)

            except requests.exceptions.RequestException as e:
                print(f"Error fetching scores: {e}")
                break

        return all_scores

    def extract_score_info(self, score: Dict) -> Dict:
        beatmap = score.get('beatmap', {})
        beatmapset = score.get('beatmapset', {})
        statistics = score.get('statistics', {})
        mods_list = score.get('mods', [])

        # accuracy calculation
        count_300 = statistics.get('count_300', 0)
        count_100 = statistics.get('count_100', 0)
        count_50 = statistics.get('count_50', 0)
        count_miss = statistics.get('count_miss', 0)
        count_geki = statistics.get('count_geki', 0)  # max
        count_katu = statistics.get('count_katu', 0)  # 200

        total_hits = count_300 + count_100 + count_50 + count_miss + count_geki + count_katu
        if total_hits > 0:
            # Mania accuracy calculation
            accuracyV1 = (count_geki * 300 + count_300 * 300 + count_katu * 200 + count_100 * 100 + count_50 * 50) / (total_hits * 300) * 100
            accuracyV2 = (count_geki * 305 + count_300 * 300 + count_katu * 200 + count_100 * 100 + count_50 * 50) / (total_hits * 305) * 100
        else:
            accuracyV1 = 0
            accuracyV2 = 0

        return {
            'pp': score.get('pp'),
            'accuracy': round(accuracyV1, 2),
            'accuracyV2': round(accuracyV2, 2),
            'beatmap_id': beatmap.get('id'),
            'difficulty_name': beatmap.get('version', 'Unknown'),
            'mods': self.parse_mods(mods_list),
            'rate': self.get_rate_from_mods(mods_list),
            'score': score.get('score', 0),
            'max_combo': score.get('max_combo', 0),
            'perfect': score.get('perfect', False),
            'created_at': score.get('created_at'),
            'beatmapset_id': beatmapset.get('id'),
            'title': beatmapset.get('title', 'Unknown'),
            'artist': beatmapset.get('artist', 'Unknown'),
            'creator': beatmapset.get('creator', 'Unknown'),
            'star_rating': beatmap.get('difficulty_rating', 0),
            'key_count': beatmap.get('cs', 4),  # Circle size = key count in mania
            'rank': score.get('rank', 'F'),
            'statistics': {
                'count_geki': count_geki,
                'count_300': count_300,
                'count_katu': count_katu,
                'count_100': count_100,
                'count_50': count_50,
                'count_miss': count_miss
            }
        }

    def scrape_user_scores(self, user_id: int, force_refresh: bool = False) -> Dict:
        try:
            print(f"Scraping scores for user {user_id}...")

            user_info = self.get_user_info(user_id)
            print(f"Found user: {user_info.get('username', 'Unknown')}")

            # top plays
            best_scores = self.get_user_scores(user_id, 'best', limit=100)
            print(f"Found {len(best_scores)} best 4K scores")

            # recents
            recent_scores = self.get_user_scores(user_id, 'recent', limit=100)
            print(f"Found {len(recent_scores)} recent 4K scores")

            processed_best = [self.extract_score_info(score) for score in best_scores]
            processed_recent = [self.extract_score_info(score) for score in recent_scores]

            unique_beatmaps = {}
            for score in processed_best + processed_recent:
                if score['beatmap_id']:
                    beatmap_id = score['beatmap_id']
                    rate = score['rate']
                    if beatmap_id not in unique_beatmaps:
                        unique_beatmaps[beatmap_id] = set()
                    unique_beatmaps[beatmap_id].add(rate)

            analysis_groups = {}
            for beatmap_id, rates in unique_beatmaps.items():
                for rate in rates:
                    if rate not in analysis_groups:
                        analysis_groups[rate] = []
                    analysis_groups[rate].append(beatmap_id)

            result = {
                'user_info': {
                    'user_id': user_info.get('id'),
                    'username': user_info.get('username'),
                    'country_code': user_info.get('country_code'),
                    'global_rank': user_info.get('statistics', {}).get('global_rank'),
                    'country_rank': user_info.get('statistics', {}).get('country_rank'),
                    'pp': user_info.get('statistics', {}).get('pp'),
                    'accuracy': user_info.get('statistics', {}).get('hit_accuracy'),
                    'play_count': user_info.get('statistics', {}).get('play_count'),
                    'scraped_at': datetime.now().isoformat()
                },
                'scores': {
                    'best': processed_best,
                    'recent': processed_recent
                },
                'analysis_groups': analysis_groups,
                'total_unique_maps': len(unique_beatmaps)
            }

            print(f"Successfully scraped {len(processed_best)} best and {len(processed_recent)} recent scores")
            print(f"Found {len(unique_beatmaps)} unique beatmaps to analyze")
            print(f"Analysis groups by rate: {dict((k, len(v)) for k, v in analysis_groups.items())}")

            return result

        except Exception as e:
            print(f"Error scraping user {user_id}: {e}")
            return None

    def save_scores_to_file(self, user_data: Dict, filename: Optional[str] = None):
        if not filename:
            user_id = user_data['user_info']['user_id']
            username = user_data['user_info']['username']
            filename = f"scores_{username}_{user_id}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, indent=2, ensure_ascii=False)
            print(f"Scores saved to {filename}")
        except Exception as e:
            print(f"Error saving scores: {e}")

def get_user_id_from_token(access_token: str) -> int:
    """Get the user ID from the access token by fetching /me endpoint"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.get("https://osu.ppy.sh/api/v2/me", headers=headers)
    response.raise_for_status()
    user_data = response.json()
    return user_data['id']

if __name__ == "__main__":
    # this will be changed. access token will be passed from main.py in the production.
    import dotenv
    dotenv.load_dotenv()

    access_token = os.getenv("OSU_ACCESS_TOKEN", "")

    if not access_token:
        print("Please provide an OSU_ACCESS_TOKEN")
        exit(1)

    # scraper init
    scraper = OsuUserScoresScraper(access_token)

    user_id = get_user_id_from_token(access_token)
    print(f"Analyzing scores for user ID: {user_id}")

    user_data = scraper.scrape_user_scores(user_id)

    if user_data:
        scraper.save_scores_to_file(user_data)

        print(f"User: {user_data['user_info']['username']}")
        print(f"Global Rank: #{user_data['user_info']['global_rank']}")
        print(f"PP: {user_data['user_info']['pp']}")
        print(f"Best scores: {len(user_data['scores']['best'])}")
        print(f"Recent scores: {len(user_data['scores']['recent'])}")
        print(f"Unique beatmaps: {user_data['total_unique_maps']}")

        print("\n--- Analysis Groups by Rate ---")
        for rate, beatmap_ids in user_data['analysis_groups'].items():
            mod_name = "DT" if rate == 1.5 else "HT" if rate == 0.75 else "NM"
            print(f"{mod_name} (rate {rate}): {len(beatmap_ids)} beatmaps")

        print("\n--- Example scores with mods ---")
        all_scores = user_data['scores']['best'] + user_data['scores']['recent']
        modded_scores = [s for s in all_scores if s['mods'] != 'NM'][:5]

        for score in modded_scores:
            print(f"{score['title']} [{score['difficulty_name']}] {score['mods']} (rate {score['rate']}) - {score['pp']}pp ({score['accuracy']}%)")

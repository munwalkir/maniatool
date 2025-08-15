import aiohttp
import zipfile
import os
from pathlib import Path
from typing import List

class BeatmapDownloader:
    def __init__(self, access_token, client_id=None, client_secret=None, user_cookie=None):
        self.access_token = access_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.cookie_header = user_cookie or os.getenv("OSU_SESSION_COOKIE")

    async def download_and_extract_beatmapset(self, beatmap_id: int, temp_dir: str) -> str:
        if not self.cookie_header:
            raise Exception("No osu! session cookie provided. Please add your cookie in settings.")

        osz_path = await self._download_osz(beatmap_id, temp_dir)
        extracted_dir = os.path.join(temp_dir, "extracted")
        self._extract_osz(osz_path, extracted_dir)
        return extracted_dir

    async def _download_osz(self, beatmap_id: int, temp_dir: str) -> str:
        osz_path = os.path.join(temp_dir, f"{beatmap_id}.osz")
        url = f"https://osu.ppy.sh/beatmapsets/{beatmap_id}/download"

        cookie_value = self.cookie_header
        if cookie_value and not cookie_value.strip().startswith("osu_session="):
            cookie_value = f"osu_session={cookie_value.strip()}"

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Connection": "keep-alive",
            "Referer": f"https://osu.ppy.sh/beatmapsets/{beatmap_id}",
            "Cookie": cookie_value,
            "Upgrade-Insecure-Requests": "1",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, allow_redirects=True) as resp:
                if resp.status == 401:
                    raise Exception("Invalid or expired osu! session cookie. Please update your cookie.")
                elif resp.status != 200:
                    snippet = await resp.text()
                    raise Exception(f"Download failed: HTTP {resp.status} {snippet[:500]}")

                first_bytes = await resp.content.read(4)
                if not first_bytes.startswith(b"PK"):
                    snippet = (first_bytes + await resp.content.read(1024)).decode(errors="replace")
                    raise Exception(f"Invalid OSZ file: {snippet[:500]}")

                with open(osz_path, "wb") as f:
                    f.write(first_bytes)
                    async for chunk in resp.content.iter_chunked(8192):
                        f.write(chunk)

        try:
            with zipfile.ZipFile(osz_path, "r") as z:
                if not z.namelist():
                    raise zipfile.BadZipFile("Empty OSZ")
        except zipfile.BadZipFile:
            raise Exception("Corrupted OSZ")

        return osz_path

    def _extract_osz(self, osz_path: str, extract_dir: str):
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(osz_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

    def find_mania_osu_files(self, directory: str) -> List[str]:
        mania_files = []
        for file in Path(directory).rglob("*.osu"):
            if self._is_mania_map(str(file)):
                mania_files.append(str(file))
        return mania_files

    def _is_mania_map(self, osu_file_path: str) -> bool:
        try:
            with open(osu_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.strip().startswith('Mode:'):
                        return line.split(':')[1].strip() == '3'
                return False
        except Exception:
            return False

    def parse_osu_metadata(self, osu_file_path: str) -> dict:
        metadata = {}
        hit_objects = 0
        star_rating = 0.0

        try:
            with open(osu_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                current_section = None

                for line in f:
                    line = line.strip()

                    if line.startswith('[') and line.endswith(']'):
                        current_section = line[1:-1]
                    elif ':' in line and current_section in ['General', 'Metadata', 'Difficulty']:
                        key, value = line.split(':', 1)
                        key, value = key.strip(), value.strip()

                        if key == 'Title': metadata['title'] = value
                        elif key == 'Artist': metadata['artist'] = value
                        elif key == 'Creator': metadata['creator'] = value
                        elif key == 'Version': metadata['version'] = value
                        elif key == 'CircleSize': metadata['key_count'] = int(float(value))
                        elif key == 'OverallDifficulty': star_rating = float(value)
                    elif current_section == 'HitObjects' and line and not line.startswith('//'):
                        hit_objects += 1

            metadata['hit_objects'] = hit_objects
            metadata['star_rating'] = star_rating
        except Exception as e:
            print(f"Error parsing {osu_file_path}: {e}")

        return metadata

    async def get_beatmapset_info(self, beatmap_id: int):
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                url = f"https://osu.ppy.sh/api/v2/beatmapsets/{beatmap_id}"

                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"API request failed: {response.status}")

                    data = await response.json()
                    mania_beatmaps = [bm for bm in data['beatmaps'] if bm['mode_int'] == 3]

                    if not mania_beatmaps:
                        raise Exception("No osu!mania maps found")

                    difficulties = []
                    for bm in mania_beatmaps:
                        difficulties.append({
                            'filename': f"{data['artist']} - {data['title']} ({data['creator']}) [{bm['version']}].osu",
                            'difficulty_name': bm['version'],
                            'creator': data['creator'],
                            'key_count': int(bm['cs']),
                            'hit_objects': bm['count_circles'] + bm['count_sliders'] + bm['count_spinners'],
                            'star_rating': bm['difficulty_rating']
                        })

                    return {
                        'beatmapset_id': beatmap_id,
                        'title': data['title'],
                        'artist': data['artist'],
                        'creator': data['creator'],
                        'difficulties': difficulties
                    }

        except Exception:
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                extracted_dir = await self.download_and_extract_beatmapset(beatmap_id, temp_dir)
                mania_files = self.find_mania_osu_files(extracted_dir)

                if not mania_files:
                    raise Exception("No osu!mania maps found")

                difficulties = []
                first_meta = self.parse_osu_metadata(mania_files[0])

                for osu_file in mania_files:
                    meta = self.parse_osu_metadata(osu_file)
                    difficulties.append({
                        'filename': os.path.basename(osu_file),
                        'difficulty_name': meta.get('version', 'Unknown'),
                        'creator': meta.get('creator', 'Unknown'),
                        'key_count': meta.get('key_count', 4),
                        'hit_objects': meta.get('hit_objects', 0),
                        'star_rating': meta.get('star_rating', 0.0)
                    })

                return {
                    'beatmapset_id': beatmap_id,
                    'title': first_meta.get('title', 'Unknown'),
                    'artist': first_meta.get('artist', 'Unknown'),
                    'creator': first_meta.get('creator', 'Unknown'),
                    'difficulties': difficulties
                }

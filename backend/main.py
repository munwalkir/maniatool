from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import tempfile
import os
import shutil
from datetime import datetime
import re
import hashlib
import json

from osu_to_sm import convert_osu_to_stepmania
from minacalc_bindings import MinaCalc, parse_sm_file
from beatmap_downloader import BeatmapDownloader
from scores import OsuUserScoresScraper, get_user_id_from_token

import dotenv
dotenv.load_dotenv()

OSU_CLIENT_ID = int(os.getenv("OSU_CLIENT_ID", "0"))
OSU_CLIENT_SECRET = os.getenv("OSU_CLIENT_SECRET", "")

app = FastAPI(title="Mania Difficulty Analysis API", description="osu!mania to StepMania difficulty analysis")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9731", "http://localhost:9831", "http://localhost:9931"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# directory structure
DOWNLOADS_DIR = "downloads"
OSU_FILES_DIR = os.path.join(DOWNLOADS_DIR, "osu")
SM_FILES_DIR = os.path.join(DOWNLOADS_DIR, "sm")
USER_SCORES_DIR = os.path.join(DOWNLOADS_DIR, "user_scores")

for directory in [DOWNLOADS_DIR, OSU_FILES_DIR, SM_FILES_DIR, USER_SCORES_DIR]:
    os.makedirs(directory, exist_ok=True)

class AnalysisRequest(BaseModel):
    beatmap_ids: List[int]
    difficulty_names: Optional[List[str]] = None
    access_token: str
    rate: Optional[float] = 1.0
    osu_session_cookie: Optional[str] = None

class UserScoreRequest(BaseModel):
    access_token: str

class DifficultyInfo(BaseModel):
    filename: str
    difficulty_name: str
    creator: str
    key_count: int
    hit_objects: int
    star_rating: float

class BeatmapsetInfo(BaseModel):
    beatmapset_id: int
    title: str
    artist: str
    creator: str
    difficulties: List[DifficultyInfo]

class DifficultyAnalysis(BaseModel):
    beatmap_id: int
    title: str
    artist: str
    difficulty_name: str
    creator: str
    key_count: int
    overall: float
    stream: float
    jumpstream: float
    handstream: float
    stamina: float
    jackspeed: float
    chordjack: float
    technical: float
    hit_objects: int
    star_rating: float
    rate: float
    success: bool
    error_message: Optional[str] = None
    analyzed_at: str

class AnalysisResponse(BaseModel):
    results: List[DifficultyAnalysis]
    total_processed: int
    successful: int
    failed: int

class BeatmapsetListResponse(BaseModel):
    beatmapsets: List[BeatmapsetInfo]
    total_found: int

class UserScoreInfo(BaseModel):
    pp: Optional[float]
    accuracy: float
    accuracyV2: float
    beatmap_id: int
    difficulty_name: str
    mods: str
    rate: float
    score: int
    max_combo: int
    perfect: bool
    created_at: str
    beatmapset_id: int
    title: str
    artist: str
    creator: str
    star_rating: float
    key_count: int
    rank: str
    statistics: Dict

class UserAnalysisData(BaseModel):
    user_id: int
    username: str
    country_code: str
    global_rank: Optional[int]
    country_rank: Optional[int]
    user_pp: Optional[float]
    user_accuracy: Optional[float]
    play_count: Optional[int]
    best_scores: List[UserScoreInfo]
    recent_scores: List[UserScoreInfo]
    analysis_groups: Dict[float, List[int]]
    total_unique_maps: int
    scraped_at: str

minacalc_instance = None

@app.on_event("startup")
async def startup_event():
    #initialize minacalc
    global minacalc_instance
    try:
        minacalc_instance = MinaCalc()
        print(f"MinaCalc initialized, version: {minacalc_instance.get_version()}")
    except Exception as e:
        print(f"Failed to initialize MinaCalc: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    global minacalc_instance
    if minacalc_instance:
        del minacalc_instance

def get_file_hash(file_path: str) -> str:
    #sha256 cache
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()[:12]
    except Exception:
        return "unknown"

def get_cached_osu_path(beatmap_id: int, difficulty_name: str) -> Optional[str]:
    #.osu caching control
    pattern = f"{beatmap_id}_{difficulty_name.replace(' ', '_')}"
    for filename in os.listdir(OSU_FILES_DIR):
        if filename.startswith(pattern) and filename.endswith(".osu"):
            full_path = os.path.join(OSU_FILES_DIR, filename)
            if os.path.exists(full_path):
                return full_path
    return None

def get_cached_sm_path(beatmap_id: int, difficulty_name: str, file_hash: str) -> Optional[str]:
    #same for .sm
    sm_filename = f"{beatmap_id}_{difficulty_name.replace(' ', '_')}_{file_hash}.sm"
    sm_path = os.path.join(SM_FILES_DIR, sm_filename)
    return sm_path if os.path.exists(sm_path) else None

def cache_osu_file(source_path: str, beatmap_id: int, difficulty_name: str) -> str:
    #cache stuff - pimp biscuit
    file_hash = get_file_hash(source_path)
    cached_filename = f"{beatmap_id}_{difficulty_name.replace(' ', '_')}_{file_hash}.osu"
    cached_path = os.path.join(OSU_FILES_DIR, cached_filename)

    if not os.path.exists(cached_path):
        shutil.copy2(source_path, cached_path)
        print(f"Cached .osu file: {cached_filename}")

    return cached_path

def cache_sm_file(source_path: str, beatmap_id: int, difficulty_name: str, file_hash: str) -> str:
    cached_filename = f"{beatmap_id}_{difficulty_name.replace(' ', '_')}_{file_hash}.sm"
    cached_path = os.path.join(SM_FILES_DIR, cached_filename)

    if not os.path.exists(cached_path):
        shutil.copy2(source_path, cached_path)
        print(f"Cached .sm file: {cached_filename}")

    return cached_path

def save_user_scores_to_json(user_data: UserAnalysisData) -> str:
    #saving scores to json
    filename = f"user_scores_{user_data.username}_{user_data.user_id}.json"
    filepath = os.path.join(USER_SCORES_DIR, filename)

    data_dict = user_data.model_dump()

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False)
        print(f"User scores saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error saving user scores: {e}")
        return ""

@app.get("/")
async def root():
    return {"message": "Mania Difficulty Analysis API is running"}

@app.post("/user-scores", response_model=UserAnalysisData)
async def get_user_scores(request: UserScoreRequest):
    if not request.access_token:
        raise HTTPException(status_code=400, detail="access_token is required")

    try:
        print("Initializing user score scraper...")
        scraper = OsuUserScoresScraper(request.access_token)

        print("Getting user ID from token...")
        user_id = get_user_id_from_token(request.access_token)
        print(f"Analyzing scores for user ID: {user_id}")

        user_data = scraper.scrape_user_scores(user_id)

        if not user_data:
            raise HTTPException(status_code=404, detail="Could not fetch user scores")

        best_scores = []
        for score in user_data['scores']['best']:
            try:
                best_scores.append(UserScoreInfo(
                    pp=score['pp'],
                    accuracy=score['accuracy'],
                    accuracyV2=score['accuracyV2'],
                    beatmap_id=score['beatmap_id'],
                    difficulty_name=score['difficulty_name'],
                    mods=score['mods'],
                    rate=score['rate'],
                    score=score['score'],
                    max_combo=score['max_combo'],
                    perfect=score['perfect'],
                    created_at=score['created_at'],
                    beatmapset_id=score['beatmapset_id'],
                    title=score['title'],
                    artist=score['artist'],
                    creator=score['creator'],
                    star_rating=score['star_rating'],
                    key_count=score['key_count'],
                    rank=score['rank'],
                    statistics=score['statistics']
                ))
            except Exception as e:
                print(f"Error processing best score: {e}")
                continue

        recent_scores = []
        for score in user_data['scores']['recent']:
            try:
                recent_scores.append(UserScoreInfo(
                    pp=score['pp'],
                    accuracy=score['accuracy'],
                    accuracyV2=score['accuracyV2'],
                    beatmap_id=score['beatmap_id'],
                    difficulty_name=score['difficulty_name'],
                    mods=score['mods'],
                    rate=score['rate'],
                    score=score['score'],
                    max_combo=score['max_combo'],
                    perfect=score['perfect'],
                    created_at=score['created_at'],
                    beatmapset_id=score['beatmapset_id'],
                    title=score['title'],
                    artist=score['artist'],
                    creator=score['creator'],
                    star_rating=score['star_rating'],
                    key_count=score['key_count'],
                    rank=score['rank'],
                    statistics=score['statistics']
                ))
            except Exception as e:
                print(f"Error processing recent score: {e}")
                continue

        user_analysis_data = UserAnalysisData(
            user_id=user_data['user_info']['user_id'],
            username=user_data['user_info']['username'],
            country_code=user_data['user_info']['country_code'],
            global_rank=user_data['user_info']['global_rank'],
            country_rank=user_data['user_info']['country_rank'],
            user_pp=user_data['user_info']['pp'],
            user_accuracy=user_data['user_info']['accuracy'],
            play_count=user_data['user_info']['play_count'],
            best_scores=best_scores,
            recent_scores=recent_scores,
            analysis_groups=user_data['analysis_groups'],
            total_unique_maps=user_data['total_unique_maps'],
            scraped_at=user_data['user_info']['scraped_at']
        )

        # save to json
        json_filepath = save_user_scores_to_json(user_analysis_data)

        print(f"User: {user_analysis_data.username} (#{user_analysis_data.user_id})\nGlobal Rank: #{user_analysis_data.global_rank}\nPP: {user_analysis_data.user_pp}\nAccuracy: {user_analysis_data.user_accuracy:.2f}%\nPlay Count: {user_analysis_data.play_count}\nBest scores: {len(user_analysis_data.best_scores)}\nRecent scores: {len(user_analysis_data.recent_scores)}\nUnique beatmaps: {user_analysis_data.total_unique_maps}")

        print("\nAnalysis Groups by Rate:")
        for rate, beatmap_ids in user_analysis_data.analysis_groups.items():
            mod_name = "DT" if rate == 1.5 else "HT" if rate == 0.75 else "NM"
            print(f"   {mod_name} (rate {rate}x): {len(beatmap_ids)} beatmaps")

        print("\nExample modded scores:")
        all_scores = user_analysis_data.best_scores + user_analysis_data.recent_scores
        modded_scores = [s for s in all_scores if s.mods != 'NM'][:5]

        for score in modded_scores:
            print(f"   {score.title} [{score.difficulty_name}] +{score.mods} (rate {score.rate}x) - {score.pp}pp ({score.accuracy:.2f}%)")

        if json_filepath:
            print(f"\nData saved to: {json_filepath}")

        return user_analysis_data

    except Exception as e:
        print(f"❌ Error in get_user_scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/list-difficulties", response_model=BeatmapsetListResponse)
async def list_difficulties(request: AnalysisRequest):
    #listing mania diffs for id
    if not request.access_token:
        raise HTTPException(status_code=400, detail="access_token is required in request body")

    downloader = BeatmapDownloader(
        request.access_token,
        OSU_CLIENT_ID,
        OSU_CLIENT_SECRET,
        user_cookie=request.osu_session_cookie
    )
    beatmapsets = []
    total_found = 0

    for beatmap_id in request.beatmap_ids:
        try:
            beatmapset_info = await downloader.get_beatmapset_info(beatmap_id)
            beatmapsets.append(BeatmapsetInfo(
                beatmapset_id=beatmapset_info['beatmapset_id'],
                title=beatmapset_info['title'],
                artist=beatmapset_info['artist'],
                creator=beatmapset_info['creator'],
                difficulties=[
                    DifficultyInfo(
                        filename=diff['filename'],
                        difficulty_name=diff['difficulty_name'],
                        creator=diff['creator'],
                        key_count=diff['key_count'],
                        hit_objects=diff['hit_objects'],
                        star_rating=diff['star_rating']
                    ) for diff in beatmapset_info['difficulties']
                ]
            ))
            total_found += len(beatmapset_info['difficulties'])
        except Exception as e:
            beatmapsets.append(BeatmapsetInfo(
                beatmapset_id=beatmap_id,
                title=f"Error: {str(e)}",
                artist="Unknown",
                creator="Unknown",
                difficulties=[]
            ))

    return BeatmapsetListResponse(
        beatmapsets=beatmapsets,
        total_found=total_found
    )

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_maps(request: AnalysisRequest):
    #difficulty analysis (this was a pain ong)
    if not minacalc_instance:
        raise HTTPException(status_code=500, detail="MinaCalc not initialized")

    if not request.access_token:
        raise HTTPException(status_code=400, detail="access_token is required in request body")

    rate = request.rate or 1.0
    if rate <= 0 or rate > 3.0:
        raise HTTPException(status_code=400, detail="Rate must be between 0 and 3.0")

    downloader = BeatmapDownloader(
        request.access_token,
        OSU_CLIENT_ID,
        OSU_CLIENT_SECRET,
        user_cookie=request.osu_session_cookie
    )
    results = []
    successful = 0
    failed = 0

    for beatmap_id in request.beatmap_ids:
        try:
            map_results = await process_beatmapset(downloader, beatmap_id, request.difficulty_names, rate)
            for analysis in map_results:
                if analysis.success:
                    successful += 1
                else:
                    failed += 1
                results.append(analysis)
        except Exception as e:
            failed += 1
            results.append(DifficultyAnalysis(
                beatmap_id=beatmap_id,
                title="Unknown",
                artist="Unknown",
                difficulty_name="Unknown",
                creator="Unknown",
                key_count=0,
                overall=0.0,
                stream=0.0,
                jumpstream=0.0,
                handstream=0.0,
                stamina=0.0,
                jackspeed=0.0,
                chordjack=0.0,
                technical=0.0,
                hit_objects=0,
                star_rating=0.0,
                rate=rate,
                success=False,
                error_message=str(e),
                analyzed_at=datetime.now().isoformat()
            ))

    return AnalysisResponse(
        results=results,
        total_processed=len(results),
        successful=successful,
        failed=failed
    )

def strip_keycount_prefix(s):
    return re.sub(r'^\[\d+K\]\s*', '', s, flags=re.IGNORECASE).strip()

async def process_beatmapset(downloader: BeatmapDownloader, beatmap_id: int, difficulty_filter: Optional[List[str]] = None, rate: float = 1.0) -> List[DifficultyAnalysis]:
    #processing difficulties (lowk unoptimized)
    results = []

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            extracted_dir = await downloader.download_and_extract_beatmapset(beatmap_id, temp_dir)
            mania_files = downloader.find_mania_osu_files(extracted_dir)

            if not mania_files:
                raise Exception("No osu!mania maps found in beatmapset")

            for osu_file in mania_files:
                metadata = None
                try:
                    metadata = downloader.parse_osu_metadata(osu_file)
                    diff_name = metadata.get('version', 'Unknown')
                    print(f"Checking file: {osu_file}, version: {diff_name}")

                    if difficulty_filter:
                        filter_lc = [strip_keycount_prefix(f).lower() for f in difficulty_filter]
                        version_lc = diff_name.strip().lower()
                        filename_lc = os.path.basename(osu_file).strip().lower()
                        if not any(f in version_lc or f in filename_lc for f in filter_lc):
                            print(f"Skipping {diff_name} (not in filter, after keycount strip)")
                            continue

                    print(f"Processing {osu_file}")
                    analysis = await process_single_difficulty(beatmap_id, osu_file, temp_dir, metadata, rate)
                    results.append(analysis)

                except Exception as e:
                    results.append(DifficultyAnalysis(
                        beatmap_id=beatmap_id,
                        title=metadata.get('title', 'Unknown') if metadata else 'Unknown',
                        artist=metadata.get('artist', 'Unknown') if metadata else 'Unknown',
                        difficulty_name=metadata.get('version', 'Unknown') if metadata else 'Unknown',
                        creator=metadata.get('creator', 'Unknown') if metadata else 'Unknown',
                        key_count=metadata.get('key_count', 4) if metadata else 4,
                        overall=0.0,
                        stream=0.0,
                        jumpstream=0.0,
                        handstream=0.0,
                        stamina=0.0,
                        jackspeed=0.0,
                        chordjack=0.0,
                        technical=0.0,
                        hit_objects=metadata.get('hit_objects', 0) if metadata else 0,
                        star_rating=metadata.get('star_rating', 0.0) if metadata else 0.0,
                        rate=rate,
                        success=False,
                        error_message=str(e),
                        analyzed_at=datetime.now().isoformat()
                    ))

        except Exception as e:
            results.append(DifficultyAnalysis(
                beatmap_id=beatmap_id,
                title="Unknown",
                artist="Unknown",
                difficulty_name="Unknown",
                creator="Unknown",
                key_count=0,
                overall=0.0,
                stream=0.0,
                jumpstream=0.0,
                handstream=0.0,
                stamina=0.0,
                jackspeed=0.0,
                chordjack=0.0,
                technical=0.0,
                hit_objects=0,
                star_rating=0.0,
                rate=rate,
                success=False,
                error_message=str(e),
                analyzed_at=datetime.now().isoformat()
            ))

    return results

async def process_single_difficulty(beatmap_id: int, osu_file: str, temp_dir: str, metadata: dict, rate: float = 1.0) -> DifficultyAnalysis:
    #single diff process
    global minacalc_instance

    if not minacalc_instance:
        raise Exception("MinaCalc not initialized")

    try:
        diff_name = metadata.get('version', 'Unknown')

        # Check if we have cached files
        cached_osu_path = get_cached_osu_path(beatmap_id, diff_name)

        if cached_osu_path:
            print(f"Using cached .osu file: {os.path.basename(cached_osu_path)}")
            file_hash = get_file_hash(cached_osu_path)
            cached_sm_path = get_cached_sm_path(beatmap_id, diff_name, file_hash)

            if cached_sm_path:
                print(f"Using cached .sm file: {os.path.basename(cached_sm_path)}")
                sm_path = cached_sm_path
            else:
                # Convert and cache the SM file
                sm_filename = f"{os.path.basename(osu_file)}.sm"
                sm_path = os.path.join(temp_dir, sm_filename)
                conversion_result = convert_osu_to_stepmania(cached_osu_path, sm_path)

                if not conversion_result['success']:
                    raise Exception(f"Conversion failed: {conversion_result.get('error', 'Unknown error')}")

                # Cache the converted SM file
                sm_path = cache_sm_file(sm_path, beatmap_id, diff_name, file_hash)
        else:
            # No cached files, do full process and cache
            print(f"No cached files found, processing fresh")

            # Cache the .osu file first
            cached_osu_path = cache_osu_file(osu_file, beatmap_id, diff_name)
            file_hash = get_file_hash(cached_osu_path)

            # Convert to SM
            sm_filename = f"{os.path.basename(osu_file)}.sm"
            sm_path = os.path.join(temp_dir, sm_filename)
            conversion_result = convert_osu_to_stepmania(osu_file, sm_path)

            if not conversion_result['success']:
                raise Exception(f"Conversion failed: {conversion_result.get('error', 'Unknown error')}")

            # Cache the SM file
            sm_path = cache_sm_file(sm_path, beatmap_id, diff_name, file_hash)

        # Parse SM file
        note_data = parse_sm_file(sm_path)

        if not note_data:
            raise Exception("No note data found in converted SM file")

        # Use SSR calculation with the specified rate
        difficulty_data = minacalc_instance.calculate_ssr(note_data, music_rate=rate, score_goal=0.93)

        return DifficultyAnalysis(
            beatmap_id=beatmap_id,
            title=metadata.get('title', 'Unknown'),
            artist=metadata.get('artist', 'Unknown'),
            difficulty_name=metadata.get('version', 'Unknown'),
            creator=metadata.get('creator', 'Unknown'),
            key_count=metadata.get('key_count', 4),
            overall=difficulty_data.get('overall', 0.0),
            stream=difficulty_data.get('stream', 0.0),
            jumpstream=difficulty_data.get('jumpstream', 0.0),
            handstream=difficulty_data.get('handstream', 0.0),
            stamina=difficulty_data.get('stamina', 0.0),
            jackspeed=difficulty_data.get('jackspeed', 0.0),
            chordjack=difficulty_data.get('chordjack', 0.0),
            technical=difficulty_data.get('technical', 0.0),
            hit_objects=metadata.get('hit_objects', 0),
            star_rating=metadata.get('star_rating', 0.0),
            rate=rate,
            success=True,
            analyzed_at=datetime.now().isoformat()
        )

    except Exception as e:
        return DifficultyAnalysis(
            beatmap_id=beatmap_id,
            title=metadata.get('title', 'Unknown'),
            artist=metadata.get('artist', 'Unknown'),
            difficulty_name=metadata.get('version', 'Unknown'),
            creator=metadata.get('creator', 'Unknown'),
            key_count=metadata.get('key_count', 4),
            overall=0.0,
            stream=0.0,
            jumpstream=0.0,
            handstream=0.0,
            stamina=0.0,
            jackspeed=0.0,
            chordjack=0.0,
            technical=0.0,
            hit_objects=metadata.get('hit_objects', 0),
            star_rating=metadata.get('star_rating', 0.0),
            rate=rate,
            success=False,
            error_message=str(e),
            analyzed_at=datetime.now().isoformat()
        )

@app.get("/health")
async def health_check():
    #health check
    global minacalc_instance

    status = {
        "status": "healthy" if minacalc_instance else "unhealthy",
        "message": "Mania Difficulty Analysis API is operational",
        "minacalc_available": minacalc_instance is not None
    }

    if minacalc_instance:
        try:
            status["minacalc_version"] = minacalc_instance.get_version()
        except Exception as e:
            status["minacalc_error"] = str(e)
            status["status"] = "unhealthy"

    return status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9731)

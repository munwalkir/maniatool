import os
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class TimingPoint:
    time: float  # milliseconds
    beat_length: float  # milliseconds per beat
    meter: int
    sample_set: int
    sample_index: int
    volume: int
    uninherited: bool
    effects: int


@dataclass
class HitObject:
    x: int
    y: int
    time: float  # milliseconds
    type: int
    hit_sound: int
    end_time: Optional[float] = None

    @property
    def is_hold(self) -> bool:
        return (self.type & 128) != 0


@dataclass
class Metadata:
    title: str = "Unknown"
    artist: str = "Unknown"
    creator: str = "Unknown"
    version: str = "Unknown"
    audio_filename: str = "audio.mp3"
    preview_time: int = -1


class OsuBeatmap:
    def __init__(self):
        self.metadata = Metadata()
        self.circle_size: float = 4.0
        self.timing_points: List[TimingPoint] = []
        self.hit_objects: List[HitObject] = []
        self.mode: int = 0

    @classmethod
    def from_file(cls, filepath: str) -> 'OsuBeatmap':
        beatmap = cls()

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        lines = content.splitlines()
        current_section = None

        for line in lines:
            line = line.strip()
            if not line or line.startswith('//'):
                continue

            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1].lower()
                continue

            if current_section == 'general':
                beatmap._parse_general(line)
            elif current_section == 'metadata':
                beatmap._parse_metadata(line)
            elif current_section == 'difficulty':
                beatmap._parse_difficulty(line)
            elif current_section == 'timingpoints':
                beatmap._parse_timing_point(line)
            elif current_section == 'hitobjects':
                beatmap._parse_hit_object(line)

        return beatmap

    def _parse_general(self, line: str):
        if ':' not in line:
            return
        key, value = line.split(':', 1)
        key, value = key.strip(), value.strip()

        if key == 'AudioFilename':
            self.metadata.audio_filename = value
        elif key == 'PreviewTime':
            try:
                self.metadata.preview_time = int(value)
            except ValueError:
                pass
        elif key == 'Mode':
            try:
                self.mode = int(value)
            except ValueError:
                pass

    def _parse_metadata(self, line: str):
        if ':' not in line:
            return
        key, value = line.split(':', 1)
        key, value = key.strip(), value.strip()

        if key == 'Title':
            self.metadata.title = value
        elif key == 'Artist':
            self.metadata.artist = value
        elif key == 'Creator':
            self.metadata.creator = value
        elif key == 'Version':
            self.metadata.version = value

    def _parse_difficulty(self, line: str):
        if ':' not in line:
            return
        key, value = line.split(':', 1)
        key, value = key.strip(), value.strip()

        if key == 'CircleSize':
            try:
                self.circle_size = float(value)
            except ValueError:
                pass

    def _parse_timing_point(self, line: str):
        parts = line.split(',')
        if len(parts) < 2:
            return

        try:
            time = float(parts[0])
            beat_length = float(parts[1])
            meter = int(parts[2]) if len(parts) > 2 and parts[2] else 4
            sample_set = int(parts[3]) if len(parts) > 3 and parts[3] else 0
            sample_index = int(parts[4]) if len(parts) > 4 and parts[4] else 0
            volume = int(parts[5]) if len(parts) > 5 and parts[5] else 100
            uninherited = len(parts) <= 6 or parts[6] == '1'
            effects = int(parts[7]) if len(parts) > 7 else 0

            # skip invalid sh
            if not uninherited and beat_length > 0:
                return

            timing_point = TimingPoint(
                time=time,
                beat_length=beat_length,
                meter=meter,
                sample_set=sample_set,
                sample_index=sample_index,
                volume=volume,
                uninherited=uninherited,
                effects=effects
            )

            self.timing_points.append(timing_point)

        except (ValueError, IndexError):
            pass

    def _parse_hit_object(self, line: str):
        parts = line.split(',')
        if len(parts) < 5:
            return

        try:
            x = int(parts[0])
            y = int(parts[1])
            time = float(parts[2])
            obj_type = int(parts[3])
            hit_sound = int(parts[4])

            end_time = None
            # LNs
            if obj_type & 128:  # ln bit
                if len(parts) > 5:
                    # dont question this
                    end_time_str = parts[5].split(':')[0]
                    try:
                        end_time = float(end_time_str)
                    except ValueError:
                        pass

            hit_object = HitObject(
                x=x, y=y, time=time, type=obj_type,
                hit_sound=hit_sound, end_time=end_time
            )

            self.hit_objects.append(hit_object)

        except (ValueError, IndexError):
            pass

    @property
    def is_mania(self) -> bool:
        return self.mode == 3

    @property
    def key_count(self) -> int:
        if self.is_mania:
            return max(1, min(18, int(round(self.circle_size))))
        return 4


class StepManiaConverter:
    KEY_MODES = {
        1: 'dance-single',
        3: 'dance-single',
        4: 'dance-single',
        5: 'pump-single',
        6: 'dance-solo',
        7: 'kb7-single',
        8: 'dance-double',
        9: 'kb7-single',
        10: 'dance-double'
    }

    def __init__(self, quantization: int = 192):
        self.quantization = quantization

    def convert(self, beatmap: OsuBeatmap, output_path: str) -> Dict:
        if not beatmap.is_mania:
            return {
                'success': False,
                'error': f'Only osu!mania maps supported (mode {beatmap.mode} found)'
            }

        try:
            # Generate StepMania content
            header = self._generate_header(beatmap)
            notes_section = self._generate_notes(beatmap)

            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(header)
                f.write(notes_section)

            return {
                'success': True,
                'output_path': output_path,
                'title': beatmap.metadata.title,
                'artist': beatmap.metadata.artist,
                'version': beatmap.metadata.version,
                'key_count': beatmap.key_count,
                'hit_objects': len(beatmap.hit_objects),
                'timing_points': len(beatmap.timing_points)
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Conversion failed: {str(e)}'
            }

    def _generate_header(self, beatmap: OsuBeatmap) -> str:

        # timing info
        uninherited_points = self._get_uninherited_timing_points(beatmap)

        if not uninherited_points:
            # fallback
            offset = 0.0
            bpms = "0.000=120.000"
        else:
            # offset
            first_timing = uninherited_points[0]
            offset = -first_timing.time / 1000.0

            # BPM CHANGES
            bpms = self._generate_bpms_string(uninherited_points)

        # start
        sample_start = 0.0
        if beatmap.metadata.preview_time >= 0:
            sample_start = beatmap.metadata.preview_time / 1000.0

        header = f"""#TITLE:{beatmap.metadata.title};
#ARTIST:{beatmap.metadata.artist};
#CREDIT:{beatmap.metadata.creator};
#MUSIC:{beatmap.metadata.audio_filename};
#OFFSET:{offset:.6f};
#SAMPLESTART:{sample_start:.6f};
#SAMPLELENGTH:12.000;
#SELECTABLE:YES;
#BPMS:{bpms};
#STOPS:;

"""
        return header

    def _generate_bpms_string(self, timing_points: List[TimingPoint]) -> str:
        if not timing_points:
            return "0.000=120.000"

        bpm_changes = []
        cumulative_beats = 0.0

        for i, tp in enumerate(timing_points):
            # Calculate BPM
            bpm = 60000.0 / tp.beat_length if tp.beat_length > 0 else 120.0

            # Add BPM change
            bpm_changes.append(f"{cumulative_beats:.3f}={bpm:.3f}")

            # Calculate beats until next timing point
            if i + 1 < len(timing_points):
                next_tp = timing_points[i + 1]
                time_diff = next_tp.time - tp.time
                beats_diff = time_diff / tp.beat_length
                cumulative_beats += beats_diff

        return ','.join(bpm_changes)

    def _generate_notes(self, beatmap: OsuBeatmap) -> str:
        key_count = beatmap.key_count
        game_mode = self.KEY_MODES.get(key_count, 'dance-single')

        # header
        notes_header = f"""//---------------{game_mode} - {beatmap.metadata.version}----------------
#NOTES:
     {game_mode}:
     :
     Challenge:
     1:
     0,0,0,0,0:
"""

        # note data generation
        measures = self._generate_measures(beatmap)
        measures_str = '\n'.join(measures)

        return notes_header + measures_str + '\n;\n'

    def _generate_measures(self, beatmap: OsuBeatmap) -> List[str]:
        key_count = beatmap.key_count

        uninherited_points = self._get_uninherited_timing_points(beatmap)

        if not uninherited_points:
            empty_row = '0' * key_count
            return [empty_row] * self.quantization + [',']

        note_grid = defaultdict(lambda: ['0'] * key_count)

        for hit_obj in beatmap.hit_objects:
            beat_pos = self._time_to_beat(hit_obj.time, uninherited_points)
            row = self._beat_to_row(beat_pos)
            col = self._x_to_column(hit_obj.x, key_count)

            if hit_obj.is_hold and hit_obj.end_time:
                # ln start
                note_grid[row][col] = '2'

                # ln end
                end_beat_pos = self._time_to_beat(hit_obj.end_time, uninherited_points)
                end_row = self._beat_to_row(end_beat_pos)
                note_grid[end_row][col] = '3'
            else:
                # note
                note_grid[row][col] = '1'

        if not note_grid:
            empty_row = '0' * key_count
            return [empty_row] * self.quantization + [',']

        max_row = max(note_grid.keys()) if note_grid else 0
        max_measure = (max_row // self.quantization) + 1

        measures = []
        for measure in range(max_measure):
            for row_in_measure in range(self.quantization):
                global_row = measure * self.quantization + row_in_measure
                row_data = note_grid.get(global_row, ['0'] * key_count)
                measures.append(''.join(row_data))

            measures.append(',')

        return measures

    def _get_uninherited_timing_points(self, beatmap: OsuBeatmap) -> List[TimingPoint]:
        uninherited = [tp for tp in beatmap.timing_points
                      if tp.uninherited and tp.beat_length > 0]
        return sorted(uninherited, key=lambda x: x.time)

    def _time_to_beat(self, time_ms: float, timing_points: List[TimingPoint]) -> float:
        #ms to beat convert
        if not timing_points:
            return 0.0

        active_tp = timing_points[0]
        beats_elapsed = 0.0

        for i, tp in enumerate(timing_points):
            if time_ms >= tp.time:
                active_tp = tp
                if i > 0:
                    prev_tp = timing_points[i-1]
                    time_diff = tp.time - prev_tp.time
                    beats_elapsed += time_diff / prev_tp.beat_length
            else:
                break

        time_in_section = time_ms - active_tp.time
        beats_in_section = time_in_section / active_tp.beat_length

        return beats_elapsed + beats_in_section

    def _beat_to_row(self, beat: float) -> int:
        # 1 measure = 4 beats
        measure = int(beat // 4)
        beat_in_measure = beat % 4
        row_in_measure = int((beat_in_measure / 4) * self.quantization)

        row_in_measure = max(0, min(self.quantization - 1, row_in_measure))

        return measure * self.quantization + row_in_measure

    def _x_to_column(self, x: int, key_count: int) -> int:
        x_normalized = max(0, min(511, x)) / 512.0
        column = int(x_normalized * key_count)

        return max(0, min(key_count - 1, column))


def convert_osu_to_stepmania(osu_file: str, sm_file: str, quantization: int = 192) -> Dict:

    if not os.path.exists(osu_file):
        return {'success': False, 'error': f'Input file not found: {osu_file}'}

    try:
        beatmap = OsuBeatmap.from_file(osu_file)
        converter = StepManiaConverter(quantization=quantization)
        result = converter.convert(beatmap, sm_file)

        return result

    except Exception as e:
        return {'success': False, 'error': f'Conversion error: {str(e)}'}


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python osu_to_sm.py <input.osu> <output.sm> [quantization]")
        print("  quantization: Notes per measure (default: 192)")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    quant = int(sys.argv[3]) if len(sys.argv) > 3 else 192

    result = convert_osu_to_stepmania(input_file, output_file, quant)

    if result['success']:
        print("✓ Conversion successful!")
        print(f"  Title: {result['title']}")
        print(f"  Artist: {result['artist']}")
        print(f"  Version: {result['version']}")
        print(f"  Keys: {result['key_count']}")
        print(f"  Objects: {result['hit_objects']}")
        print(f"  Output: {result['output_path']}")
    else:
        print(f"✗ Conversion failed: {result['error']}")
        sys.exit(1)

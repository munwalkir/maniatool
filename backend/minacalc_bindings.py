import ctypes
import os
import re
from typing import List, Tuple, Optional
from pathlib import Path
import traceback

# c structure definition
class NoteInfo(ctypes.Structure):
    _fields_ = [
        ("notes", ctypes.c_int),
        ("rowTime", ctypes.c_float)
    ]

class Ssr(ctypes.Structure):
    _fields_ = [
        ("overall", ctypes.c_float),
        ("stream", ctypes.c_float),
        ("jumpstream", ctypes.c_float),
        ("handstream", ctypes.c_float),
        ("stamina", ctypes.c_float),
        ("jackspeed", ctypes.c_float),
        ("chordjack", ctypes.c_float),
        ("technical", ctypes.c_float)
    ]

class MsdForAllRates(ctypes.Structure):
    _fields_ = [
        ("msds", Ssr * 14)  # one for each full-rate from 0.7 to 2.0 inclusive (useless tbh)
    ]

class MinaCalc:
    """py wrapper for c api"""

    def __init__(self, library_path: Optional[str] = None):
        if library_path is None:
            current_dir = Path(__file__).parent
            library_path = current_dir / "minacalc" / "libminacalc.so"
            # try parent
            if not os.path.exists(library_path):
                library_path = current_dir.parent / "minacalc" / "libminacalc.so"

        if not os.path.exists(library_path):
            raise FileNotFoundError(f"MinaCalc library not found at {library_path}")

        self.lib = ctypes.CDLL(str(library_path))
        self._setup_function_signatures()

        self.calc_handle = self.lib.create_calc()
        if not self.calc_handle:
            raise RuntimeError("Failed to create MinaCalc handle")

    def _setup_function_signatures(self):
        self.lib.calc_version.argtypes = []
        self.lib.calc_version.restype = ctypes.c_int

        self.lib.create_calc.argtypes = []
        self.lib.create_calc.restype = ctypes.c_void_p

        self.lib.destroy_calc.argtypes = [ctypes.c_void_p]
        self.lib.destroy_calc.restype = None

        self.lib.calc_msd.argtypes = [ctypes.c_void_p, ctypes.POINTER(NoteInfo), ctypes.c_size_t]
        self.lib.calc_msd.restype = MsdForAllRates

        self.lib.calc_ssr.argtypes = [ctypes.c_void_p, ctypes.POINTER(NoteInfo), ctypes.c_size_t, ctypes.c_float, ctypes.c_float]
        self.lib.calc_ssr.restype = Ssr

    def get_version(self) -> int:
        """minacalc ver check"""
        return self.lib.calc_version()

    def calculate_msd(self, note_data: List[Tuple[int, float]]) -> dict:
        """MSD just for compatibility"""
        if not note_data:
            return {k: 0.0 for k in ['overall', 'stream', 'jumpstream', 'handstream',
                                     'stamina', 'jackspeed', 'chordjack', 'technical']}

        valid_note_data = []
        for i, (notes, row_time) in enumerate(note_data):
            if notes < 0:
                print(f"Warning: Invalid notes value at index {i}: notes={notes}, skipping")
                continue
            if row_time < 0:
                print(f"Warning: Negative row_time at index {i}: row_time={row_time}, adjusting to 0.0")
                row_time = max(0.0, row_time)
            valid_note_data.append((notes, row_time))

        if not valid_note_data:
            print("Warning: No valid note data after filtering")
            return {k: 0.0 for k in ['overall', 'stream', 'jumpstream', 'handstream',
                                     'stamina', 'jackspeed', 'chordjack', 'technical']}

        note_array = (NoteInfo * len(valid_note_data))()
        for i, (notes, row_time) in enumerate(valid_note_data):
            note_array[i].notes = notes
            note_array[i].rowTime = ctypes.c_float(row_time)

        result = self.lib.calc_msd(self.calc_handle, note_array, len(valid_note_data))
        rate_1_0_index = 3  # 1.0x rate index
        ssr = result.msds[rate_1_0_index]

        return {
            'overall': ssr.overall,
            'stream': ssr.stream,
            'jumpstream': ssr.jumpstream,
            'handstream': ssr.handstream,
            'stamina': ssr.stamina,
            'jackspeed': ssr.jackspeed,
            'chordjack': ssr.chordjack,
            'technical': ssr.technical
        }

    def calculate_ssr(self, note_data: List[Tuple[int, float]], music_rate: float = 1.0, score_goal: float = 0.93) -> dict:
        #would make score_goal 1.0 but i dont trust myself
        if not note_data:
            return {k: 0.0 for k in ['overall', 'stream', 'jumpstream', 'handstream',
                                     'stamina', 'jackspeed', 'chordjack', 'technical']}

        valid_note_data = []
        for i, (notes, row_time) in enumerate(note_data):
            if notes < 0:
                print(f"Warning: Invalid notes value at index {i}: notes={notes}, skipping")
                continue
            if row_time < 0:
                print(f"Warning: Negative row_time at index {i}: row_time={row_time}, adjusting to 0.0")
                row_time = max(0.0, row_time)
            valid_note_data.append((notes, row_time))

        if not valid_note_data:
            print("Warning: No valid note data after filtering")
            return {k: 0.0 for k in ['overall', 'stream', 'jumpstream', 'handstream',
                                     'stamina', 'jackspeed', 'chordjack', 'technical']}

        note_array = (NoteInfo * len(valid_note_data))()
        for i, (notes, row_time) in enumerate(valid_note_data):
            note_array[i].notes = notes
            note_array[i].rowTime = ctypes.c_float(row_time)

        result = self.lib.calc_ssr(self.calc_handle, note_array, len(valid_note_data),
                                  ctypes.c_float(music_rate), ctypes.c_float(score_goal))

        return {
            'overall': result.overall,
            'stream': result.stream,
            'jumpstream': result.jumpstream,
            'handstream': result.handstream,
            'stamina': result.stamina,
            'jackspeed': result.jackspeed,
            'chordjack': result.chordjack,
            'technical': result.technical
        }

    def __del__(self):
        if hasattr(self, 'calc_handle') and self.calc_handle:
            self.lib.destroy_calc(self.calc_handle)

def parse_sm_file(sm_file_path: str) -> List[Tuple[int, float]]:
    note_data = []

    try:
        with open(sm_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        sections = re.split(r'#([A-Z]+):', content)
        metadata = {}
        for i in range(1, len(sections), 2):
            key = sections[i]
            value = sections[i+1].split(';')[0].strip() if i+1 < len(sections) else ''
            metadata[key] = value

        print(f"Parsing SM file: {sm_file_path}")

        bpms = {}
        if 'BPMS' in metadata:
            print(f"BPMs found: {metadata['BPMS']}")
            for bpm_entry in metadata['BPMS'].split(','):
                bpm_entry = bpm_entry.strip()
                if not bpm_entry:
                    continue
                if '=' in bpm_entry:
                    beat_str, bpm_str = bpm_entry.split('=', 1)
                    try:
                        beat = float(beat_str.strip())
                        bpm = float(bpm_str.strip())
                        if bpm <= 0 or bpm > 1000:
                            print(f"  Warning: Suspicious BPM value {bpm}, using 120 instead")
                            bpm = 120.0
                        bpms[beat] = bpm
                        print(f"  BPM change: beat {beat} -> {bpm} BPM")
                    except (ValueError, TypeError):
                        print(f"  Invalid BPM entry: {bpm_entry}")
                        continue
        else:
            print("No BPMs found in metadata")

        offset = 0.0
        if 'OFFSET' in metadata:
            try:
                offset = float(metadata['OFFSET'].strip())
                print(f"Offset: {offset}")
            except (ValueError, TypeError):
                offset = 0.0
                print("Invalid offset, using 0.0")
        else:
            print("No offset found, using 0.0")

        if 'NOTES' not in metadata:
            print("No NOTES section found")
            return note_data

        notes_section = metadata['NOTES']
        if not notes_section:
            print("Empty NOTES section")
            return note_data

        measures = []
        current_measure = []
        for line in notes_section.split('\n'):
            line = line.strip()
            if not line or line.startswith('//'):
                continue

            if line in (',', ';'):
                if current_measure:
                    measures.append(current_measure)
                    current_measure = []
                if line == ';':
                    break
                continue

            current_measure.append(line)

        if current_measure:
            measures.append(current_measure)

        print(f"Found {len(measures)} measures")

        sorted_bpms = sorted(bpms.items())
        if not sorted_bpms:
            sorted_bpms = [(0.0, 120.0)]
            print("No BPMs found, using default 120 BPM")

        print(f"Using BPM changes: {sorted_bpms}")

        current_beat = 0.0
        current_time = abs(offset)
        active_lns = set()

        for measure_idx, measure in enumerate(measures):
            rows = len(measure)
            if rows == 0:
                current_beat += 4.0
                bpm = get_bpm_at_beat(current_beat, sorted_bpms)
                current_time += (4.0 * 60.0 / bpm)
                continue

            for row_idx, row in enumerate(measure):
                if not row or len(row) > 100:
                    continue

                beat_in_measure = 4.0 * row_idx / rows
                absolute_beat = current_beat + beat_in_measure

                bpm_at_beat = get_bpm_at_beat(absolute_beat, sorted_bpms)
                beat_duration = 60.0 / bpm_at_beat
                time_in_measure = beat_in_measure * beat_duration
                absolute_time = abs(offset) + calculate_time_for_beat(absolute_beat, sorted_bpms, abs(offset))

                notes_bitmask = 0
                note_count = 0
                ln_starts = 0
                ln_ends = 0

                for col_idx, char in enumerate(row):
                    if col_idx >= 32:
                        break

                    if char == '1':  # note
                        notes_bitmask |= (1 << col_idx)
                        note_count += 1
                    elif char == '2':  # LN start
                        notes_bitmask |= (1 << col_idx)
                        note_count += 1
                        ln_starts += 1
                        active_lns.add(col_idx)
                    elif char == '3':  # LN end
                        ln_ends += 1
                        if col_idx in active_lns:
                            active_lns.remove(col_idx)
                    # skip mines and other characters

                if notes_bitmask != 0:
                    if absolute_time >= 0 and absolute_time < 3600:
                        note_data.append((notes_bitmask, absolute_time))
                        if len(note_data) <= 5:
                            print(f"  Note {len(note_data)}: beat={absolute_beat:.3f}, time={absolute_time:.3f}, bitmask={notes_bitmask}, notes={note_count}, LN_start={ln_starts}")

            current_beat += 4.0

        print(f"Parsed {len(note_data)} note events")

        note_data.sort(key=lambda x: x[1])

        filtered_notes = []
        prev_time = -1.0
        note_density_window = []

        for notes, time in note_data:
            if time == prev_time:
                continue

            note_density_window = [(t, n) for t, n in note_density_window if time - t < 0.1]
            note_density_window.append((time, bin(notes).count('1')))

            total_notes_in_window = sum(n for _, n in note_density_window)
            if total_notes_in_window > 300:  #spam asf
                print(f"Warning: High note density detected at time {time:.3f}, might be conversion artifact")
                continue

            filtered_notes.append((notes, time))
            prev_time = time

        print(f"Final note data: {len(filtered_notes)} valid notes (filtered from {len(note_data)})")
        if filtered_notes:
            print(f"First note: time={filtered_notes[0][1]:.3f}")
            print(f"Last note: time={filtered_notes[-1][1]:.3f}")

            song_length = filtered_notes[-1][1] - filtered_notes[0][1]
            if song_length > 1800: #long ass map
                print(f"Warning: Very long song detected ({song_length:.1f}s), might indicate timing issues")

        return filtered_notes

    except Exception as e:
        print(f"Error parsing SM file {sm_file_path}: {str(e)}")
        traceback.print_exc()
        return []

def get_bpm_at_beat(beat: float, sorted_bpms: List[Tuple[float, float]]) -> float:
    current_bpm = sorted_bpms[0][1]
    for bpm_beat, bpm_value in sorted_bpms:
        if beat >= bpm_beat:
            current_bpm = bpm_value
        else:
            break
    return current_bpm

def calculate_time_for_beat(target_beat: float, sorted_bpms: List[Tuple[float, float]], offset: float) -> float:
    if not sorted_bpms:
        return offset + (target_beat * 60.0 / 120.0)

    current_time = offset
    current_beat = 0.0

    for i, (bpm_beat, bpm_value) in enumerate(sorted_bpms):
        if target_beat <= bpm_beat:
            remaining_beats = target_beat - current_beat
            current_time += (remaining_beats * 60.0 / get_previous_bpm(i, sorted_bpms))
            return current_time
        else:
            if i == 0:
                beat_duration = bpm_beat - current_beat
                prev_bpm = bpm_value
            else:
                beat_duration = bpm_beat - current_beat
                prev_bpm = sorted_bpms[i-1][1]

            current_time += (beat_duration * 60.0 / prev_bpm)
            current_beat = bpm_beat

    if target_beat > current_beat:
        remaining_beats = target_beat - current_beat
        last_bpm = sorted_bpms[-1][1]
        current_time += (remaining_beats * 60.0 / last_bpm)

    return current_time

def get_previous_bpm(index: int, sorted_bpms: List[Tuple[float, float]]) -> float:
    if index == 0:
        return sorted_bpms[0][1]
    else:
        return sorted_bpms[index-1][1]

if __name__ == "__main__":
    try:
        calc = MinaCalc()
        print(f"MinaCalc version: {calc.get_version()}")

        example_notes = [
            (1, 0.0),
            (2, 0.5),
            (5, 1.0),
            (8, 1.5),
        ]

        # ssr calc
        ssr_result = calc.calculate_ssr(example_notes, music_rate=1.0, score_goal=0.93)
        print("SSR Results:", ssr_result)

        # msd for compatibility
        msd_result = calc.calculate_msd(example_notes)
        print("MSD Results:", msd_result)

    except Exception as e:
        print(f"Error: {e}")

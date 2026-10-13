#!/usr/bin/env python3
"""Local vocal separation and melody transcription. See README.md."""
import json
import argparse
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from guitar_tabs import export_tabs


class PipelineError(Exception):
    pass


def run_command(command, timeout):
    try:
        subprocess.run(command, check=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise PipelineError(f'Stage exceeded {timeout} seconds; increase --timeout.') from exc
    except subprocess.CalledProcessError as exc:
        raise PipelineError(f'{Path(command[0]).name} failed (exit {exc.returncode}); see output above.') from exc


def transcribe(wav, midi):
    from basic_pitch import FilenameSuffix, build_icassp_2022_model_path
    from basic_pitch.inference import predict
    _, midi_data, notes = predict(str(wav), model_or_model_path=build_icassp_2022_model_path(FilenameSuffix.onnx))
    midi_data.write(str(midi))
    if not notes:
        print('Warning: no pitched notes detected; MIDI is empty.', file=sys.stderr)


def parser():
    p = argparse.ArgumentParser(description='Extract vocals as MP3 and detected vocal notes as MIDI and lyric-aligned text guitar tabs, locally.')
    p.add_argument('input', type=Path, help='Input MP3 file, or existing MIDI with --midi-only')
    p.add_argument('-o', '--output-dir', type=Path, default=Path(__file__).resolve().parent / 'output')
    p.add_argument('--midi-only', action='store_true', help='Convert existing MIDI plus vocal audio to lyric-aligned tabs without repeating separation')
    p.add_argument('--vocals', type=Path, help='Vocal audio for --midi-only; defaults to a sibling MP3 with the same stem')
    p.add_argument('--timeout', type=int, default=3600, help='Maximum seconds per processing stage (default: 3600)')
    return p


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    source = args.input.expanduser().resolve()
    if not source.is_file():
        p.error(f'Input is not a regular file: {source}')
    extensions = ('.mid', '.midi') if args.midi_only else ('.mp3',)
    if source.suffix.lower() not in extensions:
        p.error(f'Input must have one of these extensions: {extensions}')
    if source.stat().st_size == 0:
        p.error('Input file is empty.')
    if args.timeout <= 0:
        p.error('--timeout must be a positive integer.')
    result = None
    try:
        if args.midi_only:
            root = args.output_dir.expanduser().resolve()
            root.mkdir(parents=True, exist_ok=True)
            result = Path(tempfile.mkdtemp(prefix='tabs-', dir=root))
            audio = (args.vocals.expanduser().resolve() if args.vocals else source.with_suffix('.mp3'))
            if not audio.is_file():
                raise PipelineError('Lyrics require vocal audio. Supply --vocals path/to/vocals.mp3 with --midi-only.')
            lyric_path = result / f'{source.stem}_lyrics.json'
            run_command([sys.executable, str(Path(__file__).resolve()), '--_lyrics', str(audio), str(lyric_path)], args.timeout)
            tab = export_tabs(source, result / f'{source.stem}.txt', json.loads(lyric_path.read_text())['words'])
            print(f'Tabs:   {tab}\nLyrics: {lyric_path.with_suffix(".txt")}')
            return 0
        for binary in ('ffmpeg', 'ffprobe'):
            if not shutil.which(binary):
                raise PipelineError(f'{binary} is missing. Install with: brew install ffmpeg')
        for package in ('demucs', 'basic_pitch', 'onnxruntime', 'faster_whisper'):
            if importlib.util.find_spec(package) is None:
                raise PipelineError(f'{package} is missing. Activate .venv and run: python -m pip install -r requirements.txt')
        # Decode first: rejects corrupt files and gives Demucs a predictable WAV input.
        root = args.output_dir.expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        name = re.sub(r'[^\w .-]', '_', source.stem).strip(' .')[:100] or 'audio'
        result = Path(tempfile.mkdtemp(prefix=f'{name}-', dir=root))
        with tempfile.TemporaryDirectory(prefix='work-', dir=result) as workdir:
            work = Path(workdir)
            wav = work / 'input.wav'
            print('1/5 Decoding input and separating vocals (first run downloads model weights)…', flush=True)
            run_command(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source), '-map', '0:a:0', '-ac', '2', '-ar', '44100', str(wav)], args.timeout)
            run_command([sys.executable, '-m', 'demucs', '-n', 'htdemucs', '--two-stems', 'vocals', '--shifts', '0', '-d', 'cpu', '-o', str(work / 'stems'), str(wav)], args.timeout)
            vocals = work / 'stems' / 'htdemucs' / 'input' / 'vocals.wav'
            if not vocals.is_file():
                raise PipelineError('Demucs did not produce the expected vocals.wav.')
            print('2/5 Exporting isolated vocals MP3…', flush=True)
            mp3 = result / f'{name}_vocals.mp3'
            run_command(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(vocals), '-codec:a', 'libmp3lame', '-q:a', '2', str(mp3)], args.timeout)
            print('3/5 Transcribing vocal notes…', flush=True)
            midi = result / f'{name}_vocals.mid'
            temporary_midi = work / 'notes.mid'
            run_command([sys.executable, str(Path(__file__).resolve()), '--_transcribe', str(vocals), str(temporary_midi)], args.timeout)
            if not temporary_midi.is_file() or temporary_midi.read_bytes()[:4] != b'MThd':
                raise PipelineError('Transcription did not produce a valid MIDI header.')
            temporary_midi.replace(midi)
            print('4/5 Transcribing lyrics locally (first run downloads Whisper small)…', flush=True)
            lyric_path = result / f'{name}_lyrics.json'
            run_command([sys.executable, str(Path(__file__).resolve()), '--_lyrics', str(vocals), str(lyric_path)], args.timeout)
        print('5/5 Aligning lyrics and exporting guitar tablature…', flush=True)
        tab = export_tabs(midi, result / f'{name}_vocals.txt', json.loads(lyric_path.read_text())['words'])
        print(f'Vocals: {mp3}\nMIDI:   {midi}\nTabs:   {tab}\nLyrics: {lyric_path.with_suffix(".txt")}')
        return 0
    except (PipelineError, OSError, ValueError, ImportError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        if result:
            print(f'Partial outputs (if any): {result}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(f'Cancelled. Partial outputs: {result or "none"}', file=sys.stderr)
        return 130


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] in ('--_transcribe', '--_lyrics'):
        try:
            if sys.argv[1] == '--_lyrics':
                from lyrics import transcribe_lyrics
                transcribe_lyrics(Path(sys.argv[2]), Path(sys.argv[3]))
            else:
                transcribe(Path(sys.argv[2]), Path(sys.argv[3]))
        except Exception as exc:
            print(f'Transcription failed: {exc}', file=sys.stderr)
            sys.exit(1)
    else:
        sys.exit(main())

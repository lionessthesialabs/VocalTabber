# Vocaltabber

One MP3 in → isolated vocals MP3 + detected vocal notes MIDI + text guitar tablature. Runs locally using Demucs (htdemucs, CPU) and Basic Pitch (explicit ONNX runtime). No account or hosted inference. Demucs downloads model weights on the first run; subsequent runs can work offline with the cached weights. Audio is not uploaded.

## Install (macOS Apple Silicon)

Use Python 3.11 in a dedicated environment; do not install these older ML packages into your global Python 3.13 environment.

```sh
brew install python@3.11 ffmpeg
cd ~/desktop/projects/vocaltabber
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

```sh
cd ~/desktop/projects/vocaltabber
source .venv/bin/activate
python vocaltabber.py "/absolute/path/file.mp3"
```

Outputs go in `output/file-<unique suffix>/file_vocals.mp3` , `file_vocals.mid`, and `file_vocals.txt` beside the script. Each run gets its own directory, so existing files are never overwritten. The full output paths are printed on completion.

```sh
python vocaltabber.py file.mp3 --output-dir ~/Music/Vocaltabber --timeout 7200
python vocaltabber.py --help
```

Processing is CPU-based for compatibility and may take several minutes per song. The timeout applies separately to each stage. Temporary uncompressed stems are removed after processing; a successfully exported MP3 remains available if transcription fails. MIDI uses the lossless vocal stem, not the exported MP3. No input files are modified.

## Expectations and troubleshooting

MIDI and the derived text tabs are best-effort transcriptions: harmonies, backing vocals, leakage, vibrato and unpitched speech can cause overlapping, missed or extra notes. No forced monophonic filtering is applied. An empty transcription produces a valid empty MIDI with a warning. Check/edit results in your DAW. MIDI contains notes, not recorded singing.

Missing module: activate `.venv` and reinstall requirements. Missing ffmpeg/ffprobe: `brew install ffmpeg`. First-run network/model-download failures: restore connectivity and retry. Corrupt or non-audio MP3s fail during decoding. Failures return a nonzero exit status and identify any partial output directory. Use audio you have permission to process.

Upstream documentation: [Demucs](https://github.com/facebookresearch/demucs), [Basic Pitch](https://github.com/spotify/basic-pitch).

## Verification

Tested locally on Apple Silicon with Python 3.11.14: full Demucs → MP3 → Basic Pitch ONNX → MIDI pipeline completed on a generated four-second 220 Hz test tone. MP3 decoded successfully and MIDI parsed successfully with detected notes. This is a plumbing smoke test, not a measurement of real singing accuracy. Five regression tests cover missing/empty/wrong-extension inputs, invalid timeouts, subprocess failure and timeout handling:

```sh
python -m unittest discover -v
```

All dependencies are already installed in `.venv` on this machine, and Demucs weights are cached. `requirements-lock.txt` records the tested environment; for a reproducible Python 3.11 installation use `python -m pip install -r requirements-lock.txt`. Basic Pitch may print warnings about unused TensorFlow/TFLite/CoreML backends; the script explicitly uses ONNX. Setuptools is pinned below 81 because resampy uses its legacy pkg_resources module.

## Text guitar tabs

Normal MP3 runs now also produce `<name>_vocals.txt`. Convert an existing MIDI without repeating separation or transcription:

```sh
python vocaltabber.py --midi-only "output/slowdancing-1yj2n25w/slowdancing_vocals.mid"
```

MIDI-only exports go into a new `output/tabs-<unique suffix>/` folder (or under `--output-dir`). The local faster-whisper dependency is required for lyrics. Standard tuning E2 A2 D3 G3 B3 E4, frets 0–24; the top row is the high e string. Each numbered column is one note, with exact onset/duration seconds in a table below each block. Spacing is not proportional to rhythm. A simple heuristic favors nearby frets and strings, but does not guarantee optimal fingering.

All non-drum notes are retained, including overlaps (flagged in the timing table); this is not automatic lead-vocal selection or chord arrangement. Out-of-range notes are marked OUT without octave shifting. Pitch bends are omitted. The MIDI remains unchanged. Nine regression tests pass, covering pitch preservation across the guitar range, overlaps, empty/invalid MIDI, overwrite protection, and existing CLI validation.

## Default lyrics and alignment

Every MP3 run now performs local lyric transcription with faster-whisper's multilingual `small` model on CPU (int8), then aligns its word timestamps with MIDI notes. No opt-in flag is needed and transcription failures return an error, preserving completed audio/MIDI outputs. First use downloads model weights from Hugging Face; later use works with the cached model. Audio stays local.

The normal command is unchanged: `python vocaltabber.py file.mp3`. Outputs include vocals MP3, MIDI, lyric-aligned tab TXT, and separate `_lyrics.txt` / `_lyrics.json` files with word timing and model confidence. Lyrics appear above the corresponding note columns; `~` means a word continues. Words without overlapping notes remain listed separately. Singing recognition and timestamps are approximate and may contain omissions or invented words, especially during instrumental passages. Review against the audio; confidence is not a guarantee of correctness.

Existing MIDI runs also transcribe lyrics: the matching sibling MP3 must exist, or pass `--vocals /path/to/isolated-vocals.mp3`. The audio and MIDI must share the same timeline. There is no lyrics-skip flag. Speech activity filtering is disabled to avoid clipping sustained singing.

Implementation follows [faster-whisper's word timestamp API](https://github.com/SYSTRAN/faster-whisper). Install/update using `python -m pip install -r requirements.txt`.

"""Local word transcription and deterministic temporal alignment."""
import json
from pathlib import Path


def transcribe_lyrics(audio, output):
    from faster_whisper import WhisperModel
    model = WhisperModel('small', device='cpu', compute_type='int8', cpu_threads=4)
    segments, info = model.transcribe(str(audio), word_timestamps=True,
                                     condition_on_previous_text=False, vad_filter=False,
                                     beam_size=5)
    words = []
    for segment in segments:
        print(f'Lyrics: processed through {segment.end:.1f}s', flush=True)
        for word in segment.words or []:
            text = ' '.join(word.word.split())
            if text:
                words.append(dict(text=text, start=float(word.start), end=float(word.end),
                                  probability=float(word.probability)))
    data = dict(model='faster-whisper/small', language=info.language, words=words)
    Path(output).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['Automatic lyric transcription — review singing recognition and timing.',
             f'Language: {info.language}', '']
    lines += [f"{w['start']:.3f}–{w['end']:.3f}  {w['text']}" for w in words]
    if not words:
        lines.append('No words detected.')
    Path(output).with_suffix('.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def align_words(notes, words):
    """Anchor each word at its first overlapping note; retain unaligned words."""
    labels = [''] * len(notes)
    unmatched = []
    for word in words:
        indices = [i for i, n in enumerate(notes)
                   if min(n.end, word['end']) > max(n.start, word['start'])]
        if not indices:
            unmatched.append(word)
            continue
        first = indices[0]
        labels[first] = (labels[first] + ' ' + word['text']).strip()
        for i in indices[1:]:
            if not labels[i]:
                labels[i] = '~'
    return labels, unmatched

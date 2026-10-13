"""Deterministic MIDI-to-standard-guitar ASCII tablature."""
from pathlib import Path

# String order matches printed tab, highest string first.
TUNING = (64, 59, 55, 50, 45, 40)
LABELS = ('e', 'B', 'G', 'D', 'A', 'E')


def choose_position(pitch, previous=None):
    candidates = [(string, pitch - base) for string, base in enumerate(TUNING)
                  if 0 <= pitch - base <= 24]
    if not candidates:
        return None
    def cost(position):
        string, fret = position
        if previous is None:
            return (fret, string)
        return (abs(fret - previous[1]) + 2 * abs(string - previous[0]), fret, string)
    return min(candidates, key=cost)


def render_tab(midi, title, words=None):
    notes = sorted((n for instrument in midi.instruments if not instrument.is_drum
                    for n in instrument.notes), key=lambda n: (n.start, n.pitch, n.end))
    lines = [f'Guitar tablature: {title}', 'Standard tuning: E2 A2 D3 G3 B3 E4; frets 0–24.',
             'Each column is one detected note, ordered by onset (not a rhythmic grid).',
             'Timing and duration in seconds appear below each block.',
             'Overlapping notes are retained as separate columns, not arranged into chords.',
             'Fingering uses a simple movement heuristic; edit for comfort.',
             'Pitches are not transposed. OUT means outside E2–E6; bends are not rendered.', '']
    from lyrics import align_words
    labels, unmatched = align_words(notes, words or [])
    if words is not None:
        lines += ['Lyrics are automatic; ~ continues a word. Alignment is approximate.',
                  'No words detected.' if not words else '', '']
    if unmatched:
        lines += ['Words without overlapping notes:'] + [f"{w['start']:.3f}s: {w['text']}" for w in unmatched] + ['']
    if not notes:
        return '\n'.join(lines + ['No pitched notes detected.', ''])
    positions = []
    previous = None
    for note in notes:
        position = choose_position(note.pitch, previous)
        positions.append(position)
        if position is not None:
            previous = position
    active_end = 0.0
    overlaps = []
    for note in notes:
        overlaps.append(note.start < active_end - 1e-6)
        active_end = max(active_end, note.end)
    for start in range(0, len(notes), 12):
        stop = min(start + 12, len(notes))
        width = max(5, len(str(stop)) + 1, max((len(x)+2 for x in labels[start:stop]), default=5))
        if words is not None:
            lines.append('  ' + ''.join(x.center(width) for x in labels[start:stop]))
        lines.append(' #' + ''.join(str(i + 1).center(width) for i in range(start, stop)))
        for string, label in enumerate(LABELS):
            cells = []
            for position in positions[start:stop]:
                value = str(position[1]) if position and position[0] == string else ''
                cells.append(value.center(width, '-'))
            lines.append(f'{label}|' + ''.join(cells) + '|')
        lines.append('Note | start(s) | duration(s) | MIDI pitch | string/fret | overlap')
        for i in range(start, stop):
            note, position = notes[i], positions[i]
            fingering = f'{LABELS[position[0]]}/{position[1]}' if position else 'OUT'
            lines.append(f'{i+1:4} | {note.start:8.3f} | {note.end-note.start:11.3f} | {note.pitch:10} | {fingering:11} | {"yes" if overlaps[i] else "no"}')
        lines.append('')
    return '\n'.join(lines)


def export_tabs(midi_path, output_path, words=None):
    import pretty_midi
    try:
        midi = pretty_midi.PrettyMIDI(str(midi_path))
        text = render_tab(midi, Path(midi_path).stem, words)
    except Exception as exc:
        raise ValueError(f'Cannot read MIDI for tablature: {exc}') from exc
    # Exclusive creation protects existing edits and previous exports.
    with Path(output_path).open('x', encoding='utf-8') as handle:
        handle.write(text)
    return Path(output_path)

import tempfile
from pathlib import Path
import unittest
import pretty_midi
from guitar_tabs import TUNING, choose_position, export_tabs, render_tab

class TabTests(unittest.TestCase):
    def test_every_playable_pitch_is_preserved(self):
        previous = None
        for pitch in range(40, 89):
            position = choose_position(pitch, previous)
            self.assertEqual(TUNING[position[0]] + position[1], pitch)
            self.assertTrue(0 <= position[1] <= 24)
            previous = position
        self.assertIsNone(choose_position(39))
        self.assertIsNone(choose_position(89))

    def test_roundtrip_overlap_range_and_no_overwrite(self):
        midi = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(0)
        instrument.notes = [pretty_midi.Note(100, 64, 0, 1), pretty_midi.Note(100, 67, .5, 1.5), pretty_midi.Note(100, 30, 2, 3)]
        midi.instruments.append(instrument)
        with tempfile.TemporaryDirectory() as d:
            source, target = Path(d)/'test.mid', Path(d)/'test.txt'
            midi.write(str(source))
            export_tabs(source, target)
            text = target.read_text()
            self.assertIn('OUT', text)
            self.assertIn('yes', text)
            self.assertIn('e|', text)
            with self.assertRaises(FileExistsError):
                export_tabs(source, target)

    def test_empty(self):
        self.assertIn('No pitched notes', render_tab(pretty_midi.PrettyMIDI(), 'empty'))

    def test_invalid_midi(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)/'broken.mid'
            source.write_text('not midi')
            with self.assertRaises(ValueError):
                export_tabs(source, Path(d)/'out.txt')

if __name__ == '__main__':
    unittest.main()

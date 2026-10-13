import unittest
from types import SimpleNamespace as N
from lyrics import align_words
from guitar_tabs import render_tab

class LyricsTests(unittest.TestCase):
    def test_sustained_word_and_unmatched(self):
        words = [dict(text='hello',start=0,end=2),dict(text='lost',start=3,end=4)]
        labels, unmatched = align_words([N(start=0,end=1),N(start=1,end=2)], words)
        self.assertEqual(labels,['hello','~'])
        self.assertEqual(unmatched,[words[1]])

    def test_multiple_words_one_note(self):
        labels,_ = align_words([N(start=0,end=2)], [dict(text='hi',start=0,end=1),dict(text='there',start=1,end=2)])
        self.assertEqual(labels,['hi there'])

    def test_empty_notes_preserve_lyrics(self):
        midi=N(instruments=[])
        text=render_tab(midi,'test',[dict(text='hello',start=1,end=2)])
        self.assertIn('hello',text)
        self.assertIn('No pitched notes',text)

    def test_empty_words(self):
        self.assertEqual(align_words([N(start=0,end=1)],[]),([''],[]))

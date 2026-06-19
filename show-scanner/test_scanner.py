import unittest
from datetime import date

import scanner


class ShowScannerDateWindowTests(unittest.TestCase):
    def test_parse_event_date_supports_known_formats(self):
        self.assertEqual(scanner.parse_event_date("June 20, 2026"), date(2026, 6, 20))
        self.assertEqual(scanner.parse_event_date("2026-06-20"), date(2026, 6, 20))
        self.assertEqual(scanner.parse_event_date("Jun 20, 2026"), date(2026, 6, 20))

    def test_filter_events_to_window_drops_past_and_far_future_events(self):
        events = [
            {"date": "June 18, 2026", "artist": "Past Show", "venue": "Fox Cabaret"},
            {"date": "June 19, 2026", "artist": "Today Show", "venue": "Fox Cabaret"},
            {"date": "June 25, 2026", "artist": "Next Week Show", "venue": "Fox Cabaret"},
            {"date": "July 15, 2026", "artist": "Far Future Show", "venue": "Fox Cabaret"},
            {"date": "TBD", "artist": "Undated Show", "venue": "Fox Cabaret"},
        ]

        filtered = scanner.filter_events_to_window(events, today=date(2026, 6, 19), weeks_ahead=3)
        artists = [event["artist"] for event in filtered]

        self.assertEqual(artists, ["Today Show", "Next Week Show", "Undated Show"])


if __name__ == "__main__":
    unittest.main()

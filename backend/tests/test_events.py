import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from codex_deck.events import EventStore, SqliteEventStore


class EventStoreTest(unittest.TestCase):
    def test_events_are_monotonic_filtered_and_bounded(self) -> None:
        store = EventStore(maximum_events=2)
        first = store.append(workspace_id="a", event_type="work.started")
        second = store.append(workspace_id="b", event_type="work.started")
        third = store.append(workspace_id="a", event_type="work.completed")

        self.assertEqual((first.event_id, second.event_id, third.event_id), (1, 2, 3))
        self.assertEqual([event.event_id for event in store.after(0)], [2, 3])
        self.assertEqual([event.event_id for event in store.after(0, workspace_id="a")], [3])

    def test_sqlite_events_survive_reopen(self) -> None:
        with TemporaryDirectory() as directory:
            database = Path(directory) / "deck.db"
            first_store = SqliteEventStore(database)
            first_store.append(workspace_id="a", event_type="work.started", payload={"workId": "work-1"})
            first_store.close()

            reopened = SqliteEventStore(database)
            events = reopened.after(0)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].payload, {"workId": "work-1"})
            reopened.close()


if __name__ == "__main__":
    unittest.main()

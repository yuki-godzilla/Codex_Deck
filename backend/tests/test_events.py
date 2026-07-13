import unittest

from codex_deck.events import EventStore


class EventStoreTest(unittest.TestCase):
    def test_events_are_monotonic_filtered_and_bounded(self) -> None:
        store = EventStore(maximum_events=2)
        first = store.append(workspace_id="a", event_type="work.started")
        second = store.append(workspace_id="b", event_type="work.started")
        third = store.append(workspace_id="a", event_type="work.completed")

        self.assertEqual((first.event_id, second.event_id, third.event_id), (1, 2, 3))
        self.assertEqual([event.event_id for event in store.after(0)], [2, 3])
        self.assertEqual([event.event_id for event in store.after(0, workspace_id="a")], [3])


if __name__ == "__main__":
    unittest.main()

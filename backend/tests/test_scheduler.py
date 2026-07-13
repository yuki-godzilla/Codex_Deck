import unittest

from codex_deck.scheduler import Scheduler, WorkState, WorkspaceBusyError


class SchedulerTest(unittest.TestCase):
    def test_same_workspace_is_rejected_without_queueing(self) -> None:
        scheduler = Scheduler()
        first = scheduler.acquire("workspace-a")

        with self.assertRaises(WorkspaceBusyError) as raised:
            scheduler.acquire("workspace-a")

        self.assertEqual(raised.exception.active_work.work_id, first.work_id)
        self.assertEqual(scheduler.get("workspace-a"), first)

    def test_distinct_workspaces_can_be_active(self) -> None:
        scheduler = Scheduler()
        first = scheduler.acquire("workspace-a")
        second = scheduler.acquire("workspace-b")

        self.assertNotEqual(first.work_id, second.work_id)

    def test_turn_and_state_are_attached_to_existing_work(self) -> None:
        scheduler = Scheduler()
        work = scheduler.acquire("workspace-a", thread_id="thread-1")
        threaded = scheduler.attach_thread(work.work_id, "thread-1")
        attached = scheduler.attach_turn(threaded.work_id, "turn-1")
        waiting = scheduler.set_state(attached.work_id, WorkState.WAITING_FOR_APPROVAL)

        self.assertEqual(waiting.thread_id, "thread-1")
        self.assertEqual(waiting.turn_id, "turn-1")
        self.assertEqual(waiting.state, WorkState.WAITING_FOR_APPROVAL)


if __name__ == "__main__":
    unittest.main()

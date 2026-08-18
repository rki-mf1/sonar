from unittest import mock
from unittest import TestCase

from celery import states

from rest_api.data_entry.sample_entry_job import _collect_celery_group_results


class FakeAsyncResult:
    def __init__(self, task_id, backend):
        self.id = task_id
        self.backend = backend
        self.forget = mock.Mock()


class FakeBackend:
    """Stands in for the Celery/Redis backend: get_task_meta() reads
    whatever state the test put in `metas`, no Redis involved."""

    def __init__(self, metas):
        self.metas = metas

    def get_task_meta(self, task_id):
        return self.metas[task_id]


class FakeGroupResult:
    def __init__(self, async_results):
        self.results = async_results
        self.forget = mock.Mock()


def make_group(count, backend):
    return FakeGroupResult(
        [FakeAsyncResult(f"task-{i}", backend) for i in range(count)]
    )


class CollectCeleryGroupResultsTest(TestCase):
    def test_all_success_preserves_order_and_forgets_everything(self):
        backend = FakeBackend(
            {
                "task-0": {"status": states.SUCCESS, "result": (True, "a", 0)},
                "task-1": {"status": states.SUCCESS, "result": (True, "b", 1)},
                "task-2": {"status": states.SUCCESS, "result": (True, "c", 2)},
            }
        )
        group_result = make_group(3, backend)

        results = _collect_celery_group_results(group_result)

        self.assertEqual(
            results,
            [(True, "a", 0), (True, "b", 1), (True, "c", 2)],
        )
        for async_result in group_result.results:
            async_result.forget.assert_called_once()
        group_result.forget.assert_called_once()

    def test_failure_reraises_original_exception_and_still_forgets_group(self):
        error = ValueError("boom")
        backend = FakeBackend(
            {
                "task-0": {"status": states.SUCCESS, "result": (True, "a", 0)},
                "task-1": {"status": states.FAILURE, "result": error},
            }
        )
        group_result = make_group(2, backend)

        with self.assertRaises(ValueError):
            _collect_celery_group_results(group_result)

        # cleanup must still happen even though we raised
        group_result.forget.assert_called_once()

    def test_non_exception_failure_result_raises_runtime_error(self):
        backend = FakeBackend(
            {"task-0": {"status": states.FAILURE, "result": "disk full"}}
        )
        group_result = make_group(1, backend)

        with self.assertRaisesRegex(RuntimeError, "disk full"):
            _collect_celery_group_results(group_result)

    def test_empty_group_returns_empty_list(self):
        backend = FakeBackend({})
        group_result = make_group(0, backend)

        results = _collect_celery_group_results(group_result)

        self.assertEqual(results, [])
        group_result.forget.assert_called_once()

    @mock.patch("rest_api.data_entry.sample_entry_job.time.sleep")
    def test_pending_task_is_polled_until_ready(self, mock_sleep):
        metas = {"task-0": {"status": states.PENDING, "result": None}}
        backend = FakeBackend(metas)
        group_result = make_group(1, backend)

        def flip_to_success(*_args, **_kwargs):
            metas["task-0"] = {"status": states.SUCCESS, "result": (True, "done")}

        mock_sleep.side_effect = flip_to_success

        results = _collect_celery_group_results(group_result, poll_interval_seconds=0)

        self.assertEqual(results, [(True, "done")])
        mock_sleep.assert_called_once()

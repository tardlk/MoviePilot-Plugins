"""分享转存队列离线验证：真实解析/持久化/编排，替代远端云盘和宿主识别。"""
import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

PATH = Path(__file__).resolve().parents[1] / 'plugins.v3/guangyasync/share_tasks.py'
spec = importlib.util.spec_from_file_location('share_tasks_tested', PATH)
share = importlib.util.module_from_spec(spec)
spec.loader.exec_module(share)
LINK = 'https://www.guangyapan.com/s/test_share_123?code=1234#/share'


class ParserTests(unittest.TestCase):
    def test_parse_link_markdown_and_separate_code(self):
        self.assertEqual(share.parse_share(f'[{LINK}]({LINK})'), ('test_share_123', '1234'))
        self.assertEqual(share.parse_share('资源 https://guangyapan.com/#/share/test_share_123 提取码：abcd'), ('test_share_123', 'abcd'))

    def test_reject_impostor_domain_and_multiple_shares(self):
        for text in ('https://evilguangyapan.com/s/test_share_123', 'https://guangyapan.com.evil.test/s/test_share_123',
                     LINK + ' https://guangyapan.com/s/second_share_123', 'http://localhost/s/test_share_123'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                share.parse_share(text)

    def test_whitelist_is_numeric_and_exact(self):
        self.assertTrue(share.allowed_user('123', '456，123'))
        self.assertFalse(share.allowed_user('12', '123'))
        self.assertFalse(share.allowed_user('', ''))
        self.assertFalse(share.allowed_user('admin', 'admin'))

    def test_invalid_directories_and_empty_whitelist_are_rejected(self):
        for config in ({'share_source_dir': '/'}, {'share_source_dir': '/Media/inbox'},
                       {'share_target_dir': '/待整理/out'}, {'share_source_dir': '/a/../b'},
                       {'telegram_enabled': True}, {'telegram_user_ids': '@name'}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                share.share_settings(config)

    def test_manifest_reads_nested_directories_and_total_size(self):
        client = Mock()
        client.share_files.side_effect = lambda token, parent, page: {'total': 1, 'list': [
            {'fileId': 'f1', 'fileName': 'A', 'resType': 2} if not parent else
            {'fileId': 'f2', 'fileName': 'movie.mkv', 'resType': 1, 'totalSize': 42}]}
        roots, manifest = share.read_manifest(client, 'private-token')
        self.assertEqual(roots, ['f1'])
        self.assertEqual(manifest['A/movie.mkv'], {'type': 'file', 'size': 42})

    def test_manifest_fails_closed_for_partial_page_cycle_and_bad_name(self):
        for data in ({'total': 2, 'list': [{'fileId': 'f', 'fileName': 'x', 'resType': 1}]},
                     {'total': 1, 'list': [{'fileId': 'f', 'fileName': '../escape', 'resType': 1}]},
                     {'total': 1, 'list': [{'fileId': 'f', 'fileName': 'loop', 'resType': 2}]}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                share.read_manifest(SimpleNamespace(share_files=lambda *_: data), 'token')


    def test_preview_rejects_numeric_year_misrecognition_and_failed_items(self):
        for ok, items in ((True, [{'success': True, 'title': '2026 (2024)', 'source': '/x/2026.IMAX.mkv'}]),
                          (False, [{'success': False}]), (True, [])):
            with self.subTest(items=items), self.assertRaises(ValueError):
                share.validate_preview(ok, {'items': items})
        share.validate_preview(True, {'items': [{'success': True, 'title': 'Example (2024)', 'source': '/x/Example.2024.mkv'}]})


class TelegramBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import ast
        tree = ast.parse(PATH.with_name('__init__.py').read_text())
        plugin = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'guangyasync')
        method = next(node for node in plugin.body if isinstance(node, ast.FunctionDef) and node.name == '_receive_share')
        namespace = {'allowed_user': share.allowed_user}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(PATH.with_name('__init__.py')), 'exec'), namespace)
        cls.receive = staticmethod(namespace['_receive_share'])

    def setUp(self):
        self.plugin = SimpleNamespace(_enabled=True, _share_config={**share.DEFAULTS, 'telegram_enabled': True, 'telegram_user_ids': '123'},
                                      _share_services=Mock(), _share_queue=Mock(), _share_notify=Mock())
        self.plugin._share_queue.submit.return_value = {'id': 'job', 'duplicate': False}
        self.data = {'channel': 'Telegram', 'userid': '123', 'chat_id': '123', 'source': 'MyBot', 'text': LINK}

    def test_private_message_retains_notification_source_and_user(self):
        self.receive(self.plugin, self.data)
        self.plugin._share_queue.submit.assert_called_once_with(LINK, self.plugin._share_config, {'userid': '123', 'source': 'MyBot'})

    def test_unauthorized_users_groups_other_channels_and_unrelated_text_are_ignored(self):
        for overrides in ({'userid': '12'}, {'chat_id': '-1001'}, {'channel': 'WeChat'}, {'text': 'hello'}):
            with self.subTest(overrides=overrides):
                self.receive(self.plugin, {**self.data, **overrides})
        self.plugin._share_queue.submit.assert_not_called()
        self.plugin._share_notify.assert_not_called()

    def test_explicit_command_uses_native_arg_str_and_numeric_user(self):
        self.receive(self.plugin, {'channel': SimpleNamespace(value='Telegram'), 'user': '123', 'source': 'MyBot', 'arg_str': LINK}, command=True)
        self.plugin._share_queue.submit.assert_called_once_with(LINK, self.plugin._share_config, {'userid': '123', 'source': 'MyBot'})

    def test_disabled_telegram_does_not_receive_messages(self):
        self.plugin._share_config['telegram_enabled'] = False
        self.receive(self.plugin, self.data)
        self.plugin._share_queue.submit.assert_not_called()


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cloud = Mock()
        self.cloud.share_access.return_value = {'accessToken': 'do-not-expose'}
        self.cloud.share_files.return_value = {'total': 1, 'list': [
            {'fileId': 'resource', 'fileName': 'movie.mkv', 'resType': 1, 'totalSize': 42}]}
        self.cloud.restore_share.return_value = {'taskId': 'receipt'}
        self.api = Mock()
        self.folder = SimpleNamespace(path='/待整理/task/', fileid='folder', type='dir')
        self.organize = Mock(return_value=(True, {'items': [{'state': 'completed'}]}))
        self.notify = Mock()
        self.queue = share.ShareQueue(self.temp.name, lambda: (self.cloud, self.api, self.organize), self.notify)
        self.result = self.queue.submit(LINK, share.DEFAULTS)
        self.job = self.queue._transaction(lambda rows: rows[0])
        self.folder.path = self.job['staging_dir'] + '/'
        self.file = SimpleNamespace(path=self.folder.path + 'movie.mkv', fileid='new', type='file', size=42)
        self.api.list_strict.side_effect = [[], [self.file]]
        self.ensure = patch.object(share, 'ensure_folder', return_value=self.folder)
        self.ensure.start()
        self.addCleanup(self.ensure.stop)

    def test_end_to_end_save_verify_then_organize_only_current_job(self):
        self.queue.process(self.job)
        self.assertEqual(self.queue.list()[0]['state'], 'completed')
        self.cloud.restore_share.assert_called_once_with('do-not-expose', ['resource'], 'folder')
        self.assertEqual(self.organize.call_args.args[0]['staging_dir'], self.job['staging_dir'])
        self.assertEqual(self.queue.list()[0]['files'], 1)
        self.assertEqual(self.queue.path.stat().st_mode & 0o777, 0o600)

    def test_dedup_ignores_code_and_freezes_destination(self):
        other = self.queue.submit(LINK.replace('1234', 'abcd'), {**share.DEFAULTS, 'share_target_dir': '/Elsewhere'})
        self.assertTrue(other['duplicate'])
        self.assertEqual(other['id'], self.result['id'])
        self.assertEqual(self.job['settings']['share_target_dir'], '/Media')

    def test_corrected_code_can_retry_only_before_save(self):
        self.queue.update(self.job, 'failed')
        result = self.queue.submit(LINK.replace('1234', 'fixed'), share.DEFAULTS)
        self.assertFalse(result['duplicate'])
        self.assertEqual(self.queue._transaction(lambda rows: rows[0])['code'], 'fixed')
        self.queue.update(self.job, 'needs_review')
        self.assertTrue(self.queue.submit(LINK, share.DEFAULTS)['duplicate'])

    def test_redacted_api_has_no_codes_tokens_or_telegram_identity(self):
        self.queue.process(self.job)
        public = json.dumps(self.queue.list())
        for secret in ('1234', 'test_share_123', 'do-not-expose', 'telegram_user_ids', 'share_id', 'recipient'):
            self.assertNotIn(secret, public)

    def test_save_timeout_never_repeats_write_or_starts_organizer(self):
        self.cloud.restore_share.side_effect = TimeoutError('private-token')
        self.queue.process(self.job)
        self.assertEqual(self.queue.list()[0]['state'], 'needs_review')
        self.cloud.restore_share.assert_called_once()
        self.organize.assert_not_called()
        self.assertNotIn('private-token', self.queue.list()[0]['message'])

    def test_wrong_saved_size_prevents_organize(self):
        self.file.size = 41
        with patch.object(share.time, 'monotonic', side_effect=[0, 181]):
            self.queue.process(self.job)
        self.assertEqual(self.queue.list()[0]['state'], 'needs_review')
        self.organize.assert_not_called()

    def test_pre_save_failure_never_writes(self):
        self.cloud.share_access.return_value = {}
        self.queue.process(self.job)
        self.assertEqual(self.queue.list()[0]['state'], 'failed')
        self.cloud.restore_share.assert_not_called()
        self.organize.assert_not_called()

    def test_native_accepted_retry_skipped_and_failure_are_not_completed(self):
        for state in ('accepted', 'retry_wait', 'skipped', 'failed', 'manual_review'):
            with self.subTest(state=state):
                self.job['state'] = 'saved'
                self.organize.return_value = (True, {'items': [{'state': state}]})
                self.queue.process(self.job)
                self.assertEqual(self.queue.list()[0]['state'], 'partial')
        self.cloud.restore_share.assert_not_called()

    def test_restart_never_replays_ambiguous_save(self):
        self.queue.update(self.job, 'saving')
        done = threading.Event()
        replacement = share.ShareQueue(self.temp.name, lambda: (self.cloud, self.api, self.organize), lambda _: done.set())
        replacement.start()
        try:
            self.assertTrue(done.wait(2))
            self.assertEqual(replacement.list()[0]['state'], 'needs_review')
            self.cloud.restore_share.assert_not_called()
        finally:
            replacement.stop()
            replacement.thread.join(2)

    def test_notification_failure_does_not_fail_successful_transfer(self):
        self.notify.side_effect = RuntimeError('telegram offline')
        self.queue.process(self.job)
        self.assertEqual(self.queue.list()[0]['state'], 'completed')

    def test_stop_before_write_leaves_no_cloud_mutation(self):
        self.queue.stop()
        self.queue.process(self.job)
        self.cloud.restore_share.assert_not_called()
        self.organize.assert_not_called()
        self.assertEqual(self.queue.list()[0]['state'], 'queued')


if __name__ == '__main__':
    unittest.main()

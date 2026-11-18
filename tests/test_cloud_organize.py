"""离线契约/云盘状态测试：python3 -m unittest discover -s tests -v。

只替代 MoviePilot/OSS 的宿主依赖；被测整理入口与存储适配器使用真实代码。
不调用真实网盘，也不模拟 MoviePilot 的媒体识别算法。
"""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

PLUGIN = Path(__file__).resolve().parents[1] / "plugins.v3" / "guangyasync"


class FileItem(SimpleNamespace):
    def __init__(self, **kwargs):
        fields = dict(storage="guangyasync", path="/", type="file", fileid=None,
                      parent_fileid=None, name=None, basename=None, extension=None,
                      size=None, modify_time=None, pickcode=None, drive_id=None)
        super().__init__(**{**fields, **kwargs})

    def model_dump(self, **_):
        return vars(self).copy()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_plugin_modules():
    stubs = {name: types.ModuleType(name) for name in (
        "app", "app.schemas", "app.sdk", "app.sdk.config", "app.sdk.logging",
        "app.sdk.network", "app.modules", "app.modules.filemanager",
        "app.modules.filemanager.storages", "oss2", "cloud_test_plugin",
    )}
    stubs["app"].schemas = stubs["app.schemas"]
    stubs["app.schemas"].FileItem = FileItem
    stubs["app.sdk.config"].global_vars = SimpleNamespace()
    stubs["app.sdk.config"].settings = SimpleNamespace()
    stubs["app.sdk.logging"].logger = Mock()
    stubs["app.sdk.network"].RequestUtils = Mock()
    stubs["app.modules.filemanager.storages"].transfer_process = Mock()
    stubs["cloud_test_plugin"].__path__ = [str(PLUGIN)]
    with patch.dict(sys.modules, stubs):
        load_module("cloud_test_plugin.guangya_client", PLUGIN / "guangya_client.py")
        api = load_module("cloud_test_plugin.guangya_api", PLUGIN / "guangya_api.py")
        organizer = load_module("cloud_test_plugin.cloud_organizer", PLUGIN / "cloud_organizer.py")
    return api, organizer


api_module, organizer = load_plugin_modules()


class OrganizeTests(unittest.TestCase):
    def setUp(self):
        self.native = Mock()
        self.native.manual_transfer.return_value = (True, {"items": [{"source": "/待整理/a.mkv", "target": "/媒体库/电影/a.mkv"}]})
        native_module = types.ModuleType("app.chain.transfer")
        native_module.TransferChain = Mock(return_value=self.native)
        types_module = types.ModuleType("app.schemas.types")
        types_module.MediaType = SimpleNamespace(MOVIE="电影", TV="电视剧")
        self.host = patch.dict(sys.modules, {"app.chain.transfer": native_module, "app.schemas.types": types_module})
        self.host.start()
        self.addCleanup(self.host.stop)
        self.api = Mock()
        self.folder = FileItem(path="/待整理/", type="dir", fileid="inbox")
        self.api.get_item_strict.side_effect = [self.folder, None]

    def payload(self, **overrides):
        return SimpleNamespace(**{**dict(source_dir="/待整理", target_dir="/媒体库", transfer_type="move",
                                        media_type="auto", preview=True, library_type_folder=True,
                                        library_category_folder=False, scrape=False), **overrides})

    def test_preview_delegates_read_only_to_native_planner(self):
        state, result = organizer.organize_cloud_directory(self.api, self.payload(), "guangyasync")
        self.assertTrue(state)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(self.api.method_calls, [unittest.mock.call.get_item_strict(Path("/待整理")),
                                                unittest.mock.call.get_item_strict(Path("/媒体库"))])
        options = self.native.manual_transfer.call_args.kwargs
        self.assertTrue(options["preview"])
        self.assertFalse(options["background"])
        self.assertEqual(options["target_storage"], "guangyasync")
        self.assertEqual(options["target_path"], Path("/媒体库"))
        self.assertIs(options["fileitem"], self.folder)
        self.assertTrue(options["sync_extra_files"])

    def test_execution_uses_native_background_queue_and_requested_mode(self):
        organizer.organize_cloud_directory(self.api, self.payload(preview=False, transfer_type="copy", media_type="tv"), "guangyasync")
        options = self.native.manual_transfer.call_args.kwargs
        self.assertFalse(options["preview"])
        self.assertTrue(options["background"])
        self.assertEqual(options["transfer_type"], "copy")
        self.assertEqual(options["mtype"], "电视剧")

    def test_rejects_overlapping_or_invalid_paths_before_queries(self):
        for source, target in (("/", "/媒体库"), ("/a", "/a"), ("/a", "/a/library"),
                               ("/a/inbox", "/a"), ("a", "/b"), ("/a", "b"),
                               ("/a/../x", "/b"), ("//a", "/b"), ("/a\\x", "/b")):
            with self.subTest(source=source, target=target), self.assertRaises(ValueError):
                organizer.organize_cloud_directory(self.api, self.payload(source_dir=source, target_dir=target), "guangyasync")
        self.api.get_item_strict.assert_not_called()
        self.native.manual_transfer.assert_not_called()

    def test_sibling_names_are_not_mistaken_for_nested_paths(self):
        self.assertEqual(organizer.organize_paths(" /待整理/ ", "/待整理完成/"), (Path("/待整理"), Path("/待整理完成")))

    def test_missing_source_does_not_enqueue(self):
        self.api.get_item_strict.side_effect = [None]
        with self.assertRaisesRegex(ValueError, "不存在"):
            organizer.organize_cloud_directory(self.api, self.payload(), "guangyasync")
        self.native.manual_transfer.assert_not_called()

    def test_file_target_does_not_enqueue(self):
        self.api.get_item_strict.side_effect = [self.folder, FileItem(type="file")]
        with self.assertRaisesRegex(ValueError, "不是目录"):
            organizer.organize_cloud_directory(self.api, self.payload(), "guangyasync")
        self.native.manual_transfer.assert_not_called()

    def test_query_failure_does_not_enqueue_or_create_directories(self):
        self.api.get_item_strict.side_effect = api_module.StorageQueryError("offline")
        with self.assertRaises(api_module.StorageQueryError):
            organizer.organize_cloud_directory(self.api, self.payload(), "guangyasync")
        self.native.manual_transfer.assert_not_called()
        self.api.get_folder.assert_not_called()

    def test_native_failure_is_preserved(self):
        self.native.manual_transfer.return_value = (False, "未识别到媒体")
        self.assertEqual(organizer.organize_cloud_directory(self.api, self.payload(), "guangyasync"), (False, "未识别到媒体"))


class CloudClient:
    """有文件 ID 的内存云盘，真实适配器负责查询、移动/复制及改名编排。"""
    def __init__(self):
        self.items = {"/inbox": ("inbox", 2), "/library": ("library", 2), "/inbox/raw.mkv": ("media", 1)}
        self.status = 2
        self.moves = self.copies = self.renames = 0

    def get_file_list(self, parent_id, **_):
        parent = next((path for path, (fid, _) in self.items.items() if fid == parent_id), "/")
        values = [{"fileId": fid, "fileName": Path(path).name, "type": kind, "fileSize": 100}
                  for path, (fid, kind) in self.items.items() if str(Path(path).parent) == parent]
        return {"list": values, "total": len(values)}

    def get_task_status(self, _):
        return {"status": self.status}

    def _transfer(self, ids, target_parent_id, copy):
        source = next(path for path, (fid, _) in self.items.items() if fid == ids[0])
        target = next(path for path, (fid, _) in self.items.items() if fid == target_parent_id)
        if self.status == 2:
            value = self.items[source]
            self.items[str(Path(target) / Path(source).name)] = ("copied" if copy else value[0], value[1])
            if not copy:
                del self.items[source]
        return {"taskId": "task"}

    def move_file(self, ids, target_parent_id):
        self.moves += 1
        return self._transfer(ids, target_parent_id, False)

    def copy_file(self, ids, target_parent_id):
        self.copies += 1
        return self._transfer(ids, target_parent_id, True)

    def rename(self, file_id, new_name):
        self.renames += 1
        source = next(path for path, (fid, _) in self.items.items() if fid == file_id)
        self.items[str(Path(source).parent / new_name)] = self.items.pop(source)
        return {}

    def delete_file(self, ids):
        if self.status == 2:
            self.items = {path: item for path, item in self.items.items() if item[0] not in ids}
        return {"taskId": "task"}


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.client = CloudClient()
        self.api = api_module.GuangYaApi(self.client, "guangyasync")
        self.source = self.api.get_item_strict(Path("/inbox/raw.mkv"))
        self.sleep = patch.object(api_module.time, "sleep")
        self.sleep.start()
        self.addCleanup(self.sleep.stop)

    def test_cloud_move_and_rename_preserves_file_id_without_upload(self):
        self.assertTrue(self.api.move(self.source, Path("/library"), "Movie (2026).mkv"))
        self.assertNotIn("/inbox/raw.mkv", self.client.items)
        self.assertEqual(self.client.items["/library/Movie (2026).mkv"][0], "media")
        self.assertEqual((self.client.moves, self.client.copies, self.client.renames), (1, 0, 1))

    def test_cloud_copy_and_rename_preserves_source(self):
        self.assertTrue(self.api.copy(self.source, Path("/library"), "Movie (2026).mkv"))
        self.assertEqual(self.client.items["/inbox/raw.mkv"][0], "media")
        self.assertEqual(self.client.items["/library/Movie (2026).mkv"][0], "copied")

    def test_unconfirmed_or_failed_tasks_are_not_successful(self):
        for state in (1, 3):
            for action in (self.api.move, self.api.copy):
                with self.subTest(state=state, action=action.__name__):
                    self.client.status = state
                    self.assertFalse(action(self.source, Path("/library"), "Movie.mkv"))
        self.assertIn("/inbox/raw.mkv", self.client.items)
        self.assertEqual(self.client.renames, 0)

    def test_original_name_collision_never_renames_other_file(self):
        self.client.items["/library/raw.mkv"] = ("unrelated", 1)
        self.assertFalse(self.api.move(self.source, Path("/library"), "Movie.mkv"))
        self.assertFalse(self.api.copy(self.source, Path("/library"), "Movie.mkv"))
        self.assertEqual((self.client.moves, self.client.copies, self.client.renames), (0, 0, 0))

    def test_delete_requires_confirmed_completion_and_absence(self):
        for state in (1, 3):
            self.client.status = state
            self.assertFalse(self.api.delete(self.source))
            self.assertIn("/inbox/raw.mkv", self.client.items)
        self.client.status = 2
        self.assertTrue(self.api.delete(self.source))
        self.assertIsNone(self.api.get_item_strict(Path("/inbox/raw.mkv")))

    def test_same_directory_rename_and_noop(self):
        self.assertTrue(self.api.move(self.source, Path("/inbox"), "raw.mkv"))
        self.assertTrue(self.api.move(self.source, Path("/inbox"), "renamed.mkv"))
        self.assertEqual(self.client.moves, 0)
        self.assertEqual(self.client.renames, 1)

    def test_strict_query_bypasses_cached_file_and_parent_ids(self):
        self.assertIsNotNone(self.api.get_item(Path("/inbox/raw.mkv")))
        del self.client.items["/inbox/raw.mkv"]
        self.assertIsNone(self.api.get_item_strict(Path("/inbox/raw.mkv")))
        del self.client.items["/inbox"]
        self.assertIsNone(self.api.get_item_strict(Path("/inbox/raw.mkv")))

    def test_strict_list_refuses_partial_pages(self):
        first_page = {"list": [{"fileId": str(i), "fileName": f"{i}.mkv", "type": 1} for i in range(10)], "total": 20}
        self.api._page_size = 10
        self.client.get_file_list = Mock(side_effect=[first_page, api_module.GuangYaApiError("offline")])
        with self.assertRaises(api_module.StorageQueryError):
            self.api.list_strict(FileItem(type="dir", path="/library", fileid="library"))
        self.assertNotIn("/library", self.api._dir_cache)

    def test_strict_list_refuses_empty_page_before_reported_total(self):
        self.api._page_size = 10
        self.client.get_file_list = Mock(side_effect=[
            {"list": [{"fileId": str(i), "fileName": f"{i}.mkv", "type": 1} for i in range(10)], "total": 20},
            {"list": [], "total": 20},
        ])
        with self.assertRaises(api_module.StorageQueryError):
            self.api.list_strict(FileItem(type="dir", path="/library", fileid="library"))

    def test_strict_list_refuses_page_limit_truncation(self):
        self.api._MAX_PAGES = 1
        self.api._page_size = 10
        self.client.get_file_list = Mock(return_value={"list": [{"fileId": str(i), "fileName": f"{i}.mkv", "type": 1} for i in range(10)]})
        with self.assertRaises(api_module.StorageQueryError):
            self.api.list_strict(FileItem(type="dir", path="/library", fileid="library"))

    def test_strict_query_failure_is_not_absence(self):
        self.client.get_file_list = Mock(side_effect=api_module.GuangYaApiError("offline"))
        with self.assertRaises(api_module.StorageQueryError):
            self.api.get_item_strict(Path("/inbox/raw.mkv"))

    def test_mismatched_move_receipt_does_not_rename_unrelated_item(self):
        self.api._wait_item_visible = Mock(return_value=FileItem(fileid="other", name="raw.mkv", path="/library/raw.mkv"))
        self.assertFalse(self.api.move(self.source, Path("/library"), "Movie.mkv"))
        self.assertEqual(self.client.renames, 0)


if __name__ == "__main__":
    unittest.main()

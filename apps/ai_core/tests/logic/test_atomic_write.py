# apps/ai_core/tests/logic/test_atomic_write.py
"""
Unit tests for atomic_write module.

Tests crash-safe JSON file operations including atomic writes and reads.
"""

import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path

try:
    from apps.ai_core.ai_core.logic.atomic_write import atomic_write_json, read_json_file
except ModuleNotFoundError:
    from ai_core.logic.atomic_write import atomic_write_json, read_json_file


class TestAtomicWriteJson:
    """Test suite for atomic_write_json function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        dir_path = tempfile.mkdtemp()
        yield dir_path
        shutil.rmtree(dir_path, ignore_errors=True)

    def test_write_simple_json(self, temp_dir):
        """Test writing simple JSON data."""
        file_path = os.path.join(temp_dir, "test.json")
        data = {"key": "value", "number": 42}

        atomic_write_json(file_path, data)

        assert os.path.exists(file_path)
        with open(file_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded == data

    def test_write_nested_json(self, temp_dir):
        """Test writing nested JSON structures."""
        file_path = os.path.join(temp_dir, "nested.json")
        data = {
            "nodes": [
                {"id": "start", "type": "start", "data": {}},
                {"id": "end", "type": "end", "data": {"nested": {"deep": True}}}
            ],
            "edges": [{"source": "start", "target": "end"}],
            "triggers": [],
            "permissions": {}
        }

        atomic_write_json(file_path, data)

        with open(file_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded == data

    def test_write_unicode_content(self, temp_dir):
        """Test writing JSON with unicode characters."""
        file_path = os.path.join(temp_dir, "unicode.json")
        data = {
            "name": "Тестовый агент",
            "emoji": "🚀",
            "chinese": "测试"
        }

        atomic_write_json(file_path, data)

        with open(file_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded == data

    def test_creates_parent_directory(self, temp_dir):
        """Test that parent directories are created if they don't exist."""
        file_path = os.path.join(temp_dir, "subdir", "nested", "test.json")
        data = {"created": True}

        atomic_write_json(file_path, data)

        assert os.path.exists(file_path)
        with open(file_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded == data

    def test_overwrites_existing_file(self, temp_dir):
        """Test that existing file is overwritten."""
        file_path = os.path.join(temp_dir, "overwrite.json")

        # Write initial content
        atomic_write_json(file_path, {"version": 1})

        # Overwrite with new content
        atomic_write_json(file_path, {"version": 2})

        with open(file_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded == {"version": 2}

    def test_no_temp_files_left_on_success(self, temp_dir):
        """Test that no temp files are left after successful write."""
        file_path = os.path.join(temp_dir, "clean.json")

        atomic_write_json(file_path, {"clean": True})

        # Check directory contents
        files = os.listdir(temp_dir)
        assert len(files) == 1
        assert files[0] == "clean.json"
        assert not any(".tmp." in f for f in files)

    def test_write_empty_dict(self, temp_dir):
        """Test writing an empty dictionary."""
        file_path = os.path.join(temp_dir, "empty.json")

        atomic_write_json(file_path, {})

        with open(file_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded == {}

    def test_write_with_special_characters_in_path(self, temp_dir):
        """Test writing to path with spaces."""
        subdir = os.path.join(temp_dir, "path with spaces")
        os.makedirs(subdir, exist_ok=True)
        file_path = os.path.join(subdir, "file name.json")

        atomic_write_json(file_path, {"spaces": True})

        assert os.path.exists(file_path)

    def test_raises_type_error_for_non_serializable(self, temp_dir):
        """Test that TypeError is raised for non-serializable data."""
        file_path = os.path.join(temp_dir, "bad.json")

        with pytest.raises(TypeError):
            atomic_write_json(file_path, {"func": lambda x: x})


class TestReadJsonFile:
    """Test suite for read_json_file function."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        dir_path = tempfile.mkdtemp()
        yield dir_path
        shutil.rmtree(dir_path, ignore_errors=True)

    def test_read_simple_json(self, temp_dir):
        """Test reading simple JSON file."""
        file_path = os.path.join(temp_dir, "read.json")
        expected = {"key": "value", "number": 123}

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(expected, f)

        result = read_json_file(file_path)

        assert result == expected

    def test_read_unicode_json(self, temp_dir):
        """Test reading JSON with unicode content."""
        file_path = os.path.join(temp_dir, "unicode.json")
        expected = {"name": "Агент", "emoji": "✨"}

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(expected, f, ensure_ascii=False)

        result = read_json_file(file_path)

        assert result == expected

    def test_read_file_not_found(self, temp_dir):
        """Test that FileNotFoundError is raised for missing file."""
        file_path = os.path.join(temp_dir, "nonexistent.json")

        with pytest.raises(FileNotFoundError):
            read_json_file(file_path)

    def test_read_invalid_json(self, temp_dir):
        """Test that JSONDecodeError is raised for invalid JSON."""
        file_path = os.path.join(temp_dir, "invalid.json")

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            read_json_file(file_path)

    def test_roundtrip_write_read(self, temp_dir):
        """Test writing and reading back produces identical data."""
        file_path = os.path.join(temp_dir, "roundtrip.json")
        original = {
            "nodes": [
                {"id": "start", "type": "start"},
                {"id": "end", "type": "end"}
            ],
            "edges": [{"source": "start", "target": "end"}],
            "metadata": {
                "created": "2024-01-01T00:00:00Z",
                "version": 1
            }
        }

        atomic_write_json(file_path, original)
        result = read_json_file(file_path)

        assert result == original


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

import os
import pathlib
import unittest
from unittest.mock import patch

from parameterized import parameterized

from common.filemanager import FileManager, FileNotExist, listdir


class FileManagerTests(unittest.TestCase):

    @parameterized.expand([
        ['file_path', None, 'filename', 'filename'],
        ['dir_path_and_file', 'dirname', 'filename', 'dirname/filename']
    ])
    def test_init(self, name, dirname, filename, expected):
        filemanager = FileManager(file=filename, dirname=dirname, check=False)
        self.assertEqual(expected, filemanager.filename)

    @patch.object(pathlib.Path, 'exists')
    def test_init_with_check(self, mock_exists):
        mock_exists.return_value = True
        filename = 'filename'
        filemanager = FileManager(file=filename, check=True)
        self.assertEqual(filename, filemanager.filename)
        mock_exists.assert_called()

    @patch.object(pathlib.Path, 'exists')
    def test_init_with_check_exc(self, mock_exists):
        mock_exists.return_value = False
        with self.assertRaises(FileNotExist):
            _ = FileManager(file='filename', check=True)
        mock_exists.assert_called()

    @patch.object(os, 'listdir')
    def test_listdir(self, mock_exists):
        mock_exists.return_value = ['file1', 'file2', 'file3']
        self.assertListEqual(['dir/path/file1',
                              'dir/path/file2',
                              'dir/path/file3'],
                             listdir('dir/path'))

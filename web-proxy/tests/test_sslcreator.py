import os
import pathlib
import ssl
import unittest
from unittest.mock import patch, MagicMock

from cryptography import x509

import sslcert
from common.filemanager import FileManager, save_file_at_dir
from sslcert import CertificateCreator


class SSLCreatorTests(unittest.TestCase):

    @patch.object(sslcert.CertificateCreator, '_load_certs')
    def test_get_alt_names(self, mock_load):
        mock_load.return_value = None
        sslcreator = CertificateCreator(work_dir='',
                                        ca_cert_file='', ca_key_file='')
        cert_info = {'subjectAltName': [('DNS', 'name1'), ('DNS', 'name2')]}
        actual = sslcreator._get_alt_names(
            hostname='hostname', cert_info=cert_info)
        self.assertEqual(
            x509.SubjectAlternativeName(
                [x509.DNSName('name1'), x509.DNSName('name2'),
                 x509.DNSName('hostname')]),
            actual)
        mock_load.assert_called()

    @patch.object(pathlib.Path, 'exists')
    @patch.object(sslcert.CertificateCreator, '_load_certs')
    def test_create_exist_ssl(self, mock_load, mock_exists):
        mock_load.return_value = None
        mock_exists.return_value = True
        sslcreator = CertificateCreator(work_dir='testdir',
                                        ca_cert_file='',
                                        ca_key_file='')
        sslcreator._cert = {'dns_name': 'files', 'dns_name1': 'files1'}
        self.assertEqual(
            ('testdir/ssl/files.crt', 'testdir/ssl/files.key'),
            sslcreator._create_ssl(host='dns_name', cert_info={}))
        mock_load.assert_called()
        mock_exists.assert_called()

    @patch('sslcert.sslcreator.save_file_at_dir')
    @patch.object(pathlib.Path, 'exists')
    @patch.object(sslcert.CertificateCreator, '_generate_selfsigned_cert')
    @patch.object(sslcert.CertificateCreator, '_load_certs')
    def test_create_ssl(self, mock_load, mock_gen, mock_exists, mock_save):
        mock_load.return_value = None
        mock_gen.return_value = ('filenames', b'certbytes', b'keybytes')
        sslcert.save_file_at_dir = MagicMock(side_effect=None)
        mock_exists.return_value = False
        sslcreator = CertificateCreator(work_dir='testdir',
                                        ca_cert_file='',
                                        ca_key_file='')
        sslcreator._cert = {'dns_name1': 'files1'}
        self.assertEqual(
            ('testdir/ssl/filenames.crt', 'testdir/ssl/filenames.key'),
            sslcreator._create_ssl(
                host='dns_name',
                cert_info={'subjectAltName': [('DNS', 'name1')]}
            )
        )
        self.assertDictEqual({'dns_name': 'filenames', 'dns_name1': 'files1'},
                             sslcreator._cert)
        mock_load.assert_called()
        mock_gen.assert_called()
        mock_save.assert_called()

    @patch.object(FileManager, 'check_exist')
    @patch.object(ssl.SSLContext, 'load_verify_locations')
    @patch.object(ssl.SSLContext, 'load_cert_chain')
    @patch.object(sslcert.CertificateCreator, '_load_certs')
    def test_create_sslcontext(self, mock_load, mock_chain, mock_loc,
                               mock_exist):
        mock_load.return_value = None
        mock_chain.return_value = None
        mock_loc.return_value = None
        mock_exist.return_value = True
        sslcreator = CertificateCreator(work_dir='testdir',
                                        ca_cert_file='',
                                        ca_key_file='')
        sslcreator._ca_cert_file = FileManager(file='file')
        sslcreator._create_ssl = MagicMock(return_value=('cert', 'key'))
        self.assertTrue(
            isinstance(
                sslcreator.create_sslcontext(target_host='target_host',
                                             cert_dict={}),
                ssl.SSLContext
            ))
        mock_loc.assert_called()
        mock_chain.assert_called()
        mock_exist.assert_called()

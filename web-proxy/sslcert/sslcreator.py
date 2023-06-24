import os
import random
import ssl

from datetime import datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from common.filemanager import FileManager, save_file_at_dir


class CertificateCreator:
    def __init__(self, work_dir='./openssl/',
                 ca_cert_file='RootCA.crt', ca_key_file='RootCA.key'):
        """
        :param work_dir:
        :param ca_cert_file:
        :param ca_key_file:
        :raise FileNotExist
        """
        self._cert: dict = dict()
        self._cert_dir = os.path.join(work_dir, 'ssl/')
        self._load_certs(work_dir, ca_cert_file, ca_key_file)

    def _load_certs(self, work_dir: str, ca_cert_file: str, ca_key_file: str):
        self._ca_cert_file = FileManager(dirname=work_dir, file=ca_cert_file)
        ca_cert_bytes = self._ca_cert_file.read_file()

        ca_key_file = FileManager(dirname=work_dir, file=ca_key_file)
        ca_key_bytes = ca_key_file.read_file()

        self._ca_cert = x509.load_pem_x509_certificates(ca_cert_bytes)[0]
        self._ca_key = serialization.load_pem_private_key(
            data=ca_key_bytes,
            password=None,
            backend=default_backend()
        )

    def create_sslcontext(self, target_host, cert_dict) -> ssl.SSLContext:
        certfile, keyfile = self._create_ssl(target_host, cert_dict)
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self._ca_cert_file.check_exist()
        context.load_verify_locations(cafile=self._ca_cert_file.filename)
        context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        return context

    def _create_ssl(self, host, cert_info) -> (str, str):
        is_exist = host in self._cert
        if is_exist:
            filename = self._cert[host]
            is_exist = all((
                Path(self._get_crt_path(filename)).exists(),
                Path(self._get_key_path(filename)).exists()
            ))
        if not is_exist:
            serialnumber, cert, key = self._generate_selfsigned_cert(
                hostname=host,
                san=self._get_alt_names(host, cert_info),
                key=None
            )
            filename = str(serialnumber)
            save_file_at_dir(self._cert_dir, f'{filename}.crt', cert)
            save_file_at_dir(self._cert_dir, f'{filename}.key', key)
            self._cert[host] = filename
        filename = self._cert[host]
        return self._get_crt_path(filename), self._get_key_path(filename)

    def _get_crt_path(self, filename):
        return os.path.join(self._cert_dir, f'{filename}.crt')

    def _get_key_path(self, filename):
        return os.path.join(self._cert_dir, f'{filename}.key')

    @staticmethod
    def _get_alt_names(hostname: str, cert_info: dict):
        ip_addresses = [addr for _, addr in cert_info['subjectAltName']]
        ip_addresses.append(hostname)
        alt_names = []
        for addr in ip_addresses:
            alt_names.append(x509.DNSName(addr))
        return x509.SubjectAlternativeName(alt_names)

    def _generate_selfsigned_cert(self, hostname, san, key=None):
        if key is None:
            key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend(),
            )
        name = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, hostname)
        ])

        basic_contraints = x509.BasicConstraints(ca=False, path_length=None)
        now = datetime.utcnow()
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(self._ca_cert.subject)
            .public_key(key.public_key())
            .serial_number(random.getrandbits(64))
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=10 * 365))
            .add_extension(basic_contraints, False)
            .add_extension(san, False)
            .sign(self._ca_key, hashes.SHA256(), default_backend())
        )
        cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)
        key_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return cert.serial_number, cert_pem, key_pem

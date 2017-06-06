import hashlib
import os
import tempfile

from mira.util.subprocess import run_subprocess
from mira.util.log import get_logger

log = get_logger(__name__)


def get_hex_digest(data, algorithm='md5'):
	algo_hash = hashlib.new(algorithm)
	algo_hash.update(data)
	return algo_hash.hexdigest()


def get_digest(data, algorithm='md5'):
	algo_hash = hashlib.new(algorithm)
	algo_hash.update(data)
	return algo_hash.digest()


def get_public_key(certificate):
	pub_filename = None

	with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as temp_file:
		temp_file.write(certificate.encode('utf-8'))
		pub_filename = temp_file.name

	public_key = run_subprocess([
		"openssl", "x509", "-inform", "pem",
		"-in", pub_filename, "-pubkey", "-noout"
	])

	os.remove(pub_filename)

	return public_key


def signature_is_verified(signature, public_key, text, algorithm="sha1"):
	pub_filename = None
	ssl_filename = None
	txt_filename = None

	with tempfile.NamedTemporaryFile(
		suffix=".pub", delete=False
	) as public_key_file:
		public_key_file.write(public_key)
		pub_filename = public_key_file.name

	with tempfile.NamedTemporaryFile(
		suffix=".ssl", delete=False
	) as signature_file:
		signature_file.write(signature)
		ssl_filename = signature_file.name

	with tempfile.NamedTemporaryFile(
		suffix=".txt", delete=False
	) as text_file:
		text_file.write(text)
		txt_filename = text_file.name

	output = run_subprocess(
		[
			"openssl", "dgst", "-" + algorithm, "-verify", pub_filename,
			"-signature", ssl_filename, txt_filename
		]
	)

	os.remove(pub_filename)
	os.remove(ssl_filename)
	os.remove(txt_filename)

	return output.strip() == "Verified OK"

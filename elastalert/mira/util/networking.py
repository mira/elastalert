import re

from mira.util.subprocess import run_subprocess


def resolve_dns(host):
	return re.split(r'\s+', run_subprocess(["getent", "hosts", host]))[0]

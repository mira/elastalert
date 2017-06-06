import subprocess
from mira.util.log import get_logger

log = get_logger(__name__)


class SubprocessException(Exception):
	def __init__(self, msg, cmd=None):
		super(SubprocessException, self).__init__(msg)
		self.msg = msg
		self.cmd = " ".join(cmd)


def run_subprocess(command, encoding="utf-8"):
	log.info("Running Subprocess: " + " ".join(command))

	proc = subprocess.Popen(
		command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
	)

	err = proc.stderr.read()

	if err:
		if encoding:
			err = err.decode('utf-8')
		raise SubprocessException(err, cmd=command)

	output = proc.stdout.read()

	if encoding:
		output = output.decode('utf-8')

	return output

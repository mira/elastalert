import os

base_path = os.path.dirname(
	os.path.dirname(
		os.path.dirname(
			os.path.abspath(__file__)
		)
	)
)
version_path = os.path.join(base_path, '.docker-repo-version')


def get_version():
	version = None

	with open(version_path) as f:
		version = f.read().strip()

	if not version:
		raise Exception("No version @ {}".format(version_path))

	return version

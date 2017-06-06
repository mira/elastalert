import functools
import logging
import time


def get_logger(name, level=logging.INFO):
	logging.basicConfig()
	log = logging.getLogger(name)
	log.setLevel(level)

	return log


def timed(log=None):
	log = log or get_logger("timed")

	def decorator(f):
		@functools.wraps(f)
		def wrapper(*args, **kwargs):
			start = time.time()
			result = f(*args, **kwargs)
			elapsed = time.time() - start
			log.info("%s execution time: %.02f ms", f.__name__, elapsed * 1000)
			return result
		return wrapper
	return decorator

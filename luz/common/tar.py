# module imports
from os import makedirs
from subprocess import getoutput

# local imports
from .utils import cmd_in_path, resolve_path


class TAR():
	def __init__(self, algorithm: str = 'xz', compress_level: str = 9):
		# algo
		self.algorithm = algorithm
		# fix algorithms
		if self.algorithm == 'gz':
			self.algorithm = 'gzip'
		elif self.algorithm == 'bz2':
			self.algorithm = 'bzip2'
		elif self.algorithm == 'zst':
			self.algorithm = 'zstd'
		elif self.algorithm == 'lz':
			self.algorithm = 'lzma'

		# file endings
		# handle algorithm
		if self.algorithm == 'zstd':
			self.ending = 'zst'
		elif self.algorithm == 'gzip':
			self.ending = 'gz'
		elif self.algorithm == 'bzip2':
			self.ending = 'bz2'
		else:
			self.ending = self.algorithm

		# valid algos
		self.valid = ['xz', 'gzip', 'bzip2', 'zstd', 'lzma', 'lz4']
		if self.algorithm not in self.valid:
			raise Exception(
				f'Invalid algorithm type {self.algorithm}. Valid types are: {", ".join(self.valid)}. Default is xz.')

		# get tar command
		self.tar = cmd_in_path('tar')
		# ensure file exists
		if self.tar == None:
			raise Exception(
				'Command "tar" could not be found. Please install it in order to use this library.')

		# get compress command
		self.compress_command = cmd_in_path(self.algorithm)
		# ensure file exists
		if self.compress_command == None:
			raise Exception(
				f'Command "{self.algorithm}" could not be found. Please install it in order to use this library.')

		# compression level
		self.level = compress_level

	def compress_directory(self, dir_name: str, archive_name: str):
		"""Compresses a directory using the specified algorithm.
		
		:param str dir_name: Directory to compress.
		:param str archive_name: Name of the archive. (ex: data.tar)
		"""
		# ensure path exists
		if not resolve_path(dir_name).exists():
			raise Exception(f'Path {dir_name} does not exist.')
		# compress
		getoutput(
			f'cd {dir_name} && {self.tar} -cf - . | {self.compress_command} -{self.level} -c > ../{archive_name}.{self.ending}')

	def decompress_archive(self, archive_name: str, out_dir: str = '.'):
		"""Compresses a directory using the specified algorithm.
		
		:param str dir_name: Directory to decompress to.
		:param str archive_name: Name of the archive. (ex: data.tar)
		"""
		# ensure archive exists
		if not resolve_path(archive_name).exists():
			raise Exception(f'Specified archive {archive_name} does not exist.')
		# create out dir if it doesn't exist
		if not resolve_path(out_dir).exists():
			makedirs(out_dir)
		# decompress
		getoutput(f'{self.tar} -xf {archive_name} -C {out_dir}')

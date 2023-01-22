# module imports
from os import makedirs, mkdir, path
from shutil import copytree
from time import time

# local imports
from ..logger import log
from .module import Module
from ..utils import get_hash, setup_luz_dir


class Tool(Module):
    def __init__(self, **kwargs):
        """Tool module class.
        
        :param dict module: Module dictionary to build
        :param str key: Module key name
        :param CCompiler compiler: Compiler to use to build
        :param LuzBuild luzbuild: Luzbuild class
        """
        # kwargs parsing
        module = kwargs.get('module')
        key = kwargs.get('key')
        compiler = kwargs.get('compiler')
        luzbuild = kwargs.get('luzbuild')
        # get luz dir
        self.dir = setup_luz_dir()
        # files
        files = module.get('files') if type(module.get(
            'files')) is list else [module.get('files')]
        super().__init__(module, key, compiler, luzbuild)
        self.files = self.__hash_files(files)

    def __hash_files(self, files: list) -> list:
        """Hash the files of the module, and compare them to their old hashes.

        :return: The list of changed files.
        """
        # make dirs
        if not path.exists(self.dir + '/bin'):
            mkdir(self.dir + '/bin')

        with open(self.dir + '/hashlist.json', 'w') as f:
            # write new hashes
            f.write(str({file: get_hash(file)
                    for file in files}).replace("'", '"'))

        # return files
        return files

    def __stage(self, rootless: bool = False):
        """Stage a deb to be packaged."""
        # dirs to make
        dirtomake = '/stage/usr/' if not rootless else '/stage/var/jb/usr/'
        dirtocopy = '/stage/usr/bin/' if not rootless else '/stage/var/jb/usr/bin/'
        # make proper dirs
        if not path.exists(self.dir + dirtomake):
            makedirs(self.dir + dirtomake)
        copytree(self.dir + '/bin', self.dir + dirtocopy)
        

    def compile(self, rootless: bool = False):
        """Compile the specified self.

        :param CCompiler compiler: The compiler to use.
        """

        start = time()

        # compile files
        log(f'Compiling to executable...')
        try:
            self.compiler.compile(' '.join(self.files), f'{self.dir}/bin/{self.name}', [
                                f'-isysroot {self.sdk}', self.frameworks, self.include, self.libraries, self.archs])
        except Exception as e:
            print(e)
            exit(1)

        # stage deb
        self.__stage(rootless=rootless)
        log(
            f'Finished compiling module "{self.name}" in {round(time() - start, 2)} seconds.')

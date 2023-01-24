# module imports
from glob import glob
from os import makedirs, mkdir
from shutil import copytree
from time import time

# local imports
from ..logger import log
from .module import Module
from ..utils import exists, get_hash


class Tool(Module):
    def __init__(self, **kwargs):
        """Tool module class.
        
        :param dict module: Module dictionary to build
        :param str key: Module key name
        :param LuzBuild luzbuild: Luzbuild class
        """
        # kwargs parsing
        module = kwargs.get('module')
        # files
        files = module.get('files') if type(module.get(
            'files')) is list else [module.get('files')]
        super().__init__(module, kwargs.get('key'), kwargs.get('luzbuild'))
        self.files = self.__hash_files(files)

    def __hash_files(self, files: list) -> list:
        """Hash the files of the module, and compare them to their old hashes.

        :return: The list of changed files.
        """
        # make dirs
        if not exists(self.dir + '/bin'):
            mkdir(self.dir + '/bin')
        
        # globbing
        for file in files:
            if '*' in file:
                files.remove(file)
                for f in glob(file):
                    files.append(f)

        with open(self.dir + '/hashlist.json', 'w') as f:
            # write new hashes
            f.write(str({file: get_hash(file)
                    for file in files}).replace("'", '"'))

        # return files
        return files

    def __stage(self):
        """Stage a deb to be packaged."""
        # dirs to make
        dirtomake = '/stage/usr/' if not self.luzbuild.rootless else '/stage/var/jb/usr/'
        dirtocopy = '/stage/usr/bin/' if not self.luzbuild.rootless else '/stage/var/jb/usr/bin/'
        # make proper dirs
        if not exists(self.dir + dirtomake):
            makedirs(self.dir + dirtomake)
        copytree(self.dir + '/bin', self.dir + dirtocopy)
        

    def compile(self):
        """Compile the specified self."""
        start = time()

        # compile files
        log(f'Compiling to executable...')
        try:
            build_flags = [self.luzbuild.warnings, f'-O{self.luzbuild.optimization}',
                           f'-isysroot {self.sdk}', f'-F{self.sdk}/System/Library/PrivateFrameworks' if self.private_frameworks != '' else '', self.private_frameworks, self.frameworks, self.include, self.libraries, self.archs]
            self.compiler.compile(' '.join(self.files), f'{self.dir}/bin/{self.name}', build_flags)
        except Exception as e:
            print(e)
            exit(1)

        # stage deb
        self.__stage()
        log(
            f'Finished compiling module "{self.name}" in {round(time() - start, 2)} seconds.')

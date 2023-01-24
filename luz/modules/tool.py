# module imports
from glob import glob
from os import makedirs, mkdir
from shutil import copytree
from subprocess import check_output
from time import time

# local imports
from ..logger import log, error, warn
from .module import Module
from ..utils import cmd_in_path, exists, get_hash


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
        if self.install_dir is None:
            dirtomake = '/stage/usr/' if not self.luzbuild.rootless else '/stage/var/jb/usr/'
            dirtocopy = '/stage/usr/bin/' if not self.luzbuild.rootless else '/stage/var/jb/usr/bin/'
        else:
            if self.luzbuild.rootless: warn('Custom install directory specified, and rootless is enabled. Prefixing path with /var/jb.')
            dir = self.install_dir.split('/')
            dirtomake = f'/stage/${dir[:-1]}' if not self.luzbuild.rootless else f'/stage/var/jb/${dir[:-1]}'
            dirtocopy = f'/stage/{dir}' if not self.luzbuild.rootless else f'/stage/var/jb/{dir}'
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
                           f'-isysroot {self.sdk}', f'-F{self.sdk}/System/Library/PrivateFrameworks' if self.private_frameworks != '' else '', self.private_frameworks, self.frameworks, self.include, self.libraries, self.archs, f'-m{self.platform}-version-min={self.minVers}']
            self.compiler.compile(' '.join(self.files), f'{self.dir}/bin/{self.name}', build_flags)
            # rpath
            install_tool = cmd_in_path(
                f'{(self.prefix + "/") if self.prefix is not None else ""}install_name_tool')
            if install_tool is None:
                # fall back to path
                install_tool = cmd_in_path('install_name_tool')
                if install_tool is None:
                    error('install_name_tool_not found.')
                    exit(1)
            # fix rpath
            rpath = '/var/jb/Library/Frameworks/' if self.luzbuild.rootless else '/Library/Frameworks'
            check_output(
                f'{install_tool} -add_rpath {rpath} {self.dir}/dylib/{self.name}.dylib', shell=True)
            # ldid
            ldid = cmd_in_path(
                f'{(self.prefix + "/") if self.prefix is not None else ""}ldid')
            if ldid is None:
                # fall back to path
                ldid = cmd_in_path('ldid')
                if ldid is None:
                    error('ldid not found.')
                    exit(1)
            # run ldid
            check_output(
                f'{ldid} {self.luzbuild.entflag}{self.luzbuild.entfile} {self.dir}/bin/{self.name}', shell=True)
        except Exception as e:
            print(e)
            exit(1)

        # stage deb
        self.__stage()
        log(
            f'Finished compiling module "{self.name}" in {round(time() - start, 2)} seconds.')

# module imports
from json import loads
from os import makedirs, mkdir
from shutil import copytree
from subprocess import check_output
from time import time

# local imports
from ..logger import log, error, warn
from .module import Module
from ..utils import cmd_in_path, get_hash, resolve_path


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
        # bin directory
        self.bin_dir = resolve_path(f'{self.dir}/bin')
        self.files = self.__hash_files(files)

    def __hash_files(self, files: list) -> list:
        """Hash the files of the module, and compare them to their old hashes.

        :return: The list of changed files.
        """
        # make dirs
        if not self.bin_dir.exists():
            mkdir(self.bin_dir)
            
        files_to_compile = []
        
        # file path formatting
        for file in files:
            file_path = resolve_path(file)
            if type(file_path) is list:
                for f in file_path:
                    files_to_compile.append(f)
            else:
                files_to_compile.append(file_path)

        # old hashes
        old_hashlist = {}
        # check if hashlist exists
        if self.hash_file.exists():
            with open(self.hash_file, 'r') as f:
                old_hashlist = loads(f.read())

        with open(self.hash_file, 'w') as f:
            # new hashes
            new_hashes = {}
            # loop files
            for file in files_to_compile:
                # get file hash
                new_hash = get_hash(file)
                # add to new hashes
                new_hashes[str(file)] = new_hash
            # write new hashes
            new_hashes.update({k: v for k, v in old_hashlist.items() if k in new_hashes})
            f.write(str(new_hashes).replace("'", '"'))

        # return files
        return files_to_compile

    def __stage(self):
        """Stage a deb to be packaged."""
        # dirs to make
        if self.install_dir is None:
            dirtomake = resolve_path(f'{self.dir}/stage/usr') if not self.luzbuild.rootless else resolve_path(f'{self.dir}/stage/var/jb/usr')
            dirtocopy = resolve_path(f'{self.dir}/stage/usr/bin') if not self.luzbuild.rootless else resolve_path(f'{self.dir}/stage/var/jb/usr/bin')
        else:
            if self.luzbuild.rootless: warn('Custom install directory specified, and rootless is enabled. Prefixing path with /var/jb.')
            self.install_dir = resolve_path(self.install_dir)
            dirtomake = resolve_path(f'{self.dir}/stage/{self.install_dir.parent}') if not self.luzbuild.rootless else resolve_path(f'{self.dir}/stage/var/jb/{self.install_dir.parent}')
            dirtocopy = resolve_path(f'{self.dir}/stage/{self.install_dir}') if not self.luzbuild.rootless else resolve_path(f'{self.dir}/stage/var/jb/{self.install_dir}')
        # make proper dirs
        if not dirtomake.exists():
            makedirs(dirtomake)
        copytree(self.bin_dir, dirtocopy, dirs_exist_ok=True)
        

    def compile(self):
        """Compile the specified self."""
        start = time()

        # compile files
        log(f'Compiling to executable...')
        try:
            # get files by extension
            files = ''
            for file in self.files:
                if files != '':
                    files += ' '
                files += f'{str(file)}'
            # build flags
            build_flags = [self.luzbuild.warnings, f'-O{self.luzbuild.optimization}',
                           f'-isysroot {self.sdk}', f'-F{self.sdk}/System/Library/PrivateFrameworks' if self.private_frameworks != '' else '', self.private_frameworks, self.frameworks, self.include, self.libraries, self.archs, f'-m{self.platform}-version-min={self.min_vers}']
            self.compiler.compile(files, f'{self.dir}/bin/{self.name}', build_flags)
            # rpath
            install_tool = cmd_in_path(
                f'{(str(self.prefix) + "/") if self.prefix is not None else ""}install_name_tool')
            if install_tool is None:
                # fall back to path
                install_tool = cmd_in_path('install_name_tool')
                if install_tool is None:
                    error('install_name_tool_not found.')
                    exit(1)
            # fix rpath
            rpath = '/var/jb/Library/Frameworks/' if self.luzbuild.rootless else '/Library/Frameworks'
            check_output(
                f'{install_tool} -add_rpath {rpath} {self.dir}/bin/{self.name}', shell=True)
            # ldid
            ldid = cmd_in_path(
                f'{(str(self.prefix) + "/") if self.prefix is not None else ""}ldid')
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

# module imports
from glob import glob
from json import loads
from multiprocessing.pool import ThreadPool
from os import makedirs, mkdir, path
from pyclang import CCompiler
from shutil import copytree
from subprocess import check_output
from time import time

# local imports
from ..deps import logos
from ..logger import log, error
from .module import Module
from ..utils import cmd_in_path, get_hash, setup_luz_dir


class Tweak(Module):
    def __init__(self, module: dict, key: str, compiler: CCompiler, control: str):
        # raw ctrl
        self.__raw_control = control
        # get luz dir
        self.dir = setup_luz_dir()
        # files
        files = module.get('files') if type(module.get(
            'files')) is list else [module.get('files')]
        super().__init__(module, key, compiler, control)
        self.files = self.__hash_files(files)
    

    def __hash_files(self, files: list) -> list:
        """Hash the files of the module, and compare them to their old hashes.

        :return: The list of changed files.
        """
        # make dirs
        if not path.exists(self.dir + '/obj'):
            mkdir(self.dir + '/obj')

        if not path.exists(self.dir + '/logos-processed'):
            mkdir(self.dir + '/logos-processed')

        if not path.exists(self.dir + '/dylib'):
            mkdir(self.dir + '/dylib')

        # changed files
        changed = []
        # old hashes
        old_hashlist = {}
        # check if hashlist exists
        if path.exists(self.dir + '/hashlist.json'):
            with open(self.dir + '/hashlist.json', 'r') as f:
                old_hashlist = loads(f.read())

        with open(self.dir + '/hashlist.json', 'w') as f:
            # loop files
            for file in files:
                # get file hash
                fhash = old_hashlist.get(file)
                # check if the file has changes
                if (fhash is not None and fhash != get_hash(file)) or (not path.exists(f'{self.dir}/obj/{path.basename(file)}.mm.o') and not path.exists(f'{self.dir}/obj/{path.basename(file)}.m.o')):
                    changed.append(file)
            # write new hashes
            f.write(str({file: get_hash(file)
                    for file in files}).replace("'", '"'))

        # files list
        files = changed if self.only_compile_changed else files
        # logos files
        files = logos(files)

        if len(files) == 0:
            log(f'Nothing to compile for module {self.name}.')
            return []

        # return files
        return files

    def __stage(self, rootless: bool = False):
        """Stage a deb to be packaged."""
        # make staging dirs
        if not path.exists(self.dir + '/stage/DEBIAN'):
            makedirs(self.dir + '/stage/DEBIAN')
        # write control
        with open(self.dir + '/stage/DEBIAN/control', 'w') as f:
            f.write(self.__raw_control)

        # dirs to make
        dirtomake = '/stage/Library/MobileSubstrate/' if not rootless else '/stage/var/jb/usr/lib/'
        dirtocopy = '/stage/Library/MobileSubstrate/DynamicLibraries/' if not rootless else '/stage/var/jb/usr/lib/TweakInject'
        # make proper dirs
        if not path.exists(self.dir + dirtomake):
            makedirs(self.dir + dirtomake)
        copytree(self.dir + '/dylib', self.dir + dirtocopy)
        with open(f'{self.dir}{dirtocopy}/{self.name}.plist', 'w') as f:
            filtermsg = 'Filter = {\n'
            # bundle filters
            if self.filter.get('bundles') is not None:
                filtermsg += '    Bundles = ( '
                for filter in self.filter.get('bundles'):
                    filtermsg += f'"{filter}", '
                filtermsg = filtermsg[:-2] + ' );\n'
            # executables filters
            if self.filter.get('executables') is not None:
                filtermsg += '    Executables = ( '
                for executable in self.filter.get('executables'):
                    filtermsg += f'"{executable}", '
                filtermsg = filtermsg[:-2] + ' );\n'
            filtermsg += '};'
            f.write(filtermsg)

    def __linker(self, rootless: bool = False):
        """Use a linker on the compiled files."""
        log(f'Linking compiled files to {self.name}.dylib...')
        files = ' '.join(glob(f'{self.dir}/obj/*.o'))
        self.compiler.compile(files, f'{self.dir}/dylib/{self.name}.dylib', ['-fobjc-arc' if self.arc else '', f'-isysroot {self.sdk}', '-Wall', '-O2', '-dynamiclib',
                              '-Xlinker', '-segalign', '-Xlinker 4000', self.frameworks, self.libraries, '-lc++' if ".mm" in files else '', self.include, self.librarydirs, self.archs])
        # rpath
        install_tool = cmd_in_path('install_name_tool')
        if install_tool is None:
            error('install_name_tool_not found.')
            exit(1)
        # fix rpath
        rpath = '/var/jb/Library/Frameworks/' if rootless else '/Library/Frameworks'
        check_output(f'{install_tool} -add_rpath {rpath} {self.dir}/dylib/{self.name}.dylib', shell=True)
        # ldid
        ldid = cmd_in_path('ldid')
        if ldid is None:
            error('ldid not found.')
            exit(1)
        # run ldid
        check_output(f'{ldid} -S {self.dir}/dylib/{self.name}.dylib', shell=True)
        

    def __compile_tweak_file(self, file):
        """Compile a tweak file."""
        log(f'Compiling {path.basename(file)}...')
        outName = f'{self.dir}/obj/{path.basename(file)}.o'
        # compile file
        try:
            self.compiler.compile(file, outName, [
                '-fobjc-arc' if self.arc else '', f'-isysroot {self.sdk}', '-Wall', '-O2', self.include, self.archs, '-c'])
        except Exception as e:
            print(e)
            exit(1)

    def compile(self, rootless: bool = False):
        """Compile the specified self.

        :param CCompiler compiler: The compiler to use.
        """

        start = time()

        # compile files
        with ThreadPool() as pool:
            pool.map(self.__compile_tweak_file, self.files)
        # link files
        self.__linker()

        # stage deb
        self.__stage(rootless=rootless)
        log(
            f'Finished compiling module "{self.name}" in {round(time() - start, 2)} seconds.')

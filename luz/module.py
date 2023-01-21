# module imports
from glob import glob
from json import loads
from multiprocessing.pool import ThreadPool
from os import makedirs, mkdir, path
from pyclang import CCompiler
from shutil import copytree, rmtree
from subprocess import getoutput
from time import time

# local imports
from .deps import clone_headers, clone_libraries, logos
from .logger import error, log, log_stdout, remove_log_stdout
from .utils import cmd_in_path, get_hash, setup_luz_dir


def get_safe(module: dict, key: str, default: str = None) -> str:
    """Gets a key from a dict safely.
    
    :param dict module: The dict to get the key from.
    :param str key: The key to get.
    :param str default: The default value to return if the key is not found.
    :return: The value of the key.
    """
    return module.get(key) if module.get(key) is not None else default


class Module:
    def __init__(self, module: dict, key: str, compiler: CCompiler, control: str):
        # declare raw module
        self.__raw_module = module
        
        # raw control
        self.__raw_control = control
        
        # type
        self.type = get_safe(module, 'type', 'tweak')
        
        # process
        self.filter = get_safe(module, 'filter', 'com.apple.SpringBoard')
        
        # compiler
        self.compiler = compiler

        # name
        self.name = key

        # use arc
        self.arc = bool(
            get_safe(module, 'arc', True if self.type == 'tweak' else False))

        # only compile changes
        self.only_compile_changed = get_safe(
            module, 'only_compile_changed', False)

        # ensure files are defined
        if module.get('files') is None:
            error(f'No files specified for module {self.name}.')
            exit(1)
        
        # set library files dir
        self.librarydirs = f'-L{clone_libraries()}'
        # get luz dir
        self.dir = setup_luz_dir()
        # remove staging
        if path.exists(self.dir + '/stage'):
            rmtree(self.dir + '/stage')
        # files
        files = module.get('files') if type(module.get('files')) is list else [module.get('files')]
        self.files = self.__hash_files(files)

        # define default values
        frameworksA = '-framework CoreFoundation -framework Foundation'
        librariesA = '-lsubstrate -lobjc' if self.type == 'tweak' else ''
        includesA = f'-I{clone_headers()}'
        archsA = ''
        sdkA = get_safe(module, 'sdk', '')
        
        # add module frameworks
        frameworks = get_safe(module, 'frameworks', [])
        if frameworks != []:
            for framework in frameworks:
                frameworksA += f' -framework {framework}'
        # set
        self.frameworks = frameworksA

        # add module libraries
        libraries = get_safe(module, 'libraries', [])
        if libraries != []:
            for library in libraries:
                librariesA += f' -l{library}'
        # set
        self.libraries = librariesA

        # add module include directories
        include = get_safe(module, 'include', [])
        if include != []:
            for include in include:
                includesA += f' -I{include}'
        # set
        self.include = includesA

        # add module architectures
        archs = get_safe(module, 'archs', ['arm64', 'arm64e'])
        if archs != []:
            for arch in archs:
                archsA += f' -arch {arch}'
        # set
        self.archs = archsA

        # attempt to manually find an sdk
        if sdkA == '':
            xcbuild = cmd_in_path('xcodebuild')
            if xcbuild is None:
                error(
                    'Xcode does not appear to be installed. Please specify an SDK manually.')
                exit(1)
            else:
                log_stdout('Finding an SDK...')
                sdkA = getoutput(
                    f'{xcbuild} -version -sdk iphoneos Path').split('\n')[-1]
                if sdkA == '':
                    error('Could not find an SDK. Please specify one manually.')
                    exit(1)
                remove_log_stdout('Finding an SDK...')
        else:
            # ensure sdk exists
            if not path.exists(sdkA):
                error(f'Specified SDK path "{sdkA}" does not exist.')
                exit(1)
        # set
        self.sdk = sdkA


    def __hash_files(self, files: list) -> list:
        """Hash the files of the module, and compare them to their old hashes.
        
        :return: The list of changed files.
        """
        # make dirs if tweak
        if self.type == 'tweak':
            if not path.exists(self.dir + '/obj'):
                mkdir(self.dir + '/obj')

            if not path.exists(self.dir + '/logos-processed'):
                mkdir(self.dir + '/logos-processed')

            if not path.exists(self.dir + '/dylib'):
                mkdir(self.dir + '/dylib')
        elif self.type == 'tool':
            if not path.exists(self.dir + '/bin'):
                mkdir(self.dir + '/bin')
                
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
        if self.type == 'tweak':
            files = logos(files)

        if len(files) == 0:
            log(f'Nothing to compile.')
            exit(0)

        # return files
        return files
    
    
    def __stage(self, rootless: bool = False):
        """Stage a deb to be packaged."""
        # make staging dirs
        if not path.exists(self.dir + '/stage/DEBIAN'): makedirs(self.dir + '/stage/DEBIAN')
        # write control
        with open(self.dir + '/stage/DEBIAN/control', 'w') as f:
            f.write(self.__raw_control)
        # if non-rootless tweak, make proper dirs
        if not rootless and self.type == 'tweak':
            if not path.exists(self.dir + '/stage/Library/MobileSubstrate'): makedirs(self.dir + '/stage/Library/MobileSubstrate/')
            copytree(self.dir + '/dylib', self.dir + '/stage/Library/MobileSubstrate/DynamicLibraries')
            with open(f'{self.dir}/stage/Library/MobileSubstrate/DynamicLibraries/{self.name}.plist', 'w') as f:
                # handle single filter
                if type(self.filter) == str or len(self.filter) == 1:
                    f.write("{ Filter = { Bundles = ( \"" + (self.filter if type(self.filter) == str else self.filter[0]) + "\" ); }; }")
                # handle multiple filters
                elif type(self.filter) == list and len(self.filter) > 1:
                    filterlist = '{ Filter = { Bundles = ( '
                    for filter in self.filter:
                        filterlist += f'"{filter}", '
                    filterlist = filterlist[:-2] + ' ); }; }'
                    f.write(filterlist)
        # if non-rootless tool, make proper dirs
        if not rootless and self.type == 'tool':
            if not path.exists(self.dir + '/stage/usr'): makedirs(self.dir + '/stage/usr')
            copytree(self.dir + '/bin', self.dir + '/stage/usr/bin')
        

    def __linker(self):
        """Use a linker on the compiled files."""
        log_stdout('Linking...')
        files = ' '.join(glob(f'{self.dir}/obj/*.o'))
        self.compiler.compile(files, f'{self.dir}/dylib/{self.name}.dylib', ['-fobjc-arc' if self.arc else '', f'-isysroot {self.sdk}', '-Wall', '-O2', '-dynamiclib', '-Xlinker', '-segalign', '-Xlinker 4000', self.frameworks, self.libraries, '-lc++' if ".mm" in files else '', self.include, self.librarydirs, self.archs])
        remove_log_stdout('Linking...')
        
    def __compile_tweak_file(self, file):
        """Compile a tweak file."""
        log_stdout(f'Compiling {path.basename(file)}...')
        outName = f'{self.dir}/obj/{path.basename(file)}.o'
        # compile file
        try:
            self.compiler.compile(file, outName, [
                '-fobjc-arc' if self.arc else '', f'-isysroot {self.sdk}', '-Wall', '-O2', self.include, self.archs, '-c'])
        except Exception as e:
            print(e)
            exit(1)
        # remove log
        remove_log_stdout(f'Compiling {path.basename(file)}...')


    def compile(self):
        """Compile the specified self.
        
        :param CCompiler compiler: The compiler to use.
        """
        
        start = time()
        
        if self.type == 'tweak':
            # compile files
            with ThreadPool() as pool:
                pool.map(self.__compile_tweak_file, self.files)
            # link files
            self.__linker()
        elif self.type == 'tool':
            # compile files
            log_stdout(f'Compiling...')
            try:
                self.compiler.compile(' '.join(self.files), f'{self.dir}/bin/{self.name}', [f'-isysroot {self.sdk}', self.frameworks, self.include, self.libraries, self.archs])
            except Exception as e:
                print(e)
                exit(1)
                
            # remove log
            remove_log_stdout(f'Compiling...')

        self.__stage()
        log(f'Finished compiling module "{self.name}" in {round(time() - start, 2)} seconds.')
        
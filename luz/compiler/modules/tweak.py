# module imports
from json import loads
from multiprocessing.pool import ThreadPool
from os import makedirs, mkdir
from shutil import copytree
from subprocess import check_output
from time import time

# local imports
from ..deps import logos
from ...common.logger import log, error, warn
from .module import Module
from ...common.utils import cmd_in_path, get_hash, resolve_path


class Tweak(Module):
    def __init__(self, **kwargs):
        """Tweak module class
        
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
        # directories
        self.obj_dir = resolve_path(f'{self.dir}/obj')
        self.logos_dir = resolve_path(f'{self.dir}/logos-processed')
        self.dylib_dir = resolve_path(f'{self.dir}/dylib')
        self.files = self.__hash_files(files)
    

    def __hash_files(self, files: list) -> list:
        """Hash the files of the module, and compare them to their old hashes.

        :param list files: Files to hash.
        :return: The list of changed files.
        """
        # make dirs
        if not self.obj_dir.exists():
            mkdir(self.obj_dir)
        
        if not self.logos_dir.exists():
            mkdir(self.logos_dir)
        
        if not self.dylib_dir.exists():
            mkdir(self.dylib_dir)
            
        files_to_compile = []
            
        # file path formatting
        for file in files:
            file_path = resolve_path(file)
            if type(file_path) is list:
                for f in file_path:
                    files_to_compile.append(f)
            else:
                files_to_compile.append(file_path)
                
        # changed files
        changed = []
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
                fhash = old_hashlist.get(file)
                new_hash = get_hash(file)
                # check if the file has changes
                file_path = resolve_path(file)
                if (fhash is not None and fhash != new_hash) or (not resolve_path(f'{self.dir}/obj/{file_path.name}.mm.o').exists() and not resolve_path(f'{self.dir}/obj/{file_path.name}.m.o').exists() and not resolve_path(f'{self.dir}/obj/{file_path.name}.o').exists()):
                    changed.append(file)
                # add to new hashes
                new_hashes[str(file)] = new_hash
            # write new hashes
            new_hashes.update({k: v for k, v in old_hashlist.items() if k in new_hashes})
            f.write(str(new_hashes).replace("'", '"'))

        # files list
        files = changed if self.only_compile_changed else files_to_compile
        
        # handle files not needing compilation
        if len(files) == 0:
            log(f'Nothing to compile for module {self.name}.')
            return []
        
        # use logos files if necessary
        if filter(lambda x: '.x' in x, files) != []:
            files = logos(self.luzbuild, files)

        # return files
        return files

    def __stage(self):
        """Stage a deb to be packaged."""
        # dirs to make
        if self.install_dir is None:
            dirtomake = resolve_path(f'{self.dir}/stage/Library/MobileSubstrate/') if not self.luzbuild.rootless else resolve_path(f'{self.dir}/stage/var/jb/usr/lib/')
            dirtocopy = resolve_path(f'{self.dir}/stage/Library/MobileSubstrate/DynamicLibraries/') if not self.luzbuild.rootless else resolve_path(f'{self.dir}/stage/var/jb/usr/lib/TweakInject')
        else:
            if self.luzbuild.rootless: warn('Custom install directory specified, and rootless is enabled. Prefixing path with /var/jb.')
            self.install_dir = resolve_path(self.install_dir)
            dirtomake = resolve_path(f'{self.dir}/stage/{self.install_dir.parent}') if not self.luzbuild.rootless else resolve_path(f'{self.dir}/stage/var/jb/{self.install_dir.parent}')
            dirtocopy = resolve_path(f'{self.dir}/stage/{self.install_dir}') if not self.luzbuild.rootless else resolve_path(f'{self.dir}/stage/var/jb/{self.install_dir}')
        # make proper dirs
        if not dirtomake.exists():
            makedirs(dirtomake)
        copytree(f'{self.dir}/dylib', dirtocopy, dirs_exist_ok=True)
        with open(f'{dirtocopy}/{self.name}.plist', 'w') as f:
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

    def __linker(self):
        """Use a linker on the compiled files."""
        log(f'Linking compiled files to {self.name}.dylib...')
        # get files by extension
        files = ''
        o_files = resolve_path(f'{self.dir}/obj/*.o')
        for file in o_files:
            if files != '': files += ' '
            files += f'{str(file)}'
        
        # define build flags
        build_flags = ['-fobjc-arc' if self.arc else '', f'-isysroot {self.sdk}', self.luzbuild.warnings, f'-O{self.luzbuild.optimization}', '-dynamiclib',
                       '-Xlinker', '-segalign', '-Xlinker 4000', f'-F{self.sdk}/System/Library/PrivateFrameworks' if self.private_frameworks != '' else '', self.private_frameworks, self.frameworks, self.libraries, '-lc++' if ".mm" in files else '', self.include, self.librarydirs, self.archs, f'-m{self.platform}-version-min={self.min_vers}']
        # compile with clang using build flags
        self.compiler.compile(files, f'{self.dir}/dylib/{self.name}.dylib', build_flags)
        # rpath
        install_tool = cmd_in_path(f'{(str(self.prefix) + "/") if self.prefix is not None else ""}install_name_tool')
        if install_tool is None:
            # fall back to path
            install_tool = cmd_in_path('install_name_tool')
            if install_tool is None:
                error('install_name_tool_not found.')
                exit(1)
        # fix rpath
        rpath = '/var/jb/Library/Frameworks/' if self.luzbuild.rootless else '/Library/Frameworks'
        check_output(f'{install_tool} -add_rpath {rpath} {self.dir}/dylib/{self.name}.dylib', shell=True)
        # ldid
        ldid = cmd_in_path(f'{(str(self.prefix) + "/") if self.prefix is not None else ""}ldid')
        if ldid is None:
            # fall back to path
            ldid = cmd_in_path('ldid')
            if ldid is None:
                error('ldid not found.')
                exit(1)
        # run ldid
        check_output(f'{ldid} {self.luzbuild.entflag}{self.luzbuild.entfile} {self.dir}/dylib/{self.name}.dylib', shell=True)
        

    def __compile_tweak_file(self, file):
        """Compile a tweak file.
        
        :param str file: The file to compile.
        """
        path_to_compile = ''
        orig_path = ''
        # handle logos files
        if file.get('logos') == True:
            # set compile path
            path_to_compile = file.get('new_path')
            # set original path
            orig_path = file.get('old_path')
            # include path
            include_path = '/'.join(str(orig_path).split('/')[:-1])
            # add it to include if it's not already there
            if include_path not in self.include:
                self.include += ' -I' + include_path
        # handle normal files
        else:
            # set compile path
            path_to_compile = file.get('path')
            # set original path
            orig_path = file.get('path')
        log(f'Compiling {orig_path}...')
        outName = f'{self.dir}/obj/{resolve_path(path_to_compile).name}.o'
        # compile file
        try:
            build_flags = ['-fobjc-arc' if self.arc else '',
                           f'-isysroot {self.sdk}', self.luzbuild.warnings, f'-O{self.luzbuild.optimization}', self.archs, self.include, f'-m{self.platform}-version-min={self.min_vers}',  '-c']
            check_output(f'{self.luzbuild.cc} {path_to_compile} -o {outName} {" ".join(build_flags)}', shell=True)
            #self.compiler.compile(path_to_compile, outName, build_flags)
        except Exception as e:
            exit(1)

    def compile(self):
        """Compile."""

        start = time()

        # compile files
        with ThreadPool() as pool:
            pool.map(self.__compile_tweak_file, self.files)
        # link files
        self.__linker()

        # stage deb
        self.__stage()
        log(
            f'Finished compiling module "{self.name}" in {round(time() - start, 2)} seconds.')
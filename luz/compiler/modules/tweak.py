# module imports
from json import loads
from os import makedirs
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
        # current time
        self.now = time()
        # kwargs parsing
        module = kwargs.get('module')
        # files
        files = module.get('files') if type(module.get(
            'files')) is list else [module.get('files')]
        super().__init__(module, kwargs.get('key'), kwargs.get('luzbuild'))
        # directories
        self.obj_dir = resolve_path(f'{self.dir}/obj/{self.name}')
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
            makedirs(self.obj_dir)
        
        if not self.logos_dir.exists():
            makedirs(self.logos_dir)
        
        if not self.dylib_dir.exists():
            makedirs(self.dylib_dir)
            
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
                if (fhash is not None and fhash != new_hash) or (not resolve_path(f'{self.dir}/obj/{self.name}/{file_path.name}.mm.o').exists() and not resolve_path(f'{self.dir}/obj/{self.name}/{file_path.name}.m.o').exists() and not resolve_path(f'{self.dir}/obj/{self.name}/{file_path.name}.o').exists()):
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
        # lipo
        lipod = False
        # get files by extension
        files = ''
        new_files = []
        # loop through files that were compiled
        for file in resolve_path(f'{self.dir}/obj/{self.name}/*.o'):
            # handle swift files
            if '.swift.' in str(file) and not lipod:
                # prepare lipo command
                lipo = cmd_in_path(
                    f'{(str(self.prefix) + "/") if self.prefix is not None else ""}lipo')
                if lipo is None:
                    # fall back to path
                    lipo = cmd_in_path('lipo')
                    if lipo is None:
                        error('lipo not found.')
                        exit(1)
                # combine swift files into one file for specific arch
                check_output(f'{lipo} -create -output {self.dir}/obj/{self.name}/{self.name}-swift-lipo {self.dir}/obj/{self.name}/*.swift.*-{self.now}.o && rm -rf {self.dir}/obj/{self.name}/*.swift.*-{self.now}.o', shell=True)
                # add lipo file to files list
                new_files.append(f'{self.dir}/obj/{self.name}/{self.name}-swift-lipo')
                # let the compiler know that we lipod
                lipod = True
            elif not '.swift.' in str(file):
                new_files.append(file)
        
        for file in new_files:
            if files != '': files += ' '
            files += str(file)
        
        try:
            if f'{self.dir}/obj/{self.name}/{self.name}-swift-lipo' in files:
                # define build flags
                build_flags = [f'-sdk {self.sdk}',
                            '-Xlinker', '-segalign', '-Xlinker 4000', '-emit-library', f'-F{self.sdk}/System/Library/PrivateFrameworks' if self.private_frameworks != '' else '', self.private_frameworks, self.frameworks, self.libraries, '-lc++' if ".mm" in files else '', self.include, self.librarydirs, self.luzbuild.swiftflags]
                platform = 'ios' if self.platform == 'iphoneos' else self.platform
                for arch in self.archs.split(' -arch '):
                    if arch == '':
                        continue
                    outName = f'{self.dir}/dylib/{self.name}_{arch.replace(" ", "")}.dylib'
                    arch_formatted = f' -target {arch.replace(" ", "")}-apple-{platform}{self.min_vers}'
                    # compile with swiftc using build flags
                    check_output(f'{self.luzbuild.swift} {files} -o {outName} {arch_formatted} {" ".join(build_flags)}', shell=True)
                
                # lipo the dylibs
                check_output(f'{lipo} -create -output {self.dir}/dylib/{self.name}.dylib {self.dir}/dylib/{self.name}_*.dylib && rm -rf {self.dir}/dylib/{self.name}_*.dylib', shell=True)
            else:
                # define build flags
                build_flags = ['-fobjc-arc' if self.arc else '', f'-isysroot {self.sdk}', self.luzbuild.warnings, f'-O{self.luzbuild.optimization}', '-dynamiclib',
                            '-Xlinker', '-segalign', '-Xlinker 4000', f'-F{self.sdk}/System/Library/PrivateFrameworks' if self.private_frameworks != '' else '', self.private_frameworks, self.frameworks, self.libraries, '-lc++' if ".mm" in files else '', self.include, self.librarydirs, self.archs, f'-m{self.platform}-version-min={self.min_vers}', self.luzbuild.cflags]
                # compile with clang using build flags
                check_output(
                    f'{self.luzbuild.cc} -o {self.dir}/dylib/{self.name}.dylib {files} {" ".join(build_flags)}', shell=True)
        except:
            error(f'An error occured when attempting to link the compiled files. ({self.name})')
            exit(1)
        
        try:
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
        except:
            error(f'An error occured when trying to add rpath to "{self.dir}/dylib/{self.name}.dylib". ({self.name})')
            exit(1)
        
        try:
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
        except:
            error(f'An error occured when trying to add rpath to "{self.dir}/dylib/{self.name}.dylib". ({self.name})')
            exit(1)
        

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
        outName = f'{self.dir}/obj/{self.name}/{resolve_path(path_to_compile).name}.o'
        # compile file
        try:
            is_swift = str(orig_path.name).endswith('swift')
            if is_swift:
                # format platform
                platform = 'ios' if self.platform == 'iphoneos' else self.platform
                # define build args
                build_flags = [f'-sdk {self.sdk}', self.include,  '-c', '-emit-object', self.luzbuild.swiftflags]
                for arch in self.archs.split(' -arch '):
                    # skip empty archs
                    if arch == '':
                        continue
                    outName = f'{self.dir}/obj/{self.name}/{resolve_path(path_to_compile).name}.{arch.replace(" ", "")}-{self.now}.o'
                    # format arch
                    arch_formatted = f' -target {arch.replace(" ", "")}-apple-{platform}{self.min_vers}'
                    # use swiftc to compile
                    check_output(
                        f'{self.luzbuild.swift} {path_to_compile} -o {outName} {arch_formatted} {" ".join(build_flags)}', shell=True)
            else:
                outName = f'{self.dir}/obj/{self.name}/{resolve_path(path_to_compile).name}.o'
                build_flags = ['-fobjc-arc' if self.arc else '',
                               f'-isysroot {self.sdk}', self.luzbuild.warnings, f'-O{self.luzbuild.optimization}', self.archs, self.include, f'-m{self.platform}-version-min={self.min_vers}',  '-c', self.luzbuild.cflags]
                # use clang to compile
                check_output(
                    f'{self.luzbuild.cc} {path_to_compile} -o {outName} {" ".join(build_flags)}', shell=True)
            #self.compiler.compile(path_to_compile, outName, build_flags)
        except Exception as e:
            exit(1)

    def compile(self):
        """Compile."""

        start = time()

        # compile files
        self.luzbuild.pool.map(self.__compile_tweak_file, self.files)
        # link files
        self.__linker()
        # stage deb
        self.__stage()
        log(
            f'Finished compiling module "{self.name}" in {round(time() - start, 2)} seconds.')

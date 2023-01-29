# module imports
from json import loads
from os import makedirs
from shutil import copytree
from subprocess import check_output
from time import time

# local imports
from ...common.logger import warn
from .module import Module
from ...common.utils import get_hash, resolve_path


class Tool(Module):
    def __init__(self, **kwargs):
        """Tool module class.
        
        :param dict module: Module dictionary to build
        :param str key: Module key name
        :param LuzBuild luzbuild: Luzbuild class
        """
        # time
        self.now = time()
        # kwargs parsing
        module = kwargs.get('module')
        # files
        files = module.get('files') if type(module.get(
            'files')) is list else [module.get('files')]
        super().__init__(module, kwargs.get('key'), kwargs.get('luzbuild'))
        # bin directory
        self.obj_dir = resolve_path(f'{self.dir}/obj/{self.name}')
        self.bin_dir = resolve_path(f'{self.dir}/bin')
        self.files = self.__hash_files(files)

    def __hash_files(self, files: list) -> list:
        """Hash the files of the module, and compare them to their old hashes.

        :return: The list of changed files.
        """
        # make dirs
        if not self.obj_dir.exists():
            makedirs(self.obj_dir)
        
        if not self.bin_dir.exists():
            makedirs(self.bin_dir)
            
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

    def __linker(self):
        """Use a linker on the compiled files."""
        self.log_stdout(f'Linking compiled files to executable "{self.name}"...')
        # lipo
        lipod = False
        # get files by extension
        new_files = []
        # loop through files that were compiled
        for file in resolve_path(f'{self.dir}/obj/{self.name}/*.o'):
            # handle swift files
            if '.swift.' in str(file) and not lipod:
                # combine swift files into one file for specific arch
                check_output(f'{self.luzbuild.lipo} -create -output {self.dir}/obj/{self.name}/{self.name}-swift-lipo {self.dir}/obj/{self.name}/*.swift.*-{self.now}.o && rm -rf {self.dir}/obj/{self.name}/*.swift.*-{self.now}.o', shell=True)
                # add lipo file to files list
                new_files.append(resolve_path(f'{self.dir}/obj/{self.name}/{self.name}-swift-lipo'))
                # let the compiler know that we lipod
                lipod = True
            elif not '.swift.' in str(file):
                new_files.append(resolve_path(file))
        
        try:
            if lipod:
                # define build flags
                platform = 'ios' if self.luzbuild.platform == 'iphoneos' else self.luzbuild.platform
                for arch in self.luzbuild.archs.split(' -arch '):
                    if arch == '':
                        continue
                    out_name = f'{self.dir}/bin/{self.name}_{arch.replace(" ", "")}'
                    build_flags = [f'-sdk {self.luzbuild.sdk}',
                                   '-Xlinker', '-segalign', '-Xlinker 4000', f'-F{self.luzbuild.sdk}/System/Library/PrivateFrameworks' if self.private_frameworks != '' else '', self.private_frameworks, self.frameworks, self.libraries, '-lc++' if ".mm" in new_files else '', self.include, self.library_dirs, self.luzbuild.swift_flags, f'-target {arch.replace(" ", "")}-apple-{platform}{self.luzbuild.min_vers}']
                    # compile with swiftc using build flags
                    self.luzbuild.swift_compiler.compile(new_files, out_name, build_flags)
                
                # lipo compiled files
                check_output(f'{self.luzbuild.lipo} -create -output {self.dir}/bin/{self.name} {self.dir}/bin/{self.name}_* && rm -rf {self.dir}/bin/{self.name}_*', shell=True)
            else:
                # define build flags
                build_flags = ['-fobjc-arc' if self.arc else '', f'-isysroot {self.luzbuild.sdk}', self.luzbuild.warnings, f'-O{self.luzbuild.optimization}',
                            '-Xlinker', '-segalign', '-Xlinker 4000', f'-F{self.luzbuild.sdk}/System/Library/PrivateFrameworks' if self.private_frameworks != '' else '', self.private_frameworks, self.frameworks, self.libraries, '-lc++' if ".mm" in new_files else '', self.include, self.library_dirs, self.luzbuild.archs, f'-m{self.luzbuild.platform}-version-min={self.luzbuild.min_vers}', self.luzbuild.c_flags]
                # compile with clang using build flags
                self.luzbuild.c_compiler.compile(new_files, f'{self.dir}/bin/{self.name}', build_flags)
        except:
            return f'An error occured when attempting to link the compiled files for module "{self.name}".'
        
        try:
            # fix rpath
            rpath = '/var/jb/Library/Frameworks/' if self.luzbuild.rootless else '/Library/Frameworks'
            check_output(
                f'{self.luzbuild.install_name_tool} -add_rpath {rpath} {self.dir}/bin/{self.name}', shell=True)
        except:
            return f'An error occured when trying to add rpath to "{self.dir}/bin/{self.name}" for module "{self.name}".'
        
        try:
            check_output(
                f'{self.luzbuild.strip} {self.dir}/bin/{self.name}', shell=True)
        except:
            return f'An error occured when trying to strip "{self.dir}/bin/{self.name}" for module "{self.name}".'
        
        try:
            # run ldid
            check_output(
                f'{self.luzbuild.ldid} {self.luzbuild.entflag}{self.luzbuild.entfile} {self.dir}/bin/{self.name}', shell=True)
        except:
            return f'An error occured when trying codesign "{self.dir}/bin/{self.name}" for module "{self.name}".'
        
        self.remove_log_stdout(f'Linking compiled files to executable "{self.name}"...')
            

    def __compile_tool_file(self, file):
        """Compile a tool file.
        
        :param str file: The file to compile.
        """
        self.log_stdout(f'Compiling "{file}"...')
        # compile file
        try:
            is_swift = str(file.name).endswith('swift')
            if is_swift:
                # format platform
                platform = 'ios' if self.luzbuild.platform == 'iphoneos' else self.luzbuild.platform
                for arch in self.luzbuild.archs.split(' -arch '):
                    # skip empty archs
                    if arch == '':
                        continue
                    out_name = f'{self.dir}/obj/{self.name}/{resolve_path(file).name}.{arch.replace(" ", "")}-{self.now}.o'
                    # define build flags
                    build_flags = [f'-sdk {self.luzbuild.sdk}', self.include,  '-c', '-emit-object', self.luzbuild.swift_flags, f'-target {arch.replace(" ", "")}-apple-{platform}{self.luzbuild.min_vers}']
                    # compile with swiftc using build flags
                    self.luzbuild.swift_compiler.compile(file, out_name, build_flags)
            else:
                out_name = f'{self.dir}/obj/{self.name}/{resolve_path(file).name}.o'
                build_flags = ['-fobjc-arc' if self.arc else '',
                               f'-isysroot {self.luzbuild.sdk}', self.luzbuild.warnings, f'-O{self.luzbuild.optimization}', self.luzbuild.archs, self.include, f'-m{self.luzbuild.platform}-version-min={self.luzbuild.min_vers}', self.luzbuild.c_flags, '-c']
                # compile with clang using build flags
                self.luzbuild.c_compiler.compile(file, out_name, build_flags)
            
        except:
            return f'An error occured when attempting to compile file "{file}" for module "{self.name}".'
        
        self.remove_log_stdout(f'Compiling "{file}"...')


    def __stage(self):
        """Stage a deb to be packaged."""
        # dirs to make
        if self.install_dir is None:
            dirtomake = resolve_path(f'{self.dir}/_/usr') if not self.luzbuild.rootless else resolve_path(f'{self.dir}/_/var/jb/usr')
            dirtocopy = resolve_path(f'{self.dir}/_/usr/bin') if not self.luzbuild.rootless else resolve_path(f'{self.dir}/_/var/jb/usr/bin')
        else:
            if self.luzbuild.rootless: warn(f'Custom install directory for module "{self.name}" was specified, and rootless is enabled. Prefixing path with /var/jb.')
            self.install_dir = resolve_path(self.install_dir)
            dirtomake = resolve_path(f'{self.dir}/_/{self.install_dir.parent}') if not self.luzbuild.rootless else resolve_path(f'{self.dir}/_/var/jb/{self.install_dir.parent}')
            dirtocopy = resolve_path(f'{self.dir}/_/{self.install_dir}') if not self.luzbuild.rootless else resolve_path(f'{self.dir}/_/var/jb/{self.install_dir}')
        # make proper dirs
        if not dirtomake.exists():
            makedirs(dirtomake, exist_ok=True)
        copytree(self.bin_dir, dirtocopy, dirs_exist_ok=True)
        

    def compile(self):
        """Compile the specified self."""
        # compile files
        compile_results = self.luzbuild.pool.map(self.__compile_tool_file, self.files)
        for result in compile_results:
            if result is not None:
                return result
        # link files
        linker_results = self.__linker()
        if linker_results is not None:
            return linker_results
        # stage deb
        self.__stage()

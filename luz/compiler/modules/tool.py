# module imports
from os import makedirs
from shutil import copytree, rmtree
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
            makedirs(self.obj_dir, exist_ok=True)
        
        if not self.bin_dir.exists():
            makedirs(self.bin_dir, exist_ok=True)
            
        files_to_compile = []
        
        # file path formatting
        for file in files:
            if not file.startswith('/'): file = f'{self.luzbuild.path}/{file}'
            file_path = resolve_path(file)
            if type(file_path) is list:
                for f in file_path:
                    files_to_compile.append(f)
            else:
                files_to_compile.append(file_path)
            
        # changed
        changed = []
        # get hashes
        new_hashes = {}
        # arch count
        arch_count = len(self.luzbuild.archs)
        # loop files
        for file in files_to_compile:
            # get file hash
            fhash = self.luzbuild.hashlist.get(str(file))
            new_hash = get_hash(file)
            if fhash is None: changed.append(file)
            elif fhash == new_hash:
                # variables
                object_paths = resolve_path(f'{self.dir}/obj/{self.name}/*/{file.name}*-*.o')
                dylib_paths = resolve_path(f'{self.dir}/obj/{self.name}/*/{self.name}')
                if len(object_paths) < arch_count or len(dylib_paths) < arch_count:
                    changed.append(file)
            elif fhash != new_hash: changed.append(file)
            # add to new hashes
            new_hashes[str(file)] = new_hash

        # write new hashes
        self.luzbuild.update_hashlist(new_hashes)

        # files list
        files = changed if self.only_compile_changed else files_to_compile

        # handle files not needing compilation
        if len(files) == 0:
            self.log(f'Nothing to compile for module "{self.name}".')
            return []

        # return files
        return files

    def __linker(self):
        """Use a linker on the compiled files."""
        if len(self.files) == 0 and resolve_path(f'{self.dir}/dylib/{self.name}.dylib').exists():
            return
        
        self.log_stdout(f'Linking compiled files to executable "{self.name}"...')
        
        for arch in self.luzbuild.archs:
            try:
                # define compiler flags
                build_flags = ['-fobjc-arc' if self.arc else '',
                            f'-isysroot {self.luzbuild.sdk}', self.warnings, f'-O{self.optimization}', f'-arch {arch}', self.include, self.library_dirs, self.libraries, self.frameworks, self.private_frameworks, f'-m{self.luzbuild.platform}-version-min={self.luzbuild.min_vers}', self.c_flags]
                self.luzbuild.c_compiler.compile(resolve_path(f'{self.dir}/obj/{self.name}/{arch}/*.o'), outfile=f'{self.dir}/obj/{self.name}/{arch}/{self.name}', args=build_flags)
            except:
                return f'An error occured when trying to link files for module "{self.name}" for architecture "{arch}".'

        # link
        try:
            check_output(f'{self.luzbuild.lipo} -create -output {self.dir}/bin/{self.name} {self.dir}/obj/{self.name}/*/{self.name}', shell=True)
        except:
            return f'An error occured when trying to lipo files for module "{self.name}".'
        
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
                f'{self.luzbuild.ldid} {self.entflag}{self.entfile} {self.dir}/bin/{self.name}', shell=True)
        except:
            return f'An error occured when trying codesign "{self.dir}/bin/{self.name}" for module "{self.name}".'
        
        self.remove_log_stdout(f'Linking compiled files to executable "{self.name}"...')
            

    def __compile_tool_file(self, file) -> bool:
        """Compile a tool file.
        
        :param str file: The file to compile.
        """
        files_minus_to_compile = list(filter(lambda x: x != file and str(x).endswith('.swift'), self.files))
        # compile file
        try:
            if str(file).endswith('.swift'):
                # define build flags
                build_flags = ['-frontend', '-c', f'-module-name {self.name}', f'-sdk "{self.luzbuild.sdk}"', self.include, self.library_dirs, self.libraries, self.frameworks, self.private_frameworks, self.swift_flags, self.bridging_headers]
                # format platform
                platform = 'ios' if self.luzbuild.platform == 'iphoneos' else self.luzbuild.platform
                for arch in self.luzbuild.archs:
                    rmtree(f'{self.dir}/obj/{self.name}/{arch}/{file.name}-*', ignore_errors=True)
                    out_name = f'{self.dir}/obj/{self.name}/{arch}/{file.name}-{self.now}'
                    # arch
                    arch_formatted = f'-target {arch}-apple-{platform}{self.luzbuild.min_vers}'
                    # compile with swift using build flags
                    self.luzbuild.swift_compiler.compile([file] + files_minus_to_compile, outfile=out_name+'.o', args=build_flags+[arch_formatted, f'-emit-module-path {out_name}.swiftmodule', '-primary-file'])
            else:
                for arch in self.luzbuild.archs:
                    rmtree(f'{self.dir}/obj/{self.name}/{arch}/{file.name}-*', ignore_errors=True)
                    out_name = f'{self.dir}/obj/{self.name}/{arch}/{file.name}-{self.now}.o'
                    build_flags = ['-fobjc-arc' if self.arc else '',
                                f'-isysroot {self.luzbuild.sdk}', self.warnings, f'-O{self.optimization}', f'-arch {arch}', self.include, f'-m{self.luzbuild.platform}-version-min={self.luzbuild.min_vers}', self.c_flags, '-c']
                    # compile with clang using build flags
                    self.luzbuild.c_compiler.compile(file, out_name, build_flags)
            
        except:
            return f'An error occured when attempting to compile for module "{self.name}".'


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
        for arch in self.luzbuild.archs:
            rmtree(f'{self.dir}/obj/{self.name}/{arch}', ignore_errors=True)
            makedirs(f'{self.dir}/obj/{self.name}/{arch}', exist_ok=True)
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

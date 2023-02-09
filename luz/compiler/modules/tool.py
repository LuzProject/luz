# module imports
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
        for file in files_to_compile:
            # get hashes
            fhash = self.luzbuild.hashlist.get(str(file))
            new_hash = get_hash(file)
            # variables
            objcpp_path = resolve_path(f'{self.dir}/obj/{self.name}/{file.name}.mm')
            objc_path = resolve_path(f'{self.dir}/obj/{self.name}/{file.name}.m')
            c_path = resolve_path(f'{self.dir}/obj/{self.name}/{file.name}.c')
            other_path = resolve_path(f'{self.dir}/obj/{self.name}/{file.name}.*')
            lipod_path = resolve_path(f'{self.dir}/obj/*{self.name}*-*.*')
            # check if file needs to be compiled
            if (fhash is not None and fhash != new_hash) or (not objcpp_path.exists() and not objc_path.exists() and not c_path.exists()):
                if len(lipod_path) == 0 and len(other_path) == 0:
                    changed.append(file)
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
        self.log_stdout(f'Linking compiled files to executable "{self.name}"...')

        check_output(f'{self.luzbuild.lipo} -create -output {self.dir}/bin/{self.name} {self.dir}/obj/{self.name}/*', shell=True)
        
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
            

    def __compile_tool_files(self, files) -> bool:
        """Compile tool files.
        
        :param str file: The file to compile.
        """
        # loop through files
        swift = list(filter(lambda x: str(x).endswith('swift'), files))
        c = list(filter(lambda x: not str(x).endswith('swift'), files))
        # compile file
        try:
            if len(swift) != 0:
                # convert paths to strings
                swift_strings = []
                for file in swift:
                    swift_strings.append(str(file))
                
                # define build flags
                build_flags = [f'-sdk {self.luzbuild.sdk}', self.include, self.luzbuild.swift_flags]
                out_name = f'{self.dir}/obj/{self.name}/{resolve_path("".join(swift_strings)).name}'
                # format platform
                platform = 'ios' if self.luzbuild.platform == 'iphoneos' else self.luzbuild.platform
                for arch in self.luzbuild.archs:
                    # arch
                    arch_formatted = f'-target {arch}-apple-{platform}{self.luzbuild.min_vers}'
                    # compile with swiftc using build flags
                    self.luzbuild.swift_compiler.compile(swift, outfile=out_name+f'{arch}-{self.now}', args=build_flags+[arch_formatted])
            if len(c) != 0:
                # convert paths to strings
                c_strings = []
                for file in c:
                    c_strings.append(str(file))
                out_name = f'{self.dir}/obj/{self.name}/{resolve_path("".join(c_strings)).name}'
                build_flags = ['-fobjc-arc' if self.arc else '',
                               f'-isysroot {self.luzbuild.sdk}', self.luzbuild.warnings, f'-O{self.luzbuild.optimization}', self.luzbuild.archs_formatted, self.include, f'-m{self.luzbuild.platform}-version-min={self.luzbuild.min_vers}', self.luzbuild.c_flags]
                # compile with clang using build flags
                self.luzbuild.c_compiler.compile(c, out_name, build_flags)
            
        except Exception as e:
            print(e)
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
        # compile files
        compile_results = self.__compile_tool_files(self.files)
        if compile_results is not None:
            return compile_results
        # link files
        linker_results = self.__linker()
        if linker_results is not None:
            return linker_results
        # stage deb
        self.__stage()

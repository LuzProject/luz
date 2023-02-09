# module imports
from os import makedirs
from shutil import copytree
from subprocess import check_output
from time import time

# local imports
from ..deps import logos
from ...common.logger import warn
from .module import Module
from ...common.utils import get_hash, resolve_path

import sys, os


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
            makedirs(self.obj_dir, exist_ok=True)
        
        if not self.logos_dir.exists():
            makedirs(self.logos_dir, exist_ok=True)
        
        if not self.dylib_dir.exists():
            makedirs(self.dylib_dir, exist_ok=True)
            
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

        # changed files
        changed = []
        # new hashes
        new_hashes = {}
        # loop files
        for file in files_to_compile:
            # get file hash
            fhash = self.luzbuild.hashlist.get(str(file))
            new_hash = get_hash(file)
            # variables
            lipod_path = resolve_path(f'{self.dir}/obj/{self.name}/*{file.name}.dylib')
            # check if file needs to be compiled
            if (fhash is not None and fhash != new_hash) or (len(lipod_path) == 0):
                changed.append(file)
            # add to new hashes
            new_hashes[str(file)] = new_hash

        # hashes
        self.luzbuild.update_hashlist(new_hashes)

        # files list
        files = changed if self.only_compile_changed else files_to_compile
        
        # handle files not needing compilation
        if len(files) == 0:
            self.log(f'Nothing to compile for module "{self.name}".')
            return []
    
        files = files_to_compile

        # use logos files if necessary
        if filter(lambda x: '.x' in x, files) != []:
            files = logos(self.luzbuild, files)

        # return files
        return files


    def __linker(self):
        """Use a linker on the compiled files."""
        self.log_stdout(f'Linking compiled files to "{self.name}.dylib"...')

        check_output(f'{self.luzbuild.lipo} -create -output {self.dir}/dylib/{self.name}.dylib {self.dir}/obj/{self.name}/*', shell=True)
        
        try:
            # fix rpath
            rpath = '/var/jb/Library/Frameworks/' if self.luzbuild.rootless else '/Library/Frameworks'
            check_output(f'{self.luzbuild.install_name_tool} -add_rpath {rpath} {self.dir}/dylib/{self.name}.dylib', shell=True)
        except:
            return f'An error occured when trying to add rpath to "{self.dir}/dylib/{self.name}.dylib" for module "{self.name}".'
        
        try:
            # run ldid
            check_output(f'{self.luzbuild.ldid} {self.entflag}{self.entfile} {self.dir}/dylib/{self.name}.dylib', shell=True)
        except:
            return f'An error occured when trying to codesign "{self.dir}/dylib/{self.name}.dylib". ({self.name})'
        
        self.remove_log_stdout(f'Linking compiled files to "{self.name}.dylib"...')
        

    def __compile_tweak_files(self, files):
        """Compile a tweak files.
        
        :param str files: The files to compile.
        """
        c = []
        swift = []
        for file in files:
            new_path = ''
            # handle logos files
            if file.get('logos') == True:
                # new path
                new_path = file.get('new_path')
                # set original path
                orig_path = file.get('old_path')
                # include path
                include_path = '/'.join(str(orig_path).split('/')[:-1])
                # add it to include if it's not already there
                if include_path not in self.include:
                    self.include += ' -I' + include_path
            else:
                new_path = file.get('path')
            # handle normal files
            if str(new_path).endswith('.swift'):
                swift.append(new_path)
            else:
                c.append(new_path)

        # compile file
        try:
            if len(swift) != 0:
                # convert paths to strings
                swift_strings = []
                for file in swift:
                    swift_strings.append(str(file))

                # define build flags
                build_flags = [f'-sdk {self.luzbuild.sdk}', self.include, self.library_dirs, self.libraries, self.frameworks, self.private_frameworks,  self.swift_flags, '-emit-library', f'-module-name {self.name}', self.bridging_headers]
                out_name = f'{self.dir}/obj/{self.name}/{resolve_path("".join(swift_strings)).name}'
                # format platform
                platform = 'ios' if self.luzbuild.platform == 'iphoneos' else self.luzbuild.platform
                for arch in self.luzbuild.archs:
                    # arch
                    arch_formatted = f'-target {arch}-apple-{platform}{self.luzbuild.min_vers}'
                    # compile with swiftc using build flags
                    self.luzbuild.swift_compiler.compile(
                        swift, outfile=out_name+f'{arch}-{self.now}.dylib', args=build_flags+[arch_formatted])
            if len(c) != 0:
                # convert paths to strings
                c_strings = []
                for file in c:
                    c_strings.append(str(file))
                out_name = f'{self.dir}/obj/{self.name}/{resolve_path("".join(c_strings)).name}.dylib'
                build_flags = ['-fobjc-arc' if self.arc else '',
                               f'-isysroot {self.luzbuild.sdk}', self.warnings, f'-O{self.optimization}', self.luzbuild.archs_formatted, self.include, self.library_dirs, self.libraries, self.frameworks, self.private_frameworks, f'-m{self.luzbuild.platform}-version-min={self.luzbuild.min_vers}', '-dynamiclib', self.c_flags]
                # compile with clang using build flags
                self.luzbuild.c_compiler.compile(c, out_name, build_flags)

        except:
            return f'An error occured when attempting to compile for module "{self.name}".'
            
            
    def __stage(self):
        """Stage a deb to be packaged."""
        # dirs to make
        if self.install_dir is None:
            dirtomake = resolve_path(
                f'{self.dir}/_/Library/MobileSubstrate/') if not self.luzbuild.rootless else resolve_path(f'{self.dir}/_/var/jb/usr/lib/')
            dirtocopy = resolve_path(f'{self.dir}/_/Library/MobileSubstrate/DynamicLibraries/') if not self.luzbuild.rootless else resolve_path(
                f'{self.dir}/_/var/jb/usr/lib/TweakInject')
        else:
            if self.luzbuild.rootless:
                warn(f'Custom install directory for module "{self.name}" was specified, and rootless is enabled. Prefixing path with /var/jb.')
            self.install_dir = resolve_path(self.install_dir)
            dirtomake = resolve_path(f'{self.dir}/_/{self.install_dir.parent}') if not self.luzbuild.rootless else resolve_path(
                f'{self.dir}/_/var/jb/{self.install_dir.parent}')
            dirtocopy = resolve_path(f'{self.dir}/_/{self.install_dir}') if not self.luzbuild.rootless else resolve_path(
                f'{self.dir}/_/var/jb/{self.install_dir}')
        # make proper dirs
        if not dirtomake.exists():
            makedirs(dirtomake, exist_ok=True)
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
    

    def compile(self):
        """Compile."""
        # compile files
        compile_results = self.__compile_tweak_files(self.files)
        if compile_results is not None:
            return compile_results
        # link files
        linker_results = self.__linker()
        if linker_results is not None:
            return linker_results
        # stage deb
        self.__stage()

# module imports
from os import makedirs
from shutil import copytree
from subprocess import check_output

# local imports
from ..module import ModuleBuilder
from ...common.logger import log, warn
from ...common.utils import resolve_path

class Tool(ModuleBuilder):
    def __init__(self, **kwargs):
        """Build a tool module."""
        # kwargs parsing
        super().__init__(kwargs.get("module"), kwargs.get("luz"))

        # files
        self.files = self.hash_files(self.module.files, "executable")

    def __compile_tool_file(self, file) -> bool:
        """Compile a tool file.

        :param str file: The file to compile.
        """
        # log
        file_formatted = str(file).replace(str(self.luz.path.absolute()), '')
        if file_formatted != str(file):
            file_formatted = "/".join(file_formatted.split("/")[1:])
        log(f'Compiling "{file_formatted}"...', "🔨", self.module.abbreviate(), self.luz.lock)

        # compile file
        try:
            if str(file).endswith(".swift"):
                files_minus_to_compile = list(
                    filter(lambda x: x != file and str(x).endswith(".swift"), self.files))
                futures = [self.pool.submit(self.compile_swift_arch, file, files_minus_to_compile, x) for x in self.meta.archs]
            else:
                futures = [self.pool.submit(self.compile_c_arch, file, x) for x in self.meta.archs]
            self.wait(futures)

        except:
            return f'An error occured when attempting to compile for module "{self.module.name}".'

    def __stage(self):
        """Stage a deb to be packaged."""
        # log
        log(f"Staging...", "📦", self.module.abbreviate(), self.luz.lock)
        # before stage
        if self.module.before_stage: self.module.before_stage()
        # dirs to make
        if self.module.install_dir is None:
            dirtomake = resolve_path(
                f"{self.luz.build_dir}/_/usr") if not self.meta.rootless else resolve_path(f"{self.luz.build_dir}/_/var/jb/usr")
            dirtocopy = resolve_path(
                f"{self.luz.build_dir}/_/usr/bin") if not self.meta.rootless else resolve_path(f"{self.luz.build_dir}/_/var/jb/usr/bin")
        else:
            if self.meta.rootless:
                warn(f'Custom install directory was specified, and rootless is enabled. Prefixing path with /var/jb.', msg=self.module.abbreviate())
            self.install_dir = resolve_path(self.module.install_dir)
            dirtomake = resolve_path(f"{self.luz.build_dir}/_/{self.module.install_dir.parent}") if not self.meta.rootless else resolve_path(
                f"{self.luz.build_dir}/_/var/jb/{self.module.install_dir.parent}")
            dirtocopy = resolve_path(f"{self.luz.build_dir}/_/{self.module.install_dir}") if not self.meta.rootless else resolve_path(
                f"{self.luz.build_dir}/_/var/jb/{self.module.install_dir}")
        # make proper dirs
        if not dirtomake.exists():
            makedirs(dirtomake, exist_ok=True)
        copytree(self.bin_dir, dirtocopy, dirs_exist_ok=True)
        # after stage
        if self.module.after_stage: self.module.after_stage()

    def compile(self):
        """Compile module."""
        for arch in self.meta.archs:
            for x in self.files:
                check_output(f"rm -rf {self.obj_dir}/{arch}/{x.name}-*", shell=True)
            makedirs(f"{self.obj_dir}/{arch}", exist_ok=True)
        # compile files
        futures = [self.luz.pool.submit(self.__compile_tool_file, file) for file in self.files]
        self.wait(futures)
        for result in futures:
            if result.result() is not None:
                return result
        # link files
        linker_results = self.linker("executable")
        if linker_results is not None:
            return linker_results
        # stage deb
        if self.meta.pack:
            self.__stage()
    
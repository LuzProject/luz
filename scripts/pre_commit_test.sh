MY_PATH="$(dirname -- "${BASH_SOURCE[0]}")"            # relative
MY_PATH="$(cd -- "$MY_PATH" && pwd)"    # absolutized and normalized
if [[ -z "$MY_PATH" ]] ; then
  # error; for some reason, the path is not accessible
  # to the script (e.g. permissions re-evaled after suid)
  exit 1  # fail
fi

cd $MY_PATH
bash ./install.sh
cd $MY_PATH/../../TestTweaks

echo -e '\nCOMPILING LOCKSIXTEEN\n-------------'
# build locksixteen
cd locksixteen
luz build -c
echo '-------------'

echo -e 'COMPILING BATTERYASSEMBLY\n-------------'
# build batteryassembly
cd ../BatteryAssembly
luz build -c
echo -e '-------------\n\nDone!'
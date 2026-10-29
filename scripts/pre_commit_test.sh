MY_PATH="$(dirname -- "${BASH_SOURCE[0]}")"            # relative
MY_PATH="$(cd -- "$MY_PATH" && pwd)"    # absolutized and normalized
if [[ -z "$MY_PATH" ]] ; then
  # error; for some reason, the path is not accessible
  # to the script (e.g. permissions re-evaled after suid)
  exit 1  # fail
fi

bash $MY_PATH/install.sh
TWEAKPATH="$MY_PATH/../../TestTweaks"

echo -e '\nCOMPILING LOCKSIXTEEN\n-------------'
# build locksixteen
luz build -c -p $TWEAKPATH/locksixteen
echo '-------------'

echo -e 'COMPILING BATTERYASSEMBLY\n-------------'
# build batteryassembly
luz build -c -p $TWEAKPATH/batteryassembly
echo -e '-------------\n\nDone!'
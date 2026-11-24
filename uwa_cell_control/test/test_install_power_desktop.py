"""Desktop installation writes only an isolated XDG directory, never launches GUI."""
from pathlib import Path
import sys

import pytest
from gi.repository import GLib

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'scripts'))
import install_ur_power_desktop as installer


@pytest.fixture
def installed(tmp_path,monkeypatch):
    data=tmp_path/'xdg'
    monkeypatch.setenv('XDG_DATA_HOME',str(data))
    # Desktop database/validation commands are deployment concerns. The test
    # parses the generated file with GLib but never touches the user's desktop.
    monkeypatch.setattr(installer.shutil,'which',lambda _:None)
    return data


def arguments(entry,group):
    key=GLib.KeyFile()
    key.load_from_file(str(entry),GLib.KeyFileFlags.NONE)
    success,argv=GLib.shell_parse_argv(key.get_string(group,'Exec'))
    assert success
    # %% is the Desktop Entry escape for a literal percent at launch time.
    return [value.replace('%%','%') for value in argv]


@pytest.mark.parametrize('flags,host',[([],False),(['--n100'],True)])
def test_plain_installer_keeps_legacy_exec_and_safety_action(installed,flags,host):
    installer.main(flags)
    entry=installed/'applications/uwa-robot-power.desktop'
    expected=['/usr/bin/python3',str(REPO/'scripts/ur_power_gui.py')]+(['--n100'] if host else [])
    assert arguments(entry,'Desktop Entry')==expected
    assert arguments(entry,'Desktop Action SafetyLog')==expected+['--safety-log']
    assert (installed/'icons/hicolor/scalable/apps/uwa-robot-power.svg').read_bytes()==(REPO/'assets/uwa-robot-power.svg').read_bytes()


@pytest.mark.parametrize('explicit_n100',[False,True])
def test_candidate_binding_is_durable_in_both_actions_with_desktop_escaping(installed,tmp_path,explicit_n100):
    runtime=tmp_path/'candidate with spaces "quoted" back\\slash $cash `literal` 100%'
    flags=(['--n100'] if explicit_n100 else [])+['--minimal-runtime',str(runtime)]
    installer.main(flags)
    entry=installed/'applications/uwa-robot-power.desktop'
    expected=['/usr/bin/env','UWA_PROTECTION_BACKEND=minimal','UWA_MINIMAL_RUNTIME='+str(runtime),
              '/usr/bin/python3',str(REPO/'scripts/ur_power_gui.py'),'--n100','--protection-backend','minimal']
    assert arguments(entry,'Desktop Entry')==expected
    assert arguments(entry,'Desktop Action SafetyLog')==expected+['--safety-log']
    assert '100%%' in entry.read_text()


def test_source_script_path_uses_both_desktop_and_exec_escaping(installed,tmp_path,monkeypatch):
    repository=tmp_path/'source "quotes" back\\slash $cash `literal` 50%'
    (repository/'scripts').mkdir(parents=True)
    (repository/'assets').mkdir()
    (repository/'assets/uwa-robot-power.svg').write_text('<svg/>')
    monkeypatch.setattr(installer,'__file__',str(repository/'scripts/install_ur_power_desktop.py'))
    installer.main(['--n100'])
    entry=installed/'applications/uwa-robot-power.desktop'
    assert arguments(entry,'Desktop Entry')==['/usr/bin/python3',str(repository/'scripts/ur_power_gui.py'),'--n100']


def test_relative_candidate_is_rejected_before_any_desktop_write(installed):
    with pytest.raises(SystemExit) as error:
        installer.main(['--minimal-runtime','relative/candidate'])
    assert error.value.code==2
    assert not installed.exists()

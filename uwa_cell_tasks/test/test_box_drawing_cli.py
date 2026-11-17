import importlib.util
import json
from pathlib import Path
import sys

import pytest

from uwa_cell_tasks.pilot_episode import Episode


def tool():
    path=Path(__file__).resolve().parents[2]/'tools/box_drawing_pilot.py'
    spec=importlib.util.spec_from_file_location('box_pilot_cli',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path):
    run=tmp_path/'run'
    e=Episode.create(run/'episode',backend='kinematic_model',program_sha256='a'*64)
    e.append('phase_start',phase='return_box',source='model',model_time_s=0.)
    e.append('phase_end',phase='return_box',source='model',model_time_s=2.)
    e.append('run_end',phase='end',source='model',model_time_s=2.,details=dict(status='MODEL_SEQUENCE_COMPLETE'))
    return run,e


def test_feedback_file_binds_episode_phase_and_persists_original_text(tmp_path,monkeypatch,capsys):
    run,e=fixture(tmp_path)
    path=tmp_path/'feedback.json'
    text='Am Ende bitte andersherum drehen.'
    path.write_text(json.dumps(dict(episode_sha256=e.manifest['sha256'],phase='return_box',text=text)))
    monkeypatch.setattr(sys,'argv',['box_drawing_pilot.py','feedback',str(run),'--file',str(path)])
    tool().main()
    result=json.loads(capsys.readouterr().out)
    assert result['feedback'][0]['details']['text']==text
    assert result['feedback'][0]['phase']=='return_box'
    monkeypatch.setattr(sys,'argv',['box_drawing_pilot.py','history',str(tmp_path)])
    tool().main()
    history=json.loads(capsys.readouterr().out)
    assert history[0]['feedback']==[dict(phase='return_box',text=text)]


@pytest.mark.parametrize('field,value',[('episode_sha256','b'*64),('phase','not-a-phase')])
def test_wrong_run_or_phase_cannot_pollute_memory(tmp_path,monkeypatch,field,value):
    run,e=fixture(tmp_path)
    data=dict(episode_sha256=e.manifest['sha256'],phase='return_box',text='Feedback')
    data[field]=value
    path=tmp_path/'feedback.json';path.write_text(json.dumps(data))
    monkeypatch.setattr(sys,'argv',['box_drawing_pilot.py','feedback',str(run),'--file',str(path)])
    with pytest.raises(SystemExit):tool().main()
    assert e.summary()['feedback']==[]

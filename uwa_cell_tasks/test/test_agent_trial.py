import importlib.util
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import pytest


def module():
    path=Path(__file__).resolve().parents[2]/'tools/agent_trial.py'
    spec=importlib.util.spec_from_file_location('agent_trial',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def trial(tmp_path):
    t=module().Trial(tmp_path/'trial')
    t.init(tmp_path,'test-only','test fixture')
    return t


def test_outputs_failures_repairs_and_stages_are_preserved(tmp_path):
    t=trial(tmp_path);t.start('plan')
    rc=t.run([sys.executable,'-c','import sys; print("out ä"); print("error",file=sys.stderr);sys.exit(7)'],'bad',tail_chars=0)
    assert rc==7
    rc=t.run([sys.executable,'-c','print("repaired")'],'repair',tail_chars=0)
    assert rc==0
    t.note('decision','Changed candidate; original failure retained.')
    t.end('done')
    result=t.finish('complete','Fixture only, no robot task')
    assert result['declared_status']=='complete' and len(result['failed_commands'])==1
    assert result['stages'][0]['commands']==2 and result['stages'][0]['nonzero_exits']==1
    assert result['stages'][0]['elapsed_s']>=result['stages'][0]['command_active_union_s']
    out=list((t.directory/'commands').glob('bad-*/stdout.txt'))[0]
    assert 'out ä' in out.read_text() and out.with_name('stderr.txt').read_text()=='error\n'
    assert (t.directory/'summary.md').is_file()


def test_timeout_and_launch_failure_have_exitcodes_and_raw_errors(tmp_path):
    t=trial(tmp_path);t.start('verify')
    assert t.run([sys.executable,'-c','import time;time.sleep(5)'],'timeout',timeout=.2,tail_chars=0)==124
    assert t.run(['/this-command-does-not-exist'],'missing',tail_chars=0)==127
    result=t.summary()
    assert {e['status'] for e in result['failed_commands']}=={'timeout','launch_failed'}
    assert all(Path(e['stderr']).read_text() for e in result['failed_commands'])
    t.end('failed');t.finish('failed','Expected fixture errors')


def test_stage_and_trial_boundaries_cannot_hide_active_work(tmp_path):
    t=trial(tmp_path)
    with pytest.raises(ValueError,match='Start a stage'):
        t.run([sys.executable,'-c','print(1)'],'no-stage',tail_chars=0)
    t.start('orient')
    with pytest.raises(ValueError,match='End current'):t.start('adapt')
    with pytest.raises(ValueError,match='End active'):t.finish('complete','Too early')
    t.end('done')
    with pytest.raises(ValueError,match='new stage name'):t.start('orient')
    t.finish('complete','End')
    with pytest.raises(ValueError,match='finished'):t.note('decision','Late change')


def test_parallel_commands_do_not_double_count_and_end_waits(tmp_path):
    t=trial(tmp_path);t.start('plan')
    errors=[]
    def run(label):
        try:t.run([sys.executable,'-c','import time;time.sleep(.3)'],label,tail_chars=0)
        except BaseException as ex:errors.append(ex)
    threads=[threading.Thread(target=run,args=(label,)) for label in ('a','b')]
    for thread in threads:thread.start()
    deadline=time.monotonic()+2.
    while len(t.state()['active_commands'])<2 and time.monotonic()<deadline:time.sleep(.005)
    with pytest.raises(ValueError,match='still running'):t.end('done')
    for thread in threads:thread.join()
    assert not errors
    t.end('done');result=t.finish('complete','Parallel fixture')
    ends=[json.loads(p.read_text()) for p in (t.directory/'commands').glob('*/result.json')]
    summed=sum(p['elapsed_s'] for p in ends)
    stage=result['stages'][0]
    assert stage['command_active_union_s']<summed
    assert stage['other_wall_s']>=0 and stage['commands']==2


def test_argv_is_literal_and_cwd_may_have_spaces(tmp_path):
    t=trial(tmp_path);t.start('adapt')
    cwd=tmp_path/'space folder';cwd.mkdir()
    literal='$(do-not-execute) `nor-this`'
    assert t.run([sys.executable,'-c','import sys,pathlib;print(sys.argv[1]);print(pathlib.Path.cwd())',literal],
                 'literal',cwd=cwd,tail_chars=0)==0
    out=next((t.directory/'commands').glob('*/stdout.txt')).read_text()
    assert literal in out and str(cwd) in out
    t.end('done');t.finish('complete','Fixture')


def test_interval_union_handles_nested_and_touching_commands():
    assert module().union_seconds([(2.,5.),(0.,4.),(8.,10.),(1.,3.),(10.,11.)])==8.
    with pytest.raises(ValueError,match='backwards'):module().union_seconds([(2.,1.)])


@pytest.mark.parametrize('payload',[b'',b'line one\r\nline two\n\x00\xff'])
def test_stdin_file_archives_exact_bytes_and_feeds_child(tmp_path,payload):
    t=trial(tmp_path);t.start('adapt')
    source=tmp_path/'input with spaces.bin';source.write_bytes(payload)
    assert t.run([sys.executable,'-c','import sys;sys.stdout.buffer.write(sys.stdin.buffer.read())'],
                 'stdin',stdin_file=source,tail_chars=0)==0
    folder=next((t.directory/'commands').iterdir())
    assert (folder/'stdout.txt').read_bytes()==(folder/'stdin.bin').read_bytes()==payload
    record=json.loads((folder/'command.json').read_text())['stdin']
    assert record['sha256']==hashlib.sha256(payload).hexdigest()
    assert record['size_bytes']==len(payload) and record['source']==str(source)
    assert Path(record['artifact'])==folder/'stdin.bin'
    t.end('done');t.finish('complete','Byte-preserving stdin fixture')


def test_cli_heredoc_is_captured_and_invalid_input_does_not_start_command(tmp_path):
    t=trial(tmp_path);t.start('adapt')
    with pytest.raises(FileNotFoundError):
        t.run([sys.executable,'-'],'missing-input',stdin_file=tmp_path/'missing',tail_chars=0)
    assert not t.state()['active_commands'] and not list((t.directory/'commands').iterdir())
    logger=Path(__file__).resolve().parents[2]/'tools/agent_trial.py'
    script=b'print("captured script")\n'
    result=subprocess.run([sys.executable,str(logger),'--trial',str(t.directory),'run',
                           '--label','heredoc','--stdin-file','-','--tail-chars','0',
                           '--',sys.executable,'-'],input=script,capture_output=True)
    assert result.returncode==0,result.stderr
    folder=next((t.directory/'commands').iterdir())
    assert (folder/'stdin.bin').read_bytes()==script
    assert (folder/'stdout.txt').read_text()=='captured script\n'
    assert json.loads((folder/'command.json').read_text())['stdin']['source']=='-'
    t.end('done');t.finish('complete','CLI stdin fixture')


def test_cli_termination_records_interruption_and_cleans_owned_command(tmp_path):
    t=trial(tmp_path);t.start('plan')
    logger=Path(__file__).resolve().parents[2]/'tools/agent_trial.py'
    proc=subprocess.Popen([sys.executable,str(logger),'--trial',str(t.directory),'run','--label','interrupt',
                           '--tail-chars','0','--',sys.executable,'-c',
                           'import time;print("started",flush=True);time.sleep(5)'],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    deadline=time.monotonic()+3.
    while time.monotonic()<deadline:
        paths=list((t.directory/'commands').glob('interrupt-*/stdout.txt'))
        if paths and 'started' in paths[0].read_text():break
        time.sleep(.005)
    else:
        proc.kill();proc.wait();pytest.fail('Child did not start')
    os.kill(proc.pid,signal.SIGTERM)
    proc.communicate(timeout=4.)
    assert proc.returncode==130
    s=t.summary()
    assert not s['unfinished_commands'] and s['failed_commands'][0]['status']=='interrupted'
    t.end('failed');t.finish('failed','Intentional interrupted fixture')

#!/usr/bin/env python3
"""Measure an agent trial: stages, commands, raw outputs, failures and notes.

Standard library only. This records development work, not robot telemetry or
private reasoning. Commands run as argv with no implicit shell.
"""
import argparse
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid
from zoneinfo import ZoneInfo


def stamp():
    return dict(monotonic_s=time.monotonic(),
                perth_time=datetime.now(ZoneInfo('Australia/Perth')).isoformat())


def write(path, value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    temporary.replace(path)


def slug(value):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',value):
        raise ValueError('Use 1–64 letters, digits, underscores or hyphens for stage/label')
    return value


def union_seconds(intervals):
    total=0.;right=None
    for start,end in sorted(intervals):
        if end<start:raise ValueError('Clock moved backwards; elapsed time unavailable')
        if right is None or start>=right:total+=end-start
        elif end>right:total+=end-right
        right=end if right is None else max(right,end)
    return total


class Trial:
    def __init__(self, directory):
        self.directory=Path(directory).resolve()

    def state(self):
        return json.loads((self.directory/'state.json').read_text())

    def events(self):
        return [json.loads(line) for line in (self.directory/'events.jsonl').read_text().splitlines()]

    def change(self, kind, details, mutate):
        with (self.directory/'.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            state=self.state()
            if state['finished']:raise ValueError('Trial already finished')
            mutate(state)
            event=dict(index=state['events'],kind=kind,**stamp(),**details)
            with (self.directory/'events.jsonl').open('a') as stream:
                stream.write(json.dumps(event,ensure_ascii=False,allow_nan=False)+'\n')
            state['events']+=1
            write(self.directory/'state.json',state)
        return event

    def init(self,repo,task,agent=None):
        repo=Path(repo).resolve()
        if not repo.is_dir():raise ValueError('Repository directory missing')
        self.directory.mkdir(parents=True,exist_ok=False)
        snapshots={}
        for relative in ('docs/agent_trials/BOX_DRAWING_HANDOFF.md',
                         'docs/agent_trials/PROMPT_AWAY_FACE.md',
                         'docs/agent_trials/TRACE_PROTOCOL.md',
                         'tools/agent_trial.py','tools/box_drawing_pilot.py',
                         'tools/verify_box_drawing_pilot.py',
                         'uwa_cell_tasks/uwa_cell_tasks/box_drawing.py'):
            source=repo/relative
            if source.is_file():
                raw=source.read_bytes();target=self.directory/'context'/relative
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
                snapshots[relative]=hashlib.sha256(raw).hexdigest()
        def git(*args):
            p=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True)
            return dict(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)
        metadata=dict(schema_version=1,repo=str(repo),task=task,agent_reported=agent,
                      started=stamp(),git_head=git('rev-parse','HEAD'),git_status=git('status','--short'),
                      context_sha256=snapshots,python_version=sys.version,
                      scope='development stages and wrapped commands; no automatic chat/non-shell tool capture')
        write(self.directory/'trial.json',metadata)
        write(self.directory/'state.json',dict(events=0,stage=None,active_commands=[],finished=False))
        (self.directory/'events.jsonl').touch(exist_ok=False)
        (self.directory/'commands').mkdir()
        return metadata

    def start(self,stage):
        slug(stage)
        def mutate(state):
            if state['stage'] is not None:raise ValueError('End current stage first')
            if any(e['kind']=='stage_start' and e['stage']==stage for e in self.events()):
                raise ValueError('Use a new stage name for each retry')
            state['stage']=stage
        return self.change('stage_start',dict(stage=stage),mutate)

    def end(self,outcome,note=''):
        stage=self.state()['stage']
        def mutate(state):
            if stage is None or state['stage']!=stage:raise ValueError('No active stage')
            if state['active_commands']:raise ValueError('Commands still running; cannot end stage')
            state['stage']=None
        return self.change('stage_end',dict(stage=stage,outcome=outcome,note=note),mutate)

    def note(self,kind,text,artifacts=()):
        if not text.strip():raise ValueError('Nonempty note required')
        paths=[]
        for path in artifacts:
            p=Path(path).resolve()
            if not p.exists():raise ValueError('Artifact missing: '+str(p))
            paths.append(str(p))
        return self.change('note',dict(stage=self.state()['stage'],note_kind=kind,text=text,artifacts=paths),lambda _:None)

    def run(self,command,label,timeout=900.,cwd=None,tail_chars=2000):
        if not command:raise ValueError('Command argv required after --')
        if not 0<timeout<86400:raise ValueError('Timeout must be in (0,86400) seconds')
        slug(label)
        identifier=label+'-'+uuid.uuid4().hex[:10]
        folder=self.directory/'commands'/identifier
        folder.mkdir()
        stage=self.state()['stage']
        cwd=str(Path(cwd).resolve()) if cwd else json.loads((self.directory/'trial.json').read_text())['repo']
        def begin(state):
            if stage is None or stage!=state['stage']:raise ValueError('Start a stage before running commands')
            state['active_commands'].append(identifier)
        start=self.change('command_start',dict(stage=stage,command_id=identifier,argv=command,cwd=cwd,
                          stdout=str(folder/'stdout.txt'),stderr=str(folder/'stderr.txt')),begin)
        write(folder/'command.json',start)
        print('RUNNING '+identifier+' — '+stage,flush=True)
        proc=None;status='exited';code=127
        with (folder/'stdout.txt').open('wb') as stdout,(folder/'stderr.txt').open('wb') as stderr:
            try:
                proc=subprocess.Popen(command,cwd=cwd,stdout=stdout,stderr=stderr,start_new_session=True)
                code=proc.wait(timeout=timeout)
            except (subprocess.TimeoutExpired,KeyboardInterrupt) as error:
                status='timeout' if isinstance(error,subprocess.TimeoutExpired) else 'interrupted'
                code=124 if status=='timeout' else 130
                if proc is not None:
                    try:os.killpg(proc.pid,signal.SIGTERM)
                    except ProcessLookupError:pass
                    try:proc.wait(timeout=3.)
                    except subprocess.TimeoutExpired:
                        try:os.killpg(proc.pid,signal.SIGKILL)
                        except ProcessLookupError:pass
                        proc.wait()
                stderr.write(('\nLOGGER: '+status+'\n').encode())
            except OSError as error:
                status='launch_failed';stderr.write((str(error)+'\n').encode())
        def done(state):state['active_commands'].remove(identifier)
        end=self.change('command_end',dict(stage=stage,command_id=identifier,exit_code=code,status=status,
                        stdout=str(folder/'stdout.txt'),stderr=str(folder/'stderr.txt')),done)
        result=dict(start=start,end=end,elapsed_s=end['monotonic_s']-start['monotonic_s'])
        write(folder/'result.json',result)
        print(json.dumps(dict(command_id=identifier,exit_code=code,status=status,elapsed_s=result['elapsed_s'],
                              stdout=end['stdout'],stderr=end['stderr']),ensure_ascii=False),flush=True)
        if tail_chars:
            for name in ('stdout','stderr'):
                text=(folder/(name+'.txt')).read_text(errors='replace')
                if text:print(name+' (tail):\n'+text[-tail_chars:])
        self.summary()
        return code

    def finish(self,status,text):
        def mutate(state):
            if state['stage'] is not None or state['active_commands']:
                raise ValueError('End active stage/commands before finishing')
            state['finished']=True
        self.change('trial_end',dict(declared_status=status,summary=text),mutate)
        return self.summary()

    def summary(self):
        with (self.directory/'.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            return self._summary()

    def _summary(self):
        metadata=json.loads((self.directory/'trial.json').read_text());events=self.events()
        starts={e['command_id']:e for e in events if e['kind']=='command_start'}
        ends={e['command_id']:e for e in events if e['kind']=='command_end'}
        terminal=next((e for e in reversed(events) if e['kind']=='trial_end'),None)
        finish_time=terminal['monotonic_s'] if terminal else time.monotonic()
        stages=[]
        for start in (e for e in events if e['kind']=='stage_start'):
            end=next((e for e in events if e['kind']=='stage_end' and e['stage']==start['stage']),None)
            until=end['monotonic_s'] if end else finish_time
            elapsed=until-start['monotonic_s']
            if elapsed<0:raise ValueError('Monotonic clock reset; cannot report elapsed time')
            commands=[e for e in starts.values() if e['stage']==start['stage']]
            intervals=[(e['monotonic_s'],ends[e['command_id']]['monotonic_s'] if e['command_id'] in ends else until) for e in commands]
            busy=union_seconds(intervals)
            stages.append(dict(stage=start['stage'],elapsed_s=elapsed,command_active_union_s=busy,
                               other_wall_s=max(0.,elapsed-busy),commands=len(commands),
                               nonzero_exits=sum(ends[e['command_id']]['exit_code']!=0 for e in commands if e['command_id'] in ends),
                               outcome=end['outcome'] if end else 'OPEN'))
        result=dict(schema_version=1,task=metadata['task'],agent_reported=metadata['agent_reported'],
                    elapsed_s=finish_time-metadata['started']['monotonic_s'],
                    declared_status=terminal['declared_status'] if terminal else 'OPEN',stages=stages,
                    failed_commands=[e for e in ends.values() if e['exit_code']!=0],
                    unfinished_commands=[e for k,e in starts.items() if k not in ends],
                    notes=[e for e in events if e['kind']=='note'],
                    timing_note='Other wall time includes reading/editing/chat/waiting; not measured model thinking. Tokens unknown unless externally provided.')
        result['outside_stages_s']=max(0.,result['elapsed_s']-sum(s['elapsed_s'] for s in stages))
        write(self.directory/'summary.json',result)
        lines=['# Agententest: '+metadata['task'],'',
               'Deklarierter Abschluss: '+result['declared_status'],
               f"Gesamte gemessene Wandzeit: {result['elapsed_s']:.3f} s",'',
               '| Schritt | Wandzeit s | Tool aktiv s¹ | Restzeit s² | Aufrufe | Fehler | Ergebnis |',
               '|---|---:|---:|---:|---:|---:|---|']
        for s in stages:
            lines.append(f"| {s['stage']} | {s['elapsed_s']:.3f} | {s['command_active_union_s']:.3f} | {s['other_wall_s']:.3f} | {s['commands']} | {s['nonzero_exits']} | {s['outcome']} |")
        lines+=['','¹ Vereinigung der Befehlsintervalle; parallele Befehle werden nicht doppelt gezählt.',
                '² Lesen, Änderungen, Chat und Warten; keine gemessene interne Denkzeit.',
                f"Wandzeit außerhalb benannter Stufen: {result['outside_stages_s']:.3f} s. Zeit vor init ist nicht erfasst.",
                'Agentenstatus ist eine Angabe, kein automatischer Nachweis eines gültigen Roboterprogramms.',
                '',f"Fehlgeschlagene Befehle: {len(result['failed_commands'])}; offene Befehle: {len(result['unfinished_commands'])}.",
                'Vollständige argv/Exitcodes/Zeiten: events.jsonl; Rohtexte: commands/*/{stdout,stderr}.txt.',
                'Nicht über diesen Logger ausgeführte Tools/Chat müssen separat notiert/exportiert werden.']
        (self.directory/'summary.md').write_text('\n'.join(lines)+'\n')
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial',type=Path,required=True)
    sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('init');p.add_argument('--repo',type=Path,required=True);p.add_argument('--task',required=True);p.add_argument('--agent')
    p=sub.add_parser('start');p.add_argument('stage')
    p=sub.add_parser('end');p.add_argument('--outcome',choices=('done','failed','blocked'),default='done');p.add_argument('--note',default='')
    p=sub.add_parser('run');p.add_argument('--label',required=True);p.add_argument('--cwd',type=Path);p.add_argument('--timeout',type=float,default=900.);p.add_argument('--tail-chars',type=int,default=2000);p.add_argument('command',nargs=argparse.REMAINDER)
    p=sub.add_parser('note');p.add_argument('--kind',choices=('decision','edit','error','artifact','wait','external_tool','usage'),required=True);p.add_argument('--text',required=True);p.add_argument('--artifact',type=Path,action='append',default=[])
    p=sub.add_parser('finish');p.add_argument('--status',choices=('complete','failed','blocked'),required=True);p.add_argument('--summary',required=True)
    sub.add_parser('summary')
    args=parser.parse_args();trial=Trial(args.trial)
    try:
        if args.action=='init':value=trial.init(args.repo,args.task,args.agent)
        elif args.action=='start':value=trial.start(args.stage)
        elif args.action=='end':value=trial.end(args.outcome,args.note)
        elif args.action=='note':value=trial.note(args.kind,args.text,args.artifact)
        elif args.action=='finish':value=trial.finish(args.status,args.summary)
        elif args.action=='summary':value=trial.summary()
        else:
            command=args.command[1:] if args.command[:1]==['--'] else args.command
            def terminate(signum,frame):
                raise KeyboardInterrupt('Logger termination requested')
            signal.signal(signal.SIGTERM,terminate)
            return trial.run(command,args.label,args.timeout,args.cwd,max(0,args.tail_chars))
        print(json.dumps(value,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError) as error:
        parser.exit(2,'agent_trial: '+str(error)+'\n')


if __name__=='__main__':sys.exit(main())

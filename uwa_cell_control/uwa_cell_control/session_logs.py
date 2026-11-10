"""Local, bounded snapshots of a GUI session and its related ROS logs."""
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import platform
import re
import tarfile
import tempfile
import time
import uuid


def active_ros_logs(root,namespace):
    """Include older logs still used by an attached driver, without reading its data."""
    found=set();root=Path(root).resolve()
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:
            command=(entry/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
            if namespace not in command:continue
            for fd in (entry/'fd').iterdir():
                try:
                    file=fd.resolve(strict=True)
                    if file.is_relative_to(root) and file.is_file():found.add(file)
                except (OSError,RuntimeError):continue
        except (OSError,PermissionError):continue
    return found


class SessionLogs:
    def __init__(self,workspace,*,ros_root=None,namespace='/uwa_hardware'):
        self.root=Path(workspace)/'setup/logs/uwa-control'
        self.started=time.time();self.namespace=namespace
        self.id=datetime.now().strftime('%Y%m%d_%H%M%S')+f'_{os.getpid()}_'+uuid.uuid4().hex[:8]
        self.directory=self.root/'sessions'/self.id
        self.directory.mkdir(parents=True,exist_ok=False)
        self.gui_log=self.directory/'gui.log';self.gui_log.touch()
        self.ros_root=Path(ros_root or os.environ.get('ROS_LOG_DIR',self.root/'ros')).resolve()
        self.inherited=active_ros_logs(self.ros_root,namespace)
        self.process_count=0

    def note(self,line):
        with self.gui_log.open('a',encoding='utf-8') as stream:stream.write(line+'\n')

    def process_log(self,tag,args):
        self.process_count+=1
        tag=re.sub(r'[^a-zA-Z0-9_-]','_',tag)
        file=self.directory/'processes'/f'{self.process_count:04d}-{tag}.log'
        file.parent.mkdir(exist_ok=True)
        file.write_text('Command: '+json.dumps(args)+'\n',encoding='utf-8')
        return file

    def export(self,metadata):
        """No network/upload. Copy only the file sizes observed at snapshot time."""
        export_root=self.root/'exports';export_root.mkdir(parents=True,exist_ok=True)
        destination=export_root/f'{self.id}_{time.time_ns()}.tar.gz'
        temporary=destination.with_suffix('.partial')
        warnings=[];included=[]
        sources={}
        for file in self.directory.rglob('*'):
            if file.is_file() and not file.is_symlink():
                sources['session/'+str(file.relative_to(self.directory))]=file
        inherited=self.inherited|active_ros_logs(self.ros_root,self.namespace)
        if self.ros_root.is_dir():
            for file in self.ros_root.rglob('*'):
                try:
                    if file.is_symlink() or not file.is_file():continue
                    stat=file.stat()
                    if stat.st_size and (stat.st_mtime>=self.started or file.resolve() in inherited):
                        sources['ros/'+str(file.relative_to(self.ros_root))]=file
                except OSError as error:warnings.append(str(error))
        # Compatibility context for drivers started by the pre-session GUI.
        # Deliberately labelled as inherited history, not this window's own log.
        legacy=self.root/'gui.log'
        if legacy.is_file() and not legacy.is_symlink():
            sources['inherited_context/legacy_gui.log']=legacy
        manifest={'session_id':self.id,'session_started':datetime.fromtimestamp(
            self.started,timezone.utc).isoformat(),'exported_at':datetime.now(timezone.utc).isoformat(),
            'python':platform.python_version(),'platform':platform.platform(),
            'ros':{key:os.environ.get(key) for key in ['ROS_DISTRO','ROS_DOMAIN_ID','ROS_AUTOMATIC_DISCOVERY_RANGE']},
            'ros_log_root':str(self.ros_root),'snapshot':metadata,
            'notes':['Files are copied up to their observed size; running logs may continue afterwards.',
                     'inherited_context contains pre-session GUI history for already-running drivers.',
                     'No commands are sent to robots by this export.'],
            'files':included,'warnings':warnings}
        try:
            with tarfile.open(temporary,'w:gz') as archive:
                for name,file in sorted(sources.items()):
                    try:
                        # Opening first keeps renamed/rotated logs consistent.
                        with file.open('rb') as stream:
                            stat=os.fstat(stream.fileno())
                            with tempfile.TemporaryFile() as snapshot:
                                remaining=stat.st_size
                                while remaining:
                                    chunk=stream.read(min(1024*1024,remaining))
                                    if not chunk:break
                                    snapshot.write(chunk);remaining-=len(chunk)
                                size=snapshot.tell();snapshot.seek(0)
                                info=tarfile.TarInfo(name);info.size=size;info.mtime=stat.st_mtime
                                archive.addfile(info,snapshot)
                                included.append({'archive_path':name,'source':str(file),'bytes':size})
                                if remaining:warnings.append(f'{file}: truncated during export')
                    except OSError as error:warnings.append(f'{file}: {error}')
                data=json.dumps(manifest,indent=2,ensure_ascii=False).encode()
                info=tarfile.TarInfo('manifest.json');info.size=len(data)
                archive.addfile(info,io.BytesIO(data))
            temporary.replace(destination)
            # Only completed archives become the latest diagnostic target.
            pointer=self.root/'latest-export.txt'
            pointer_tmp=pointer.with_name('latest-export-'+uuid.uuid4().hex+'.tmp')
            pointer_tmp.write_text(str(destination)+'\n',encoding='utf-8');pointer_tmp.replace(pointer)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return destination

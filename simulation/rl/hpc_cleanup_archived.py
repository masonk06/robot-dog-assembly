"""Remove byte-verified W&B artifact copies from completed HPC run folders only.

Default is a size report. --apply deletes only files matched to committed W&B
artifacts from that same run. Environments, inputs, logs, and the latest run stay.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import time

PROJECT = 'marsdenm-oregon-state-university/robot-dog-rl'
HOST = 'https://api.forge.coreweave.com'
RUN_NAME = re.compile(r'^\d{8}-\d{6}-([a-z0-9]{8})$')


def file_digest(path):
    h = hashlib.md5()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return base64.b64encode(h.digest()).decode()


def contained_regular_file(path, run_folder):
    """Reject symlinked files or directories, including links within the tree."""
    try:
        relative = path.relative_to(run_folder)
        current = run_folder
        if current.is_symlink():
            return False
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                return False
        path.resolve().relative_to(run_folder.resolve())
        return path.is_file()
    except (ValueError, OSError):
        return False


def backup_matches(relative, size, digest, entries):
    # Only exact checkpoint-relative or source-relative paths are eligible.
    for entry in entries:
        name = entry['path']
        if relative == name and size == entry['size'] and digest == entry['digest']:
            return True
    return False


def active_trainers():
    found = []
    proc = Path('/proc')
    if not proc.is_dir():
        raise RuntimeError('Run this tool in the Linux HPC terminal')
    for item in proc.iterdir():
        if not item.name.isdigit() or int(item.name) == os.getpid():
            continue
        try:
            if item.stat().st_uid != os.getuid():
                continue
            words = (item / 'cmdline').read_bytes().split(b'\0')
            scripts = {Path(w.decode(errors='replace')).name for w in words}
            if scripts & {'train.py', 'train_cuda.py', 'overnight_cuda.py', 'wandb'}:
                found.append(item.name)
        except (OSError, ProcessLookupError):
            pass
    return found


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path.home() / 'robot-dog-newton')
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    if active_trainers():
        p.error('A training or W&B process is active. Finish it before cleaning completed runs.')
    root = args.root.expanduser().resolve(strict=True)
    runs = root / 'runs'
    if runs.is_symlink() or not runs.is_dir():
        p.error('Expected a real runs directory under the specified project')
    candidates = []
    for category in runs.iterdir():
        if category.is_symlink() or not category.is_dir():
            continue
        for folder in category.iterdir():
            match = RUN_NAME.fullmatch(folder.name)
            if folder.is_dir() and not folder.is_symlink() and match:
                candidates.append((folder, match.group(1)))
    if not candidates:
        print('No recognized run folders. No files removed.')
        return
    newest = max(folder.name for folder, _ in candidates)
    import wandb
    api = wandb.Api(overrides={'base_url': HOST}, timeout=30)
    report = {'mode': 'delete_verified_copies' if args.apply else 'report_only',
              'root': str(root), 'keep_newest': newest, 'runs': [], 'bytes': 0}
    audit = root / ('cleanup-' + time.strftime('%Y%m%d-%H%M%S') + '.json')
    def save_report():
        audit.write_text(json.dumps(report, indent=2))
    save_report()  # Fail before deleting anything if the report cannot be saved.
    for folder, run_id in sorted(candidates):
        row = {'path': str(folder), 'run': run_id, 'files': [], 'kept_files': 0, 'bytes': 0}
        report['runs'].append(row)
        if folder.name == newest:
            row['skip'] = 'newest run retained for continuation'
            continue
        try:
            run = api.run(PROJECT + '/' + run_id)
            if run.state not in ('finished', 'crashed', 'failed', 'killed'):
                row['skip'] = 'run is not completed: ' + run.state
                continue
            archived = {'model': [], 'dataset': []}
            for artifact in run.logged_artifacts():
                if artifact.type not in archived or artifact.state != 'COMMITTED':
                    continue
                for name, entry in artifact.manifest.entries.items():
                    if entry.ref or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts:
                        continue
                    archived[artifact.type].append(dict(path=name, size=entry.size,
                                                       digest=entry.digest, artifact=artifact.name))
            for subdir in folder.iterdir():
                if subdir.is_symlink() or not subdir.is_dir():
                    continue
                kind = 'dataset' if subdir.name == 'source' else 'model'
                for file in subdir.rglob('*'):
                    if not contained_regular_file(file, folder):
                        continue
                    size = file.stat().st_size
                    relative = file.relative_to(subdir).as_posix()
                    digest = file_digest(file)
                    if not backup_matches(relative, size, digest, archived[kind]):
                        row['kept_files'] += 1
                        continue
                    row['files'].append(str(file.relative_to(root)))
                    row['bytes'] += size
                    if args.apply:
                        # Recheck scope and contents immediately before each deletion.
                        if not contained_regular_file(file, folder) or file_digest(file) != digest:
                            raise RuntimeError('File changed during cleanup: ' + str(file))
                        file.unlink()
                        report['bytes'] += size
                        save_report()
            if not args.apply:
                report['bytes'] += row['bytes']
            row['status'] = 'removed verified copies' if args.apply else 'verified removable copies'
            print(f'{folder}: {row["bytes"] / 1024**2:.1f} MiB; {row["kept_files"]} unmatched files retained', flush=True)
        except Exception as error:
            row['skip'] = str(error)
            print(f'Keeping unverified files in {folder}: {error}', flush=True)
        finally:
            save_report()
    save_report()
    print(f'{"Freed" if args.apply else "Can free"}: {report["bytes"] / 1024**3:.3f} GiB')
    print('Audit report: ' + str(audit))
    print('Kept: latest run, project inputs/source, Python environments, W&B logs, unmatched files.')


if __name__ == '__main__':
    main()

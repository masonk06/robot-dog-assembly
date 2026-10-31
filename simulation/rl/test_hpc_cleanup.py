from hpc_cleanup_archived import backup_matches, contained_regular_file, file_digest


def test_requires_exact_archived_path_size_and_content(tmp_path):
    f = tmp_path / 'policy.zip'
    f.write_bytes(b'weights')
    entries = [dict(path='policy.zip', size=7, digest=file_digest(f))]
    assert backup_matches('policy.zip', 7, file_digest(f), entries)
    assert not backup_matches('normalize.pkl', 7, file_digest(f), entries)
    assert not backup_matches('policy.zip', 8, file_digest(f), entries)
    f.write_bytes(b'changed')
    assert not backup_matches('policy.zip', 7, file_digest(f), entries)


def test_scope_excludes_files_outside_run(tmp_path):
    run = tmp_path / 'run'
    run.mkdir()
    inside = run / 'policy.zip'
    inside.write_text('saved')
    outside = tmp_path / 'other.txt'
    outside.write_text('keep')
    assert contained_regular_file(inside, run)
    assert not contained_regular_file(outside, run)


def test_apply_removes_only_archived_bytes_and_keeps_latest(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace as S
    import hpc_cleanup_archived as cleanup
    root = tmp_path / 'project'
    old = root / 'runs' / 'cuda' / '20261026-120000-abcdefgh'
    latest = root / 'runs' / 'cuda' / '20261027-120000-ijklmnop'
    for run in (old, latest):
        (run / 'final').mkdir(parents=True)
        (run / 'final' / 'policy.zip').write_bytes(b'weights')
        (run / 'final' / 'normalize.pkl').write_bytes(b'unbacked normalization')
    (root / 'source').mkdir()
    (root / 'source' / 'model.xml').write_text('keep')
    digest = file_digest(old / 'final' / 'policy.zip')
    artifact = S(type='model', state='COMMITTED', name='model:v0',
                 manifest=S(entries={'policy.zip': S(size=7, digest=digest, ref=None)}))
    run = S(state='finished', logged_artifacts=lambda: [artifact])
    api = S(run=lambda name: run)
    monkeypatch.setitem(sys.modules, 'wandb', S(Api=lambda **kwargs: api))
    monkeypatch.setattr(cleanup, 'active_trainers', lambda: [])
    monkeypatch.setattr(sys, 'argv', ['cleanup', '--root', str(root), '--apply'])
    cleanup.main()
    assert not (old / 'final' / 'policy.zip').exists()
    assert (old / 'final' / 'normalize.pkl').exists()
    assert (latest / 'final' / 'policy.zip').exists()
    assert (root / 'source' / 'model.xml').exists()

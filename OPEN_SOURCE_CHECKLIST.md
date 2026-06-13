# Open Source Checklist

- [ ] Choose and add a repository license before announcing the project as open source.
- [ ] Confirm the sample audio files in `examples/` are safe to publish.
- [ ] Confirm the bundled text-normalization code and `.fst` assets under `backend/tn/` can be redistributed with this project.
- [ ] Run `python -m compileall -q .` in a clean environment.
- [ ] Run a secret scan before every public push.
- [ ] Verify that `models/`, `data/`, `results/`, `temp/`, `logs/`, virtual environments, and `.env` files are still ignored.

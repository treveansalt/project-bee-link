# Local model development workflow

This app is also staged at `~/CodingJobs/bee-link-app` on the M2 Mac. OpenCode uses LM Studio locally, via the `lmstudio/kali-agent-llm` model. No cloud model was used for the Mac jobs.

Give it small, bounded tasks and explicit checks. Its 8K context and 2K response budget suit a single function or concise review better than a whole feature. The October 12 capture overview draft required reviewer corrections; treating the model's response as evidence of correctness would have missed defects.

From a Mac terminal:

```sh
cd ~/CodingJobs/bee-link-app
OPENCODE_DISABLE_MODELS_FETCH=1 ~/.opencode/bin/opencode
```

A development bridge can stage a prepared source folder over SSH and retrieve results and tool logs. Avoid copying credentials, real bike logs or unrelated files into model jobs. Review changed files and the actual test output before merging. The Mac's app copy is for development, and no persistent public server was started.

Validation command:

```sh
python3 -m unittest discover -s tests -v
```

Use `tools/build_preview.py` to regenerate the offline HTML after changing browser assets. Keep synthetic demo data separate from real receiver records. No bike control or CAN transmission feature exists.

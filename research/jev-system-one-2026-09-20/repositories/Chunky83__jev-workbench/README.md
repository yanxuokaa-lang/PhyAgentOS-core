# Jev Workbench

![This is Jev Workbench. The Jev character stumbles in, catches his balance, makes a full turn, and winks as a mint star appears.](docs/assets/jev-welcome.gif)

[View the still welcome image](docs/assets/jev-welcome.png)

A desktop workspace for evidence, diagnostic checks, and explicitly approved assistant proposals.

Jev Workbench is an independent hobby project by Dennis Hernandez. It is not
an official Jev project and is not affiliated with or endorsed by Jev's
developers or service operators.

**Mac users:** start with [the Mac quickstart](docs/mac-quickstart.md). Build Apple Silicon packages from Actions → Build macOS packages → Run workflow. Builds are manual-only; pushes, merges, and version changes do not start them.

The current baseline is **0.1.0**: a C++ desktop workspace with a Python engine, a Claude connector, an automatic proposal inbox, explicit approval, and shared results. On Windows, launch the current package with `--local-preview`. See [the workspace map](WORKSPACE.md) for the current package and folders.

The [four-world test kit](test-kits/four-worlds/README.md) has its own folder. Its offline story fixtures are ready for terminal testing; they are not yet wired into the desktop connector.

Read [the desktop guide](docs/desktop.md) for exact first-use steps, file locations, limitations, and build instructions. Keep the portable package together; Python and Qt are bundled. The original diagnostic CLI remains available below.

Version **0.1.0** is read from `VERSION.txt`. The repository starts from one current-version baseline. See [release and macOS build instructions](docs/releases.md). Current Windows checks pass; a current Mac package still needs a manual build and device validation.

## Original diagnostic CLI workflow

1. Use `prompts/collect_evidence.md` with a coding agent to collect verified evidence.
2. Save the resulting JSON file.
3. Preview the exact request without calling TypeSafe:

```powershell
python -m jev_diagnostics.main --evidence examples/demo_timeout.json --preview
```

4. Set `TYPESAFE_API_KEY` in the current terminal.
5. Send one request:

```powershell
python -m jev_diagnostics.main --evidence examples/demo_timeout.json --send
```

The original CLI consumes evidence you supply. The desktop connector separately records operation metadata and runs only an explicitly approved, named synthetic fixture. It does not execute arbitrary assistant-selected commands or apply repairs.

## Development

```powershell
python -m pip install -e .
python -m unittest discover -s tests
```

This checkout uses the versioned hooks in `.githooks` to reject the generic GitHub
no-reply identity and unfinished `YOUR_ID` placeholders before a commit or push.
After a fresh clone, enable the same checks once with:

```powershell
git config core.hooksPath .githooks
```

Set `user.email` to the private no-reply address shown in GitHub Settings → Emails.

The core evaluation client uses the Python standard library. Connector development also needs `python -m pip install -r requirements-connectors.txt`. TypeSafe evaluations use its documented HTTP endpoint.

## Key handling

Copy `.env.example` only as a reference. Do not store a real key in the repository. The program reads `TYPESAFE_API_KEY` from the process environment through `api_key.py`.

## License

Jev Workbench is available under the [MIT License](LICENSE). Copyright © 2026 Dennis Hernandez.

## Security

Report suspected vulnerabilities privately by following the [security policy](.github/SECURITY.md). Do not disclose them in public issues or pull requests.

## Contributing

Bug reports, feature ideas, and pull requests are welcome under the repository's [open-but-controlled contribution policy](CONTRIBUTING.md). Only the maintainer can merge changes.

# io.github.GoldenGnu.jEveAssets

Asset manager for EVE Online.

[https://github.com/GoldenGnu/jEveAssets](https://github.com/GoldenGnu/jEveAssets)

## How to install jEveAssets

```bash
flatpak install --user flathub io.github.GoldenGnu.jEveAssets
```

## How to run jEveAssets

```bash
flatpak run io.github.GoldenGnu.jEveAssets
```

## How to uninstall jEveAssets

```bash
flatpak uninstall --user io.github.GoldenGnu.jEveAssets
```

## Migrating existing jEveAsset data

If you have an existing installation of jEveAssets on your system you can migrate to the Flatpak application with the
following command:

```bash
rsync --delete -Pacv ~/.jeveassets/ ~/.var/app/io.github.GoldenGnu.jEveAssets/.jeveassets/
```

## Importing and exporting data

This flatpak application has no home directory access unless additional permissions are given with a tool such
as [Flatseal](https://flathub.org/apps/com.github.tchx84.Flatseal).

The directory at `~/.var/app/io.github.GoldenGnu.jEveAssets/jEveAssets_mnt/` on the host is mapped
to `~/.jEveAssets_mnt/` inside the Flatpak application.
Use this folder for importing/exporting filters and exporting data.

## Where is my jEveAssets data stored?

`~/.var/app/io.github.GoldenGnu.jEveAssets/.jeveassets/`
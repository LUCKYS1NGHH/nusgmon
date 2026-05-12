# Nusgmon - Network Usage Monitor
Lightweight Python CLI (command-line interface) network usage monitor for Linux.
Designed to run as a `systemd` service.

[![Version 1.6.0](https://img.shields.io/badge/nusgmon-1.6.0-green.svg)](https://github.com/LUCKYS1NGHH/nusgmon)
[![GitHub Stars](https://img.shields.io/github/stars/LUCKYS1NGHH/nusgmon?style=social)](https://github.com/LUCKYS1NGHH/nusgmon/stargazers)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

![Screenshot](screenshot.png)

## Usage examples

Start recording network usage:

`nusgmon record`

View today's usage:

`nusgmon --today`

View current week's usage in JSON format:

`nusgmon --thisweek --json`

View usage after certain date:

`nusgmon --since 2026-03-15`

Prune records before 30 days:

`nusgmon db --prune 30`

## Features

- Lightweight network usage monitor

- Stores usage history in SQLite

- Daily / weekly / monthly statistics

- Graph style options for statistics

- JSON output for scripting

- Works with systemd


## Dependencies
Requires Python 3 and psutil library.

```
pip install psutil # or install `python-psutil` as system-wide through your package manager
```

## Installation

#### For Arch Linux (AUR)
```bash
yay -S nusgmon-git
```

#### For any other distro

The setup script installs the `nusgmon` program and performs the required
file copy, permission, PATH variable etc. setup.

> [!NOTE]
> Run the script as root to install system-wide.
> To install only for your user, just remove sudo from the command `sudo ./setup.sh`.

```bash
git clone https://github.com/LUCKYS1NGHH/nusgmon.git
cd nusgmon
chmod +x setup.sh
sudo ./setup.sh
```

<details>
<summary> Uninstall </summary>

#### If Arch Linux
```bash
yay -R nusgmon-git
```


> Optional (removes the database):
> `rm -rf ~/.nusgmon`

#### If installed system-wide

```bash
sudo systemctl disable --now nusgmon
sudo rm /etc/systemd/system/nusgmon.service
sudo rm /usr/local/bin/nusgmon
sudo systemctl daemon-reload
```

#### If installed as normal user

```bash
systemctl --user disable --now nusgmon
rm ~/.config/systemd/user/nusgmon.service
rm ~/.local/bin/nusgmon
systemctl --user daemon-reload
```

</details>


## Wanna Contribute? 🤝

- Fork this repository to your own GitHub account.
- Create a branch for your changes:

```
git checkout -b feature/your-feature
```

- Write and test your changes (add tests if possible).
- Submit a pull request with a clear description of what you changed and why.

## Author
LUCKYS1NGHH

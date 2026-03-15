#!/usr/bin/env bash

read -p "Enter record interval (recommend -> 3): " _interval
interval="${_interval:-3}"


if [ "$EUID" -eq 0 ]; then
    echo "Setting up nusgmon system-wide.."
    cp nusgmon /usr/bin/nusgmon
    cp nusgmon.service /usr/lib/systemd/system/nusgmon.service

    chmod 755 /usr/bin/nusgmon
    chmod 644 /usr/lib/systemd/system/nusgmon.service

    sed -i "s|^ExecStart=.*|ExecStart=/usr/bin/nusgmon record -w $interval|" /usr/lib/systemd/system/nusgmon.service

    systemctl daemon-reload
    systemctl enable --now nusgmon

else
    echo "Setting up nusgmon only for this user.."
    mkdir -p "$HOME/.local/bin"
    mkdir -p "$HOME/.config/systemd/user"

    cp nusgmon "$HOME/.local/bin/nusgmon"
    cp nusgmon.service "$HOME/.config/systemd/user/nusgmon.service"

    chmod 755 "$HOME/.local/bin/nusgmon"
    chmod 644 "$HOME/.config/systemd/user/nusgmon.service"

    sed -i "s|^ExecStart=.*|ExecStart=$HOME/.local/bin/nusgmon record -w $interval|" "$HOME/.config/systemd/user/nusgmon.service"

    systemctl --user daemon-reload
    systemctl --user enable --now nusgmon


fi

echo "Done!"

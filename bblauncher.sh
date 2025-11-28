#!/bin/bash

# Launching service which calls password reset script once
if [ ! -f /home/bbuser/.firstboot_done ]; then
    systemctl --user daemon-reload
    systemctl --user enable bbpasswordsv9.service
    systemctl --user start bbpasswordsv9.service
    touch /home/bbuser/.firstboot_done
fi

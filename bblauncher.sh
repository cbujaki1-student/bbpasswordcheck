#!/bin/bash

# Launching service which calls password reset script once
if [ ! -f /home/bbuser/.firstboot_done ]; then
    systemctl --user daemon-reload
    systemctl --user enable bbpasswordsv10.service
    systemctl --user start bbpasswordsv10.service
    touch /home/bbuser/.firstboot_done
fi


# TorO2

## Installation
`sudo ./install.sh`


## Running
_Now TorO2 is running in 'live' mode, no daemon mode for now_

`toro2` or `toro2 help` provides _Help_ menu
```
Usage: toro2 start | stop | switch | install | uninstall | naked | isnaked | status | integrate | installnobackup
        start                Start toro2 app (required to have it INSTALLed first)
        stop                 Stop toro2 app (stop services & tor)
        switch               Switch tor identity
        install              Install toro2 app & files
        uninstall            Uinstall toro2 app & files
        status               Get state of tor & services
        naked                Disables TorO2 protection until next start
        isnaked              Checks TorO2 protection disabled
        integrate            Integrate toro2 installation with OS
        installnobackup      Same as INSTALL, with no backup system files
```

**Start** toro2 from terminal with _python3_ available

`toro2 start`

**Stop** with `Ctrl+C` or `toro2 stop` from another terminal

Switch with `toro2 switch` from another terminal

If you need an *direct connection with no TorO2 protection*, do

`toro2 naked`

and all protection settings will be disabled.
But don't worry - it will be restored immediately after you started TorO2 again.

No Tor bridges used by default, but you can add them to toro2.torrc file

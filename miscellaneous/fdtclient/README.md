Instruction:

1. Install fdt at the storage server (http://monalisa.cern.ch/FDT/download.html)
2. Start the fdt server (java -jar fdt.jar)
3. Start this fdt client

Start fdtclient at a host with ip and port:

```
# ./fdtclient HOSTIP HOSTPORT
```

The uri for pyro4 should be "PYRO:FCM@" + HOSTIP + ":" + HOSTPORT

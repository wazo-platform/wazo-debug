# wazo-debug

## wazo-debug collect

`wazo-debug collect` gathers log files and other information about the system,
for use in problem analysis.

Gathered info include:

- log files
- Asterisk log files
- configuration files
- Engine version

### Usage

```
Usage: wazo-debug collect -o OUTPUT_FILE.tar.gz
```

Example:

```
wazo-debug collect -o /tmp/wazo-2017-12-01.tar.gz
```

### Compression

The compression format is determined by the extension of the given file name, e.g.:

- `file.tar.gz` will be compressed with `gzip`
- `file.tar.xz` will be compressed with `xz`

## wazo-debug capture

`wazo-debug capture` captures events and logs happening on a server while the
process is running.

Captured events include:

- Wazo Platform logs
- Asterisk logs
  - including AGI logs
- SIP and RTP packets
  - sngrep only captures entire SIP dialogs, not partial dialogs, i.e. it can't
    log packets for calls that have started before sngrep started capturing

### Usage

```
wazo-debug capture
```

The capture will start automatically. To stop the capture, hit CTRL-C. The
capture file will be printed on the console.


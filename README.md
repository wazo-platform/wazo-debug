# wazo-debug

## wazo-debug-collect

`wazo-debug-collect` gathers log files and other information about the system,
for use in problem analysis.

Gathered info include:

- log files

### Usage

```
Usage: wazo-debug-collect -o OUTPUT_FILE.tar.gz
```

Example:

```
wazo-debug-collect -o /tmp/wazo-2017-12-01.tar.gz
```

### Compression

The compression format is determined by the extension of the given file name, e.g.:

- `file.tar.gz` will be compressed with `gzip`
- `file.tar.xz` will be compressed with `xz`

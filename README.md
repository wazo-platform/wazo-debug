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
  - wazo-auth in debug mode
  - wazo-calld in debug mode
  - wazo-call-logd in debug mode
  - wazo-webhookd in debug mode
- Asterisk logs
  - including AGI logs
- SIP and RTP packets
  - sngrep only captures entire SIP dialogs, not partial dialogs, i.e. it can't
    log packets for calls that have started before sngrep started capturing
- STUN packets
- DNS packets

### Usage

```
wazo-debug capture
```

The capture will start automatically. To stop the capture, hit CTRL-C. The
capture file will be printed on the console.

## wazo-debug access

`wazo-debug access` open an access to this Platform even behind a NAT or a Firewall. This is done opening a SSH tunnel on a remote server, the local port being exposed on a random port on the remote server.

### Usage

```
wazo-debug access
```

### Exit status

* Exit status `1`: Tunnel creation failed on all retries
* Exit status `2`: Tunnel connectivity check failed: the server cannot reach the SSH reverse-proxy.

## wazo-debug public-ip

`wazo-debug public-ip` detects the NAT type and public IP address used by the Wazo server to access the Internet.

### Usage

```
wazo-debug public-ip --stun-host stun.example.org
```

## wazo-debug http-request-duration

`wazo-debug http-request-duration` displays HTTP requests sorted by response duration. The first column is the request duration in seconds.

### Usage

```
wazo-debug http-request-duration
wazo-debug http-request-duration --access-file /var/log/nginx/wazo.example.com.access.log
```

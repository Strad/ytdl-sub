# Example Configurations
This directory shows how use ytdl-sub's built-in presets to start downloading immediately with no
configuration required. Simply run:

### Unix
```commandline
ytdl-sub sub tv_show_subscriptions.yaml
```

### Windows
```commandline
./ytdl-sub.exe sub tv_show_subscriptions.yaml
```

## Hooks

Hooks allow running custom commands or webhooks after certain events. A minimal
configuration looks like:

```yaml
hooks:
  after_move:
    - type: exec
      cmd: echo
      args: ["{final_filepath}"]
    - type: webhook
      url: http://localhost:8080
      body_json:
        file: "{final_filepath}"
```

The above runs a local command printing the final path and posts the same path
to an HTTP endpoint.

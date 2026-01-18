## BASIC USAGE
mise i|install python@3.11      # install specific version
mise i|install python@latest    # install latest version
mise u|use [-g] python@3.11     # use specified version (-g: global)
mise ls [python]                # list installed versions
mise ls-remote python           # list available versions
mise outdated                   # show outdated tools
mise uninstall python@3.11      # uninstall specific version
mise plugins ls|install uv      # list|install plugin

## CONFIGURATION
mise.toml                   # local project config

## MISE.TOML EXAMPLE
```
[tools]
python = "3.11"
node = "20.0.0"
[env]
PYTHONPATH = "."
NODE_ENV = "development"
[tasks.build]
run = "npm run build"
[tasks.test]
run = "pytest"
```

## EXECUTION
mise exec python -- python script.py  # run with mise-managed tool
mise x -- python script.py            # shorthand
mise run <task>                       # run defined task (defined in mise.toml)

## SHELL
mise activate|a            # enable mise in shell
mise deactivate            # disable mise in shell
mise shell python@3.11     # enter shell with specific tool version
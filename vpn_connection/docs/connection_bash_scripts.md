# Bash Configuration

## VPN Connection

```bash
# Connect via WSL
alias con='python3 /home/sharonf/workspace/canary/utility/vpn_con.py'
```

## Custom Functions for WSL Shell

```bash
# Connect to dev machine
dev_machine_screen_func() {
  python3 /home/sharonf/workspace/canary/utility/dev_machine_connection.py "$1"
}

# Connect to Ixia
ixiacon_func() {
  # xfreerdp -u admin -p cmpsys2012 10.1.90."$1"
  xfreerdp /u:admin /p:cmpsys2012 /v:10.1.90."$1" /sec:rdp
}

# Parse git branch for prompt
parse_git_branch() {
 git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/(\1)/'
}
```

## Aliases

```bash
alias go=dev_machine_screen_func
alias mygo='ssh sharonf@172.30.16.107'
alias ixiacon=ixiacon_func
alias nx="/usr/NX/bin/nxplayer"
alias my='scp -r /home/sharonf/workspace/canary/dut_ctrl/*.py /home/sharonf/workspace/canary/dut_ctrl/config.ini sharonf@172.30.16.107:/home/sharonf/workspace/canary/dut_ctrl'
```

## Prompt Configuration

```bash
if [ "$color_prompt" = yes ]; then
    PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[01;33m\]$(parse_git_branch)\[\033[00m\]\$ '
else
    PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w$(parse_git_branch)\$ '
fi
```

## Path and Environment Configuration

```bash
# Add .pyenv to PATH
export PATH="$HOME/.pyenv/bin:$PATH"

# pyenv initialization
export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
```
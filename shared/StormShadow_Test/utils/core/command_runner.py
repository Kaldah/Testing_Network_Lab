import os
import sys
import shutil
import shlex
import subprocess
import threading

from typing import List, Optional, Dict, Sequence
from utils.core.console_window import ConsoleWindow
from utils.core.logs import print_debug, print_in_dev, print_warning

def _prefix_sudo_argv(argv: List[str],
                    want_sudo: bool,
                    non_interactive: bool = True,
                    preserve_env: bool = False) -> List[str]:
    """Prefix argv with sudo when requested & available; never double-add."""
    if not want_sudo or os.geteuid() == 0:
        return argv
    sudo_path = shutil.which("sudo")
    if not sudo_path:
        print_warning("sudo requested but not available; running without sudo")
        return argv
    sudo_argv = [sudo_path]
    if non_interactive:
        sudo_argv.append("-n")
    if preserve_env:
        sudo_argv.append("-E")
    return sudo_argv + argv

def run_command(
    argv: List[str],
    *,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    want_sudo: bool = False,
    sudo_non_interactive: bool = True,
    sudo_preserve_env: bool = False,
    capture_output: bool = True,
    check: bool = True,
    text: bool = True,
    dry_run: bool = False
) -> subprocess.CompletedProcess[str]:
    """
    Run a command as a list of arguments and return a CompletedProcess result.

        Features:

        - No shell: arguments are passed directly to the OS, avoiding shell injection risks.
        - Automatic sudo support: if want_sudo is True and the current user is not root, the
            command is prefixed with sudo (if available). If sudo_non_interactive is True, "-n" is
            added to fail fast instead of waiting for a password prompt. If sudo_non_interactive is
            False, interactive prompts are allowed. If sudo_preserve_env is True, "-E" is added to
            preserve the current environment variables under sudo.
        - Environment control: override cwd (working directory) and env (environment variables).
        - Output capture: by default, both stdout and stderr are captured (capture_output=True), and
            the output is decoded to text strings (text=True).
        - Error handling: if check=True, raise subprocess.CalledProcessError on non-zero exit; otherwise
            return the CompletedProcess object without raising.

    Args:
        argv: List of program arguments, for example ["ls", "-l"].
        cwd: Optional working directory to run the command in.
        env: Optional dict of environment variables to pass to the command.
        want_sudo: Whether to prefix the command with sudo when not root.
        sudo_non_interactive: If True, pass -n to sudo to fail fast if a password is required.
            If False, allow interactive password prompts.
        sudo_preserve_env: If True, pass -E to sudo to keep the current environment.
        capture_output: If True, capture stdout and stderr into the CompletedProcess object.
        check: If True, raise an exception if the command returns a non-zero exit code.
        text: If True, decode stdout/stderr to str; if False, return bytes.

    Returns:
        subprocess.CompletedProcess: The result object with attributes args, returncode, stdout
        (if capture_output=True), and stderr (if capture_output=True).

    Raises:
        subprocess.CalledProcessError: If check=True and the command fails.
        RuntimeError: If want_sudo=True but sudo is requested/required and not available.
    """
    if env is None:
        env = dict(os.environ)

    final_argv = _prefix_sudo_argv(
        argv,
        want_sudo=want_sudo,
        non_interactive=sudo_non_interactive,
        preserve_env=sudo_preserve_env,
    )
    if dry_run:
        print_debug("Dry run enabled, not actually executing.")
        raise RuntimeError("Dry run enabled, not actually executing.")
    print_debug("Executing command: " + " ".join(shlex.quote(a) for a in final_argv))
    return subprocess.run(
        final_argv,
        cwd=cwd,
        env=env,
        capture_output=capture_output,
        check=check,
        text=text,
    )

def run_command_str(
    command: str,
    *,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    want_sudo: bool = False,
    sudo_non_interactive: bool = True,
    sudo_preserve_env: bool = False,
    capture_output: bool = True,
    check: bool = True,
    text: bool = True,
    dry_run: bool = False
) -> subprocess.CompletedProcess[str]:
    """
    Convenience wrapper when you have a simple string command (no pipes, &&, etc.).
    Splits with shlex and calls run_command.
    """
    argv = shlex.split(command)
    return run_command(
        argv,
        cwd=cwd,
        env=env,
        want_sudo=want_sudo,
        sudo_non_interactive=sudo_non_interactive,
        sudo_preserve_env=sudo_preserve_env,
        capture_output=capture_output,
        check=check,
        text=text,
        dry_run=dry_run
    )

def run_process(argv: List[str],
                *,
                cwd: Optional[str] = None,
                env: Optional[Dict[str, str]] = None,
                want_sudo: bool = False,
                new_terminal: bool = False,
                open_window: bool = False,
                interactive: bool = False,
                window_title: Optional[str] = None,
                sudo_preserve_env: bool = False,
                sudo_non_interactive: bool = True,
                keep_window_open: bool = False,
                dry_run: bool = False) -> subprocess.Popen[bytes]:
    """
    Run a command (argv) robustly. Creates a new process group so you can signal it later.

    Args:
        argv: command as a list, e.g. ["python3", "script.py", "--flag"]
        want_sudo: let this function decide whether/how to prefix sudo
        new_terminal: if True, spawn gnome-terminal and exec the command
        open_window: if True, spawn a Tk window that shows the process' TTY output
        interactive: when open_window=True, allow typing to child's stdin (input())
        window_title: override the Tk window title
    Returns:
        subprocess.Popen: the child process (you still keep full control from main)
    """

    if env is None:
        env = dict(os.environ)

    # Build final argv (handle sudo once, centrally)
    final_argv = _prefix_sudo_argv(
        argv,
        want_sudo=want_sudo,
        non_interactive=sudo_non_interactive,
        preserve_env=sudo_preserve_env
    )
    if new_terminal and open_window:
        raise ValueError("Choose either new_terminal or open_window, not both.")
    
    if new_terminal:
        # Use bash -lc with exec so signals hit the real process.
        inner = "exec " + " ".join(shlex.quote(a) for a in final_argv)
        if keep_window_open:
            # Add "; bash" to keep the terminal open after the command finishes
            inner = inner + "; echo 'Process finished. Press Enter to exit or wait 30s...'; timeout 30 bash || true"
        cmd = ['gnome-terminal', '--', 'bash', '-lc', inner]
        print_in_dev(f"Running in new terminal: {cmd}")
        if dry_run:
            print_debug("Dry run enabled, not actually executing.")
            raise RuntimeError("Dry run enabled, not actually executing.")
        return subprocess.Popen(cmd, cwd=cwd, env=env, start_new_session=True)

    if open_window:
        # Use ConsoleWindow.spawn to properly handle the terminal backend
        title = window_title or "Console Window"
        auto_close = not keep_window_open  # Don't auto-close if we want to keep the window open
        win = ConsoleWindow.spawn(
            final_argv,
            cwd=cwd,
            env=env,
            prefer_tty=True,
            title=title,
            interactive=interactive,
            auto_close=auto_close,
            start_new_session=True
        )
        # Start the window in a separate thread so it doesn't block
        def run_window():
            win.create_tk_console()
        
        window_thread = threading.Thread(target=run_window, daemon=True)
        window_thread.start()
        
        # Return the process from the ConsoleWindow
        proc = win.process or win.io.proc
        if proc is None:
            raise RuntimeError("Failed to create process for console window")
        return proc

    # Normal, non-windowed process
    print_debug(f"Running: {final_argv}")
    if dry_run:
        print_debug("Dry run enabled, not actually executing.")
        raise RuntimeError("Dry run enabled, not actually executing.")
    return subprocess.Popen(final_argv, cwd=cwd, env=env, start_new_session=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def run_python(*,
            module: Optional[str] = None,
            script: Optional[str] = None,
            args: Sequence[str] = (),
            cwd: Optional[str] = None,
            env: Optional[Dict[str, str]] = None,
            want_sudo: bool = False,
            new_terminal: bool = False,
            open_window: bool = False,
            window_title: Optional[str] = None,
            interactive: bool = False,
            sudo_preserve_env: bool = True,
            sudo_non_interactive: bool = True,
            keep_window_open: bool = False,
            dry_run: bool = False):
    """
    Launch Python using the SAME interpreter as this process.

    Exactly one of `module` or `script` must be provided.
    `args` is a sequence of extra arguments for the target.
    """

    py = sys.executable or shutil.which("python3") or "python3"
    if module is not None:
        argv = [py, "-m", module, *map(str, args)]
    elif script is not None:
        argv = [py, script, *map(str, args)]
    else:
        raise ValueError("Specify exactly one of `module` or `script`.")

    return run_process(
        argv,
        cwd=cwd,
        env=env,
        want_sudo=want_sudo,
        new_terminal=new_terminal,
        open_window=open_window,
        window_title=window_title,
        interactive=interactive,
        sudo_preserve_env=sudo_preserve_env,
        sudo_non_interactive=sudo_non_interactive,
        keep_window_open=keep_window_open,
        dry_run=dry_run
    )
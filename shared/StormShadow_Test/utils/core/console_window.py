from __future__ import annotations

from subprocess import Popen
from typing import Optional, Sequence, Dict, Union
import os
import platform
import tkinter as tk
from tkinter import scrolledtext, ttk

# Type aliases to fix Pylance Widget issues
TkWidget = Union[tk.Widget, tk.Tk, tk.Frame]

# Terminal backend interface + helpers
from utils.core.tty_terminal import TerminalIO, PipeTerminal, create_terminal


class ConsoleWindow:
    """
    Tk console that mirrors a running process.

    Exactly one of:
      - process: an existing Popen created with stdin=PIPE, stdout=PIPE (stderr optional)
      - io: a TerminalIO backend (e.g., PTY-backed on Unix)

    Closing the window does NOT kill the process. The window auto-closes when the process exits.
    """

    def __init__(
        self,
        process: Optional[Popen[bytes]] = None,
        *,
        io: Optional[TerminalIO] = None,
        title: str = "Console Window",
        interactive: bool = False,
        auto_close: bool = True,
        is_detached: bool = True,
        parent: Optional[TkWidget] = None,
    ) -> None:
        # Enforce EXACTLY one of process / io
        if (process is None) == (io is None):
            raise ValueError("Provide exactly one of `process` or `io`.")

        # If a Popen is provided, wrap it with a pipe-backed backend
        if io is None:
            if process is None or process.stdin is None or process.stdout is None:
                raise ValueError("`process` must be started with stdin=PIPE and stdout=PIPE.")
            io = PipeTerminal.wrap_existing(process)

        self.io: TerminalIO = io
        self.process: Optional[Popen[bytes]] = process or io.proc
        self.title = title
        self.interactive = interactive
        self.auto_close = auto_close
        self.is_detached = is_detached
        self.parent = parent

        self.root: Optional[tk.Tk] = None
        self.frame: Optional[tk.Frame] = None  # For embedded mode
        self.text_area: Optional[scrolledtext.ScrolledText] = None
        self.entry: Optional[ttk.Entry] = None

    # Optional: a spawner helper that *externally* decides PTY vs pipes
    @classmethod
    def spawn(
        cls,
        argv: Sequence[str],
        *,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        prefer_tty: bool = True,
        title: str = "Console Window",
        interactive: bool = False,
        auto_close: bool = True,
        start_new_session: bool = True,
        is_detached: bool = True,
        parent: Optional[TkWidget] = None,
    ) -> "ConsoleWindow":
        io = create_terminal(
            argv,
            cwd=cwd,
            env=env,
            prefer_tty=prefer_tty,
            start_new_session=start_new_session,
        )
        return cls(io=io, title=title, interactive=interactive, auto_close=auto_close, 
                  is_detached=is_detached, parent=parent)

    # --- Public -------------------------------------------------------------

    def create_tk_console(self) -> None:
        """Create console window - detached (new window) or embedded (in parent widget)."""
        if self.is_detached:
            self._create_detached_console()
        else:
            self._create_embedded_console()

    def _create_detached_console(self) -> None:
        """Create a detached console in a new Tk window."""
        self.root = tk.Tk()
        self.root.title(self.title)
        self.root.geometry("920x540")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self._create_console_widgets(self.root)
        
        self._pump_output()
        self._watch_process()
        self.root.mainloop()

    def _create_embedded_console(self) -> tk.Frame:
        """Create an embedded console within a parent widget. Returns the frame."""
        if not self.parent:
            raise ValueError("Parent widget required for embedded console")
            
        self.frame = tk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        self._create_console_widgets(self.frame)
        
        self._pump_output()
        self._watch_process()
        
        return self.frame

    def get_widget(self) -> Optional[TkWidget]:
        """Get the console widget (root window for detached, frame for embedded)."""
        return self.root if self.is_detached else self.frame

    def _create_console_widgets(self, parent: TkWidget) -> None:
        """Create console widgets in the specified parent."""
        self.text_area = scrolledtext.ScrolledText(parent, wrap=tk.WORD)
        self.text_area.configure(
            font=("Fira Mono", 11),
            background="#0c0c0c",
            foreground="#e5e5e5",
            insertbackground="#e5e5e5",
        )
        self.text_area.pack(expand=True, fill="both")

        bar = ttk.Frame(parent)
        bar.pack(fill="x")
        # ttk.Button(bar, text="INT (Ctrl‑C)", command=self.send_interrupt).pack(side="left", padx=4, pady=4)
        # ttk.Button(bar, text="TERM", command=self.send_terminate).pack(side="left", padx=4, pady=4)
        # ttk.Button(bar, text="KILL", command=self.send_kill).pack(side="left", padx=4, pady=4)

        if self.interactive:
            row = ttk.Frame(parent)
            row.pack(fill="x")
            ttk.Label(row, text="stdin:").pack(side="left", padx=(6, 2))
            self.entry = ttk.Entry(row)
            self.entry.pack(side="left", fill="x", expand=True, padx=(0, 6), pady=6)
            self.entry.bind("<Return>", self._send_line)
            # Allow keyboard shortcuts to work on the entry widget too
            self.entry.bind("<Control-c>", lambda e: self.send_interrupt())
            self.entry.bind("<Control-z>", lambda e: self.send_stop())
            self.entry.bind("<Control-backslash>", lambda e: self.send_quit())
            self.entry.bind("<Control-Shift-C>", lambda e: self._copy_text())

        # Add global keyboard shortcuts for the window/frame
        widget = self.root if self.is_detached else parent
        if widget:
            widget.bind("<Control-c>", lambda e: self.send_interrupt())
            widget.bind("<Control-z>", lambda e: self.send_stop())
            widget.bind("<Control-backslash>", lambda e: self.send_quit())
            widget.bind("<Control-d>", lambda e: self._send_eof())
            widget.bind("<Control-Shift-C>", lambda e: self._copy_text())
        
        # Allow text area to have focus for keyboard shortcuts
        if self.text_area:
            self.text_area.bind("<Control-c>", lambda e: self.send_interrupt())
            self.text_area.bind("<Control-z>", lambda e: self.send_stop())
            self.text_area.bind("<Control-backslash>", lambda e: self.send_quit())
            self.text_area.bind("<Control-Shift-C>", lambda e: self._copy_text())

    def show(self) -> None:
        """Show the console (create if not exists)."""
        if self.is_detached and not self.root:
            self.create_tk_console()
        elif not self.is_detached and not self.frame:
            self._create_embedded_console()

    def hide(self) -> None:
        """Hide the console."""
        if self.is_detached and self.root:
            self.root.withdraw()
        elif not self.is_detached and self.frame:
            self.frame.pack_forget()

    def destroy(self) -> None:
        """Destroy the console window/frame."""
        try:
            self.io.close()
        except Exception:
            pass
        
        if self.is_detached and self.root:
            self.root.destroy()
            self.root = None
        elif not self.is_detached and self.frame:
            self.frame.destroy()
            self.frame = None

    def send_interrupt(self) -> None:
        self._signal("INT")

    def send_terminate(self) -> None:
        self._signal("TERM")

    def send_kill(self) -> None:
        self._signal("KILL")

    def send_stop(self) -> None:
        self._signal("STOP")

    def send_quit(self) -> None:
        self._signal("QUIT")

    # --- Internals ----------------------------------------------------------

    def _append(self, s: str) -> None:
        if self.text_area:
            # Parse ANSI colors and apply as text tags
            self._append_with_colors(s)
            self.text_area.see("end")

    def _append_with_colors(self, text: str) -> None:
        """Append text with ANSI color codes converted to tkinter text tags."""
        if not self.text_area:
            return
            
        # ANSI color mapping to tkinter colors (matching our logging colors)
        ansi_colors = {
            '91': '#ff6b6b',  # bright red (for errors)
            '92': '#51fa7a',  # bright green (for success)
            '93': '#f1c40f',  # bright yellow (for warnings)
            '94': '#74b9ff',  # bright blue (for info)
            '95': '#fd79a8',  # bright magenta (for debug)
            '96': '#81ecec',  # bright cyan
            '97': '#ffffff',  # bright white
            # Standard colors
            '31': '#ff0000',  # red
            '32': '#00ff00',  # green
            '33': '#ffff00',  # yellow
            '34': '#0000ff',  # blue
            '35': '#ff00ff',  # magenta
            '36': '#00ffff',  # cyan
            '37': '#ffffff',  # white
        }
        
        import re
        
        # More comprehensive ANSI pattern that matches all escape sequences
        ansi_pattern = re.compile(r'\x1b\[([0-9;]*)?([a-zA-Z])')
        
        current_color = None
        current_bold = False
        position = 0
        
        for match in ansi_pattern.finditer(text):
            # Add text before this ANSI sequence
            if match.start() > position:
                plain_text = text[position:match.start()]
                if plain_text:
                    start_pos = self.text_area.index("end-1c")
                    self.text_area.insert("end", plain_text)
                    
                    # Apply current formatting
                    if current_color or current_bold:
                        end_pos = self.text_area.index("end-1c")
                        tag_name = f"style_{hash((current_color, current_bold)) % 1000}"
                        
                        if current_color and current_bold:
                            self.text_area.tag_configure(tag_name, 
                                                       foreground=current_color,
                                                       font=("Fira Mono", 11, "bold"))
                        elif current_color:
                            self.text_area.tag_configure(tag_name, 
                                                       foreground=current_color,
                                                       font=("Fira Mono", 11))
                        elif current_bold:
                            self.text_area.tag_configure(tag_name, 
                                                       font=("Fira Mono", 11, "bold"))
                        
                        self.text_area.tag_add(tag_name, start_pos, end_pos)
            
            # Process ANSI sequence (only color sequences ending with 'm')
            if match.group(2) == 'm':
                codes_str = match.group(1) or '0'
                codes = codes_str.split(';') if codes_str else ['0']
                
                for code in codes:
                    if code == '0' or code == '':  # Reset
                        current_color = None
                        current_bold = False
                    elif code == '1':  # Bold
                        current_bold = True
                    elif code in ansi_colors:  # Color
                        current_color = ansi_colors[code]
            
            position = match.end()
        
        # Add remaining text after last ANSI sequence
        if position < len(text):
            remaining_text = text[position:]
            if remaining_text:
                start_pos = self.text_area.index("end-1c")
                self.text_area.insert("end", remaining_text)
                
                # Apply current formatting
                if current_color or current_bold:
                    end_pos = self.text_area.index("end-1c")
                    tag_name = f"style_{hash((current_color, current_bold)) % 1000}"
                    
                    if current_color and current_bold:
                        self.text_area.tag_configure(tag_name, 
                                                   foreground=current_color,
                                                   font=("Fira Mono", 11, "bold"))
                    elif current_color:
                        self.text_area.tag_configure(tag_name, 
                                                   foreground=current_color,
                                                   font=("Fira Mono", 11))
                    elif current_bold:
                        self.text_area.tag_configure(tag_name, 
                                                   font=("Fira Mono", 11, "bold"))
                    
                    self.text_area.tag_add(tag_name, start_pos, end_pos)

    def _sanitize_text(self, text: str) -> str:
        """Remove unwanted control characters but preserve ANSI color sequences."""
        # Don't remove any ANSI sequences here - let _append_with_colors handle them
        # Only remove other control characters
        
        # Clean up lines by removing unwanted characters at beginning and end only
        lines = text.split('\n')
        cleaned_lines: list[str] = []
        
        # Define unwanted control characters to strip (excluding \n, \t, \x1B for ANSI, but including \r)
        control_chars = '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0B\x0C\x0D\x0E\x0F\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1A\x1C\x1D\x1E\x1F\x7F'
        
        for line in lines:
            # Strip unwanted control characters from beginning and end of each line
            cleaned_line = line.strip(control_chars)
            # Also strip regular whitespace to clean up any extra spaces/tabs at line ends
            cleaned_line = cleaned_line.rstrip()
            cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines)

    def _copy_text(self) -> None:
        """Copy selected text or all text to clipboard."""
        if not self.text_area or not self.root:
            return
        
        selected_text = ""
        try:
            # Try to get selected text first
            selected_text = str(self.text_area.get("sel.first", "sel.last"))
        except tk.TclError:
            # If no selection, copy all text
            selected_text = str(self.text_area.get("1.0", "end-1c"))
        
        if selected_text:
            # Copy to clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.root.update()  # Ensure clipboard is updated

    def _pump_output(self) -> None:
        while True:
            chunk = self.io.read_nowait()
            if not chunk:
                break
            try:
                text = chunk.decode("utf-8", "replace")
            except Exception:
                text = chunk.decode("latin-1", "replace")
            
            # Sanitize the text before appending (keeps ANSI colors)
            sanitized_text = self._sanitize_text(text)
            self._append(sanitized_text)
        
        # Schedule next pump for both detached and embedded modes
        widget = self.root if self.is_detached else self.frame
        if widget:
            widget.after(30, self._pump_output)

    def _watch_process(self) -> None:
        proc = self.process or self.io.proc
        exited = (proc is not None and proc.poll() is not None)
        if exited and self.auto_close:
            try:
                self.io.close()
            except Exception:
                pass
            if self.is_detached and self.root:
                self.root.after(50, self.root.destroy)
            elif not self.is_detached and self.frame:
                # For embedded mode, just stop pumping but don't destroy
                pass
            return
        
        # Schedule next watch for both detached and embedded modes
        widget = self.root if self.is_detached else self.frame
        if widget:
            widget.after(200, self._watch_process)

    def _on_close(self) -> None:
        """Handle window close - only for detached mode."""
        if self.is_detached:
            self.destroy()

    def _send_line(self, _evt: Optional[tk.Event] = None) -> None:
        if not self.interactive or not self.entry:
            return
        data = (self.entry.get() + "\n").encode("utf-8", "replace")
        try:
            self.io.write(data)
        except Exception:
            pass
        self.entry.delete(0, "end")

    def _send_eof(self) -> None:
        """Send EOF (Ctrl+D) to the process stdin."""
        try:
            # EOF is represented by closing stdin or sending \x04 (EOT)
            self.io.write(b"\x04")
        except Exception:
            pass

    def _signal(self, kind: str) -> None:
        proc = self.process or self.io.proc
        if proc is None:
            return

        system = platform.system().lower()
        if system == "windows":
            try:
                if kind in ("INT", "TERM"):
                    proc.terminate()
                else:
                    proc.kill()
            except Exception:
                pass
            return

        # POSIX
        try:
            import signal as _sig
            sigmap = {
                "INT": _sig.SIGINT, 
                "TERM": _sig.SIGTERM, 
                "KILL": _sig.SIGKILL,
                "STOP": _sig.SIGTSTP,  # Ctrl+Z
                "QUIT": _sig.SIGQUIT,  # Ctrl+\
            }
            sig = sigmap.get(kind, _sig.SIGTERM)
            try:
                pgid = os.getpgid(proc.pid)
            except Exception:
                pgid = None
            if pgid and pgid > 0:
                os.killpg(pgid, sig)
            else:
                os.kill(proc.pid, sig)
        except Exception:
            pass

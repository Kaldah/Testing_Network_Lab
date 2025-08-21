"""
Theme utilities for the StormShadow GUI.

This module provides modern theming capabilities for the Tkinter interface.
"""

import tkinter as tk
from tkinter import ttk
from typing import TypedDict, Any, cast


class StyleConfigDict(TypedDict, total=False):
    """Type for style configuration parameters."""
    background: str
    foreground: str
    troughcolor: str
    borderwidth: int
    relief: str
    lightcolor: str
    darkcolor: str
    padding: tuple[int, ...]
    font: tuple[str, int, str]
    fieldbackground: str
    arrowcolor: str
    insertcolor: str
    slidercolor: str
    focuscolor: str


def apply_modern_theme(root: tk.Tk):
    """
    Apply a modern theme to the Tkinter application.

    Args:
        root: The root Tkinter window
    """
    # Configure the root window
    root.configure(bg='#2b2b2b')
    # Create a modern style
    style = ttk.Style()
    style.theme_use('clam')

    # Pylance's tkinter/ttk stubs leave Style.configure / Style.map partially
    # untyped which causes `reportUnknownMemberType` diagnostics. Cast the
    # style to Any and call configure/map through small wrappers so the type
    # checker doesn't try to infer the dynamic kwargs passed to those methods.
    style_any = cast(Any, style)

    from typing import Any as _Any

    def _sconfig(*args: _Any, **kwargs: _Any) -> _Any:
        return style_any.configure(*args, **kwargs)

    def _smap(*args: _Any, **kwargs: _Any) -> _Any:
        return style_any.map(*args, **kwargs)
    
    # Configure modern colors
    colors = {
        'bg': '#2b2b2b',           # Dark background
        'fg': '#ffffff',           # White text
        'select_bg': '#404040',    # Darker selection background
        'select_fg': '#ffffff',    # White selection text
        'entry_bg': '#404040',     # Entry background
        'button_bg': '#404040',    # Button background
        'active_bg': '#505050',    # Active/hover background
        'accent': '#0078d4',       # Accent color (blue)
        'success': '#107c10',      # Success color (green)
        'warning': '#ff8c00',      # Warning color (orange)
        'error': '#d13438',        # Error color (red)
        'border': '#555555',       # Border color
    }

    # Frame styles
    _sconfig('TFrame', background=colors['bg'])

    # Label styles
    _sconfig('TLabel', background=colors['bg'], foreground=colors['fg'])
    _sconfig('Title.TLabel', background=colors['bg'], foreground=colors['fg'],
                    font=('Segoe UI', 14, 'bold'))
    _sconfig('Heading.TLabel', background=colors['bg'], foreground=colors['fg'],
                    font=('Segoe UI', 12, 'bold'))
    _sconfig('Success.TLabel', background=colors['bg'], foreground=colors['success'])
    _sconfig('Warning.TLabel', background=colors['bg'], foreground=colors['warning'])
    _sconfig('Error.TLabel', background=colors['bg'], foreground=colors['error'])

    # Button styles
    _sconfig('TButton',
                    background=colors['button_bg'],
                    foreground=colors['fg'],
                    borderwidth=1,
                    focuscolor='none',
                    relief='flat')
    _smap('TButton',
              background=[('active', colors['active_bg']),
                          ('pressed', colors['select_bg'])])

    # Primary button style
    _sconfig('Primary.TButton',
                    background=colors['accent'],
                    foreground='white',
                    borderwidth=0,
                    focuscolor='none')
    _smap('Primary.TButton',
              background=[('active', '#106ebe'),
                          ('pressed', '#005a9e')])

    # Success button style
    _sconfig('Success.TButton',
                    background=colors['success'],
                    foreground='white',
                    borderwidth=0,
                    focuscolor='none')
    _smap('Success.TButton',
              background=[('active', '#0e6e0e'),
                          ('pressed', '#0c5d0c')])

    # Warning button style
    _sconfig('Warning.TButton',
                    background=colors['warning'],
                    foreground='white',
                    borderwidth=0,
                    focuscolor='none')
    _smap('Warning.TButton',
              background=[('active', '#e67c00'),
                          ('pressed', '#cc6f00')])

    # Danger button style
    _sconfig('Danger.TButton',
                    background=colors['error'],
                    foreground='white',
                    borderwidth=0,
                    focuscolor='none')
    _smap('Danger.TButton',
              background=[('active', '#bc2e32'),
                          ('pressed', '#a7282c')])

    # Entry styles
    _sconfig('TEntry',
                    fieldbackground=colors['entry_bg'],
                    background=colors['entry_bg'],
                    foreground=colors['fg'],
                    borderwidth=1,
                    insertcolor=colors['fg'])
    _smap('TEntry',
              focuscolor=[('!focus', colors['border']),
                          ('focus', colors['accent'])])

    # Combobox styles
    _sconfig('TCombobox',
                    fieldbackground=colors['entry_bg'],
                    background=colors['entry_bg'],
                    foreground=colors['fg'],
                    borderwidth=1,
                    arrowcolor=colors['fg'])
    _smap('TCombobox',
              focuscolor=[('!focus', colors['border']),
                          ('focus', colors['accent'])],
              fieldbackground=[('readonly', colors['entry_bg'])])

    # Notebook styles
    _sconfig('TNotebook', background=colors['bg'], borderwidth=0)
    _sconfig('TNotebook.Tab',
                    background=colors['button_bg'],
                    foreground=colors['fg'],
                    padding=(20, 10),
                    borderwidth=1)
    _smap('TNotebook.Tab',
              background=[('selected', colors['accent']),
                          ('active', colors['active_bg'])])

    # Progressbar styles
    _sconfig('TProgressbar',
                    background=colors['accent'],
                    troughcolor=colors['select_bg'],
                    borderwidth=0,
                    lightcolor=colors['accent'],
                    darkcolor=colors['accent'])

    # Treeview styles
    _sconfig('TTreeview',
                    background=colors['entry_bg'],
                    foreground=colors['fg'],
                    fieldbackground=colors['entry_bg'],
                    borderwidth=1)
    _smap('TTreeview',
              background=[('selected', colors['accent'])],
              foreground=[('selected', 'white')])

    # Treeview heading style
    _sconfig('Treeview.Heading',
                    background=colors['button_bg'],
                    foreground=colors['fg'],
                    borderwidth=1)
    _smap('Treeview.Heading',
              background=[('active', colors['active_bg'])])

    # Scale/Slider styles
    _sconfig('TScale',
                    background=colors['bg'],
                    troughcolor=colors['entry_bg'],
                    borderwidth=1,
                    slidercolor=colors['accent'])

    # Checkbutton styles
    _sconfig('TCheckbutton',
                    background=colors['bg'],
                    foreground=colors['fg'],
                    focuscolor='none',
                    borderwidth=0)
    _smap('TCheckbutton',
              background=[('active', colors['bg'])],
              indicatorcolor=[('selected', colors['accent']),
                              ('!selected', colors['entry_bg'])])

    # Radiobutton styles
    _sconfig('TRadiobutton',
                    background=colors['bg'],
                    foreground=colors['fg'],
                    focuscolor='none',
                    borderwidth=0)
    _smap('TRadiobutton',
              background=[('active', colors['bg'])],
              indicatorcolor=[('selected', colors['accent']),
                              ('!selected', colors['entry_bg'])])

    # Scrollbar styles
    _sconfig('TScrollbar',
                    background=colors['button_bg'],
                    troughcolor=colors['bg'],
                    borderwidth=0,
                    arrowcolor=colors['fg'])
    _smap('TScrollbar',
              background=[('active', colors['active_bg'])])


def get_theme_colors():
    """
    Get the current theme color palette.

    Returns:
        dict: Dictionary of color values
    """
    return {
        'bg': '#2b2b2b',
        'fg': '#ffffff',
        'select_bg': '#404040',
        'select_fg': '#ffffff',
        'entry_bg': '#404040',
        'button_bg': '#404040',
        'active_bg': '#505050',
        'accent': '#0078d4',
        'success': '#107c10',
        'warning': '#ff8c00',
        'error': '#d13438',
        'border': '#555555',
    }


def create_tooltip(widget: tk.Widget, text: str) -> None:
    """
    Create a tooltip for a widget.

    Args:
        widget: The widget to attach the tooltip to
        text: The tooltip text
    """
    def show_tooltip(event: tk.Event):
        tooltip = tk.Toplevel()
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

        colors = get_theme_colors()
        tooltip.configure(bg=colors['select_bg'])

        label = tk.Label(tooltip, text=text,
                         background=colors['select_bg'],
                         foreground=colors['fg'],
                         font=('Segoe UI', 9),
                         padx=10, pady=5)
        label.pack()

        def hide_tooltip():
            tooltip.destroy()

        tooltip.after(3000, hide_tooltip)  # Auto-hide after 3 seconds
        cast(Any, widget).tooltip = tooltip

    def hide_tooltip(event: tk.Event) -> None:
        if hasattr(widget, 'tooltip'):
            cast(Any, widget).tooltip.destroy()
            # remove the attribute we set earlier
            del cast(Any, widget).tooltip

    widget.bind('<Enter>', show_tooltip)
    widget.bind('<Leave>', hide_tooltip)

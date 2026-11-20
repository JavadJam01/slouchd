import sys
import ctypes
import ctypes.util
from ctypes import c_ulong, c_long, c_char_p, c_int, c_void_p, Structure, byref

_x11 = None
_x11_display = None
_x11_init_attempted = False


class _XClientMessageEvent(Structure):
    _fields_ = [
        ('type', c_int),
        ('serial', c_ulong),
        ('send_event', c_int),
        ('display', c_void_p),
        ('window', c_ulong),
        ('message_type', c_ulong),
        ('format', c_int),
        ('data_l', c_ulong * 5)
    ]


def _get_x11():
    global _x11, _x11_display, _x11_init_attempted
    if _x11_init_attempted:
        return _x11, _x11_display
    _x11_init_attempted = True

    if not sys.platform.startswith("linux"):
        return None, None

    try:
        lib_name = ctypes.util.find_library("X11") or "libX11.so.6"
        lib = ctypes.cdll.LoadLibrary(lib_name)

        lib.XOpenDisplay.restype = c_void_p
        lib.XOpenDisplay.argtypes = [c_char_p]

        lib.XDefaultRootWindow.restype = c_ulong
        lib.XDefaultRootWindow.argtypes = [c_void_p]

        lib.XInternAtom.restype = c_ulong
        lib.XInternAtom.argtypes = [c_void_p, c_char_p, c_int]

        lib.XChangeProperty.restype = c_int
        lib.XChangeProperty.argtypes = [
            c_void_p, c_ulong, c_ulong, c_ulong, c_int, c_int, ctypes.c_char_p, c_int
        ]

        lib.XSendEvent.restype = c_int
        lib.XSendEvent.argtypes = [c_void_p, c_ulong, c_int, c_long, c_void_p]

        lib.XRaiseWindow.restype = c_int
        lib.XRaiseWindow.argtypes = [c_void_p, c_ulong]

        lib.XFlush.restype = c_int
        lib.XFlush.argtypes = [c_void_p]

        disp = lib.XOpenDisplay(None)
        if disp:
            _x11 = lib
            _x11_display = disp
    except Exception:
        _x11 = None
        _x11_display = None

    return _x11, _x11_display


def make_window_sticky(widget):
    """
    Ensure the widget appears on all workspaces/virtual desktops
    and stays on top on GNOME Mutter / X11 / XWayland.
    """
    if not widget:
        return

    try:
        win_id = int(widget.winId())
    except Exception:
        return

    if sys.platform.startswith("linux"):
        x11, display = _get_x11()
        if not x11 or not display:
            return

        try:
            root = x11.XDefaultRootWindow(display)

            net_wm_desktop = x11.XInternAtom(display, b"_NET_WM_DESKTOP", 0)
            cardinal = x11.XInternAtom(display, b"CARDINAL", 0)
            atom = x11.XInternAtom(display, b"ATOM", 0)
            net_wm_state = x11.XInternAtom(display, b"_NET_WM_STATE", 0)
            net_wm_state_sticky = x11.XInternAtom(display, b"_NET_WM_STATE_STICKY", 0)
            net_wm_state_above = x11.XInternAtom(display, b"_NET_WM_STATE_ABOVE", 0)
            net_wm_state_skip_taskbar = x11.XInternAtom(display, b"_NET_WM_STATE_SKIP_TASKBAR", 0)
            net_wm_state_skip_pager = x11.XInternAtom(display, b"_NET_WM_STATE_SKIP_PAGER", 0)

            # 1. Directly set _NET_WM_DESKTOP = 0xFFFFFFFF (all desktops) on window
            all_desktops = (c_ulong * 1)(0xFFFFFFFF)
            x11.XChangeProperty(
                display, win_id, net_wm_desktop, cardinal, 32, 0,
                ctypes.cast(all_desktops, ctypes.c_char_p), 1
            )

            # 2. Directly set initial _NET_WM_STATE property
            states = (c_ulong * 4)(
                net_wm_state_sticky, net_wm_state_above,
                net_wm_state_skip_taskbar, net_wm_state_skip_pager
            )
            x11.XChangeProperty(
                display, win_id, net_wm_state, atom, 32, 0,
                ctypes.cast(states, ctypes.c_char_p), 4
            )

            # 3. Send EWMH ClientMessage for _NET_WM_DESKTOP to root window
            # SubstructureRedirectMask (1 << 20) | SubstructureNotifyMask (1 << 19)
            mask = (1 << 20) | (1 << 19)
            ev_desktop = _XClientMessageEvent()
            ev_desktop.type = 33  # ClientMessage
            ev_desktop.send_event = 1
            ev_desktop.display = display
            ev_desktop.window = win_id
            ev_desktop.message_type = net_wm_desktop
            ev_desktop.format = 32
            ev_desktop.data_l[0] = 0xFFFFFFFF  # all workspaces
            ev_desktop.data_l[1] = 1            # source: normal application
            x11.XSendEvent(display, root, 0, mask, byref(ev_desktop))

            # 4. Send EWMH ClientMessage for _NET_WM_STATE to add STICKY & ABOVE
            ev_state = _XClientMessageEvent()
            ev_state.type = 33  # ClientMessage
            ev_state.send_event = 1
            ev_state.display = display
            ev_state.window = win_id
            ev_state.message_type = net_wm_state
            ev_state.format = 32
            ev_state.data_l[0] = 1              # _NET_WM_STATE_ADD
            ev_state.data_l[1] = net_wm_state_sticky
            ev_state.data_l[2] = net_wm_state_above
            ev_state.data_l[3] = 1              # source: normal application
            x11.XSendEvent(display, root, 0, mask, byref(ev_state))

            x11.XFlush(display)
        except Exception:
            pass


def raise_window_native(widget):
    """Raise window to top natively across window managers."""
    if not widget:
        return
    try:
        win_id = int(widget.winId())
    except Exception:
        return

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.SetWindowPos(win_id, 0, 0, 0, 0, 0, 0x0013)
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        x11, display = _get_x11()
        if x11 and display:
            try:
                x11.XRaiseWindow(display, win_id)
                x11.XFlush(display)
            except Exception:
                pass


def stack_window_above_native(top_widget, bottom_widget):
    """Ensure top_widget is positioned above bottom_widget in the Z-order."""
    if not top_widget or not bottom_widget:
        return
    try:
        top_id = int(top_widget.winId())
        bottom_id = int(bottom_widget.winId())
    except Exception:
        return

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.SetWindowPos(bottom_id, top_id, 0, 0, 0, 0, 0x0013)
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        x11, display = _get_x11()
        if x11 and display:
            try:
                x11.XRaiseWindow(display, bottom_id)
                x11.XRaiseWindow(display, top_id)
                x11.XFlush(display)
            except Exception:
                pass

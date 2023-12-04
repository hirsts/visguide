import keyboard

def print_event(e):
    print(e.name, e.scan_code, e.event_type)

keyboard.hook(print_event)
keyboard.wait('esc')

import keyboard

def test_callback(e):
    print("Space key was pressed!")

keyboard.on_press_key('space', test_callback)

print("Listening for space key...")
keyboard.wait('esc')  # Wait for 'esc' key to exit
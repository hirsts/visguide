import keyboard

# Replace this with the actual scan code for 'b'
B_KEY_CODE = YOUR_KEY_CODE

def on_key_press(key):
    if key.scan_code == B_KEY_CODE:
        print("B key pressed")

def on_key_release(key):
    if key.scan_code == B_KEY_CODE:
        print("B key released")

keyboard.on_press(on_key_press)
keyboard.on_release(on_key_release)

print("Press and release the 'b' key (using key code) to test. Press CTRL+C to exit.")

# Infinite loop to keep the program running
while True:
    pass

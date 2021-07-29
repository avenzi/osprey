from sense_hat import SenseHat, ACTION_PRESSED, ACTION_HELD, ACTION_RELEASED
from signal import pause
from time import sleep

x = 3
y = 3
sense = SenseHat()
print('released: ', ACTION_RELEASED)
print('held: ', ACTION_HELD)
print('pressed: ', ACTION_PRESSED)

def clamp(value, min_value=0, max_value=7):
    return min(max_value, max(min_value, value))

def pushed_up(event):
    global y
    if event.action != ACTION_RELEASED:
        y = clamp(y - 1)

def pushed_down(event):
    global y
    if event.action != ACTION_RELEASED:
        y = clamp(y + 1)

def pushed_left(event):
    global x
    if event.action != ACTION_RELEASED:
        x = clamp(x - 1)

def pushed_right(event):
    global x
    if event.action != ACTION_RELEASED:
        x = clamp(x + 1)

def refresh():
    sense.clear()
    print('setting: x: {}, y: {}'.format(x, y))
    sense.set_pixel(x, y, 255, 255, 255)

#sense.stick.direction_up = pushed_up
#sense.stick.direction_down = pushed_down
#sense.stick.direction_left = pushed_left
#sense.stick.direction_right = pushed_right
#sense.stick.direction_any = refresh
sense.clear()
sense.set_pixel(0, 0, 255, 0, 0)
sense.set_pixel(2, 2, 0, 255, 0)
sense.set_pixel(4, 4, 0, 0, 255)
print(sense.get_pixels())
sleep(2)

sense.clear()

X = [255, 0, 0]  # Red
O = [0, 0, 0]  # off

question_mark = [
O, O, O, X, X, O, O, O,
O, O, X, O, O, X, O, O,
O, O, O, O, O, X, O, O,
O, O, O, O, X, O, O, O,
O, O, O, X, O, O, O, O,
O, O, O, X, O, O, O, O,
O, O, O, O, O, O, O, O,
O, O, O, X, O, O, O, O
]

sense.set_pixels(question_mark)
print(sense.get_pixels())

pause()
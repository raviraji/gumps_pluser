import os
import time
import warnings

# sysfs root
_SYSFS_ROOT = "/sys/class/gpio"

if (not os.access(_SYSFS_ROOT + '/export', os.W_OK) or
        not os.access(_SYSFS_ROOT + '/unexport', os.W_OK)):
    raise RuntimeError("The current user does not have permissions set to "
                       "access the library functionalites. Please configure "
                       "permissions or use the root user to run this")

OUT = 0
IN = 1
HIGH = 1
LOW = 0
_channel_data = {}
_gpio_warnings = True
_channel_configuration = {}

class ChannelInfo(object):
    def __init__(self, channel, gpio_chip_dir, chip_gpio, gpio):
        self.channel = channel
        self.gpio_chip_dir = gpio_chip_dir
        self.chip_gpio = chip_gpio
        self.gpio = gpio


def _make_iterable(iterable, single_length=None):
    if isinstance(iterable, str):
        iterable = [iterable]
    try:
        for _ in iterable:
            break
    except:
        iterable = [iterable]
    if single_length is not None and len(iterable) == 1:
        iterable *= single_length
    return iterable


def _channel_to_info_lookup(channel, need_gpio):
    if channel not in _channel_data:
        raise ValueError("Channel %s is invalid" % str(channel))
    ch_info = _channel_data[channel]
    if need_gpio and ch_info.gpio_chip_dir is None:
        raise ValueError("Channel %s is not a GPIO" % str(channel))



def _channel_to_info(channel, need_gpio=False):
    return _channel_to_info_lookup(channel, need_gpio)


def _channels_to_infos(channels, need_gpio=False):
    return [_channel_to_info_lookup(c, need_gpio)
            for c in _make_iterable(channels)]


def _sysfs_channel_configuration(ch_info):
    """Return the current configuration of a channel as reported by sysfs. Any
    of IN, OUT, PWM, or None may be returned."""


    gpio_dir = _SYSFS_ROOT + "/gpio%i" % ch_info
    if not os.path.exists(gpio_dir):
        return None

    with open(gpio_dir + "/direction", 'r') as f_direction:
        gpio_direction = f_direction.read()

    lookup = {
        'in': IN,
        'out': OUT,
    }
    return lookup.get(gpio_direction.strip().lower())

def setwarnings(state):
    global _gpio_warnings
    _gpio_warnings = bool(state)


def _app_channel_configuration(ch_info):
    """Return the current configuration of a channel as requested by this
    module in this process. Any of IN, OUT, or None may be returned."""

    return _channel_configuration.get(ch_info, None)


def _export_gpio(gpio):
    if os.path.exists(_SYSFS_ROOT + "/gpio%i" % gpio):
        return

    with open(_SYSFS_ROOT + "/export", "w") as f_export:
        f_export.write(str(gpio))

    while not os.access(_SYSFS_ROOT + "/gpio%i" % gpio + "/value",
                        os.R_OK | os.W_OK):
        time.sleep(0.01)


def _unexport_gpio(gpio):
    if not os.path.exists(_SYSFS_ROOT + "/gpio%i" % gpio):
        return

    with open(_SYSFS_ROOT + "/unexport", "w") as f_unexport:
        f_unexport.write(str(gpio))


def _output_one(gpio, value):
    with open(_SYSFS_ROOT + "/gpio%s" % gpio + "/value", 'w') as value_file:
        value_file.write(str(int(bool(value))))


def _setup_single_out(ch_info, initial=None):
    _export_gpio(ch_info)
    time.sleep(0.1)
    gpio_dir_path = _SYSFS_ROOT + "/gpio%i" % ch_info + "/direction"
    with open(gpio_dir_path, 'w') as direction_file:
        direction_file.write("out")

    if initial is not None:
        _output_one(ch_info, initial)

    #_channel_configuration[ch_info.channel] = OUT


def _setup_single_in(ch_info):
    _export_gpio(ch_info)

    gpio_dir_path = _SYSFS_ROOT + "/gpio%i" % ch_info + "/direction"
    with open(gpio_dir_path, 'w') as direction:
        direction.write("in")

    #_channel_configuration[ch_info.channel] = IN

def _cleanup_one(ch_info):
    app_cfg = _channel_configuration[ch_info]
    if app_cfg == HARD_PWM:
        _disable_pwm(ch_info)
        _unexport_pwm(ch_info)
    else:
        event.event_cleanup(ch_info)
        _unexport_gpio(ch_info)
    #del _channel_configuration[ch_info.channel]


def _cleanup_all():
    global _gpio_mode

    for channel in list(_channel_configuration.keys()):
        ch_info = _channel_to_info(channel)
        _cleanup_one(ch_info)

    _gpio_mode = None

# Function used to setup individual pins or lists/tuples of pins as
# Input or Output. Param channels must an integer or list/tuple of integers,
# direction must be IN or OUT, pull_up_down must be PUD_OFF, PUD_UP or
# PUD_DOWN and is only valid when direction in IN, initial must be HIGH or LOW
# and is only valid when direction is OUT
def setup(channels, direction, initial=None):
    #ch_infos = _channels_to_infos(channels, need_gpio=True)

    # check direction is valid

    if direction not in [OUT, IN]:
        raise ValueError("An invalid direction was passed to setup()")
    if direction == OUT:
        if (isinstance(channels, list)):
            initial = _make_iterable(initial, len(channels))
            for ch_info, init in zip(channels, initial):
                _setup_single_out(ch_info, init)
        else:
            _setup_single_out(channels, initial)
    else:
        if initial is not None:
            raise ValueError("initial parameter is not valid for inputs")
        for temp in channels:
            _setup_single_in(channels)

def input(channel):
    #ch_info = _channel_to_info(channel, need_gpio=True)

    with open(_SYSFS_ROOT + "/gpio%i" % channel + "/value") as value:
        return int(value.read())


# Function used to set a value to a channel or list/tuple of channels.
# Parameter channels must be an integer or list/tuple of integers.
# Values must be either HIGH or LOW or list/tuple
# of HIGH and LOW with the same length as the channels list/tuple
def output(channels, values):
    #ch_infos = _channels_to_infos(channels, need_gpio=True)
    if (isinstance(channels, list)):
        values = _make_iterable(values, len(channels))
        for channels, value in zip(channels, values):
            _output_one(channels, value)
    else:
        _output_one(channels, values)


def gpio_function(channel):
    #ch_info = _channel_to_info(channel)
    func = _sysfs_channel_configuration(channel)
    if func is None:
        func = UNKNOWN
    return func


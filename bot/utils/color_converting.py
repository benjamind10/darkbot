import colorsys


def rgb_to_cmyk(a=None, g=None, b=None):
    cmyk_scale = 100
    if a == 0:
        if g == 0:
            pass
        return b == 0 and (
            0, 0, 0, cmyk_scale)
    else:
        c = 1 - a / 255.0
        m = 1 - g / 255.0
        y = 1 - b / 255.0
        min_cmy = min(c, m, y)
        c = (c - min_cmy) / (1 - min_cmy)
        m = (m - min_cmy) / (1 - min_cmy)
        y = (y - min_cmy) / (1 - min_cmy)
        k = min_cmy
        converted = (
            round(c * cmyk_scale), round(m * cmyk_scale), round(y * cmyk_scale), round(k * cmyk_scale))

        return converted


def rgb_to_hsv(a=None, b=None, c=None):
    h, s, v = colorsys.rgb_to_hsv(a / 255.0, b / 255.0, c / 255.0)
    hsv = (round(360 * h), round(100 * s), round(100 * v))

    return hsv


def rgb_to_hsl(a=None, b=None, c=None):
    h, s, l = colorsys.rgb_to_hls(a / 255.0, b / 255.0, c / 255.0)
    hsl = (round(360 * h), round(100 * l), round(100 * s))

    return hsl
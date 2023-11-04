def truncate(decimal, place_value):
    s = '{}'.format(decimal)

    if 'e' in s or 'E' in s:
        return '{0:.{1}f}'.format(decimal, place_value)

    i, p, d = s.partition('.')

    return '.'.join([i, (d +'0' * place_value)[:place_value]])
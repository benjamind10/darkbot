def uptime(dt):
    hours, r = divmod(dt.seconds, 3600)
    minutes, seconds = divmod(r, 60)

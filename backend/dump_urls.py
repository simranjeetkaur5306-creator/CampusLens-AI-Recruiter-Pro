from django.urls import get_resolver


def walk(patterns, prefix=""):
    for p in patterns:
        s = prefix + str(p.pattern)
        if hasattr(p, "url_patterns"):
            walk(p.url_patterns, s)
        else:
            print(s)


walk(get_resolver().url_patterns)
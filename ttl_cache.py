"""
Minimal cache i processminnet med en tidsgräns (TTL) - inte en riktig
cache-server, bara till för att slippa slå upp EXAKT samma sak igen inom
loppet av någon minut (t.ex. byta betygsskala för samma aktie, klicka på
samma "senast sökta"-rad igen, eller backa och skriva om samma sökord).

Appen körs med en enda gunicorn-worker utan trådar (se render.yaml) så
ingen låsning behövs för trådsäkerhet här.

Ett MISSLYCKAT anrop (tomt dict/lista/None) cachas ALDRIG - bara riktiga
träffar. Annars skulle ett tillfälligt nätverksfel mot Yahoo/proxyn kunna
göra att en aktie "inte hittas" i upp till hela TTL-tiden, även efter att
felet försvunnit - det vore sämre än ingen cache alls.
"""

import time
from collections import OrderedDict


def ttl_cache(ttl_seconds: float, max_entries: int = 200, is_success=bool):
    """`is_success` avgör om ett resultat räknas som en riktig träff värd
    att cacha. Standard är bara "sant" (icke-tomt dict/lista/sträng) - men
    t.ex. get_chart_data returnerar ALLTID ett icke-tomt dict, även vid fel
    (`{"points": [], "currency": ""}`), så ge då en egen `is_success` som
    faktiskt kollar innehållet - annars skulle ett misslyckat anrop cachas
    som om det vore en giltig träff."""

    def decorator(func):
        cache = OrderedDict()

        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()

            cached = cache.get(key)
            if cached is not None:
                cached_at, value = cached
                if now - cached_at < ttl_seconds:
                    cache.move_to_end(key)
                    return value

            result = func(*args, **kwargs)
            if is_success(result):
                cache[key] = (now, result)
                cache.move_to_end(key)
                while len(cache) > max_entries:
                    cache.popitem(last=False)
            return result

        wrapper.cache_clear = cache.clear
        return wrapper

    return decorator

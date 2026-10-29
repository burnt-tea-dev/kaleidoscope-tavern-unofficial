# Tavern 0.6.191

Restore the shared render controller used by DimensionsWine and Sculk liquid visuals. It forwards each entity’s default geometry, material and still texture, with the established 0.85 alpha. This restores the host contract; it does not by itself verify rendered client behavior.

Paired family source: Grilling 2.8.195, canonical commit `44dde213ef010b95e846510d03c3a683e518a9d7`.

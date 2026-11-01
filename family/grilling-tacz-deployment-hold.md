# Retain the installed Grilling pair for the reviewed TACZ adapter

The reviewed TACZ local compatibility output 1.0.20004 requires exactly Grilling 2.8.206. Retain the complete currently installed 2.8.206 pair while enabling that adapter and its exact IE compatibility pair. The source commit and both trees are declared in upstream.lock.json; assembly must prove byte equality with the installed pair. This hold permits no downgrade, replacement or partial pack.

Canonical 2.8.207 adds package-level license and attribution notices with a fresh release identity. It remains intact on its main branch. Remove this hold when the TACZ/IE adapter has a reviewed dependency identity for the newer pair and the complete family passes its saved-world and native gates. Client rendering and sound acceptance remain separate; this declaration does not claim them.

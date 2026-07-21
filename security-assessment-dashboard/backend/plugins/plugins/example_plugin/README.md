# Example Plugin

An internal reference plugin. It exists only to verify the plugin
framework — discovery, manifest/structure/interface validation, dynamic
loading, and registration — end to end.

It is **not** a real security tool integration:

- `check_installation()` always returns `True` (it declares no
  `required_binaries`).
- `execute()` never starts a subprocess; it returns a fixed, canned
  `PluginRawOutput`.
- `parse()`/`normalize()` never produce a real finding.

Nothing in the application core imports this plugin directly — it is
loaded purely by the framework scanning `backend/plugins/plugins/` at
runtime, the same way any future real plugin (nmap, nikto, ffuf, ...)
will be.

See `backend/plugins/README.md` for the plugin authoring guide this
plugin follows.

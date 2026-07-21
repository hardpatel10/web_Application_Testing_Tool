backend/
    api/
    core/
    database/
    models/
    schemas/
    services/
    plugins/
    workers/
    reporting/
    utils/

frontend/
    src/
        pages/
        components/
        hooks/
        layouts/
        store/
        services/
        utils/
        types/

docs/
    LINUX_TOOL_INSTALLATION.md   # Linux install instructions per integrated tool

plugins/

reports/

tests/

scripts/                        # misc dev scripts (Windows-only, pre-existing)

Run scripts (repo root / backend/ / frontend/):
    run_backend.ps1, run_backend.bat    # Windows dev launchers (dev machine only)
    run_frontend.ps1, run_frontend.bat
    run_all.ps1, run_all.bat
    run_backend.sh, run_frontend.sh, run_all.sh   # Linux launchers -- the ones that matter for the actual runtime

---

Runtime Platform: Linux ONLY. Development Environment: Windows (development only, via Claude Code). See `.claude/CLAUDE.md`.
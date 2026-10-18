"""Product availability and workspace grants are separate, server-owned gates."""
from fastapi import HTTPException

# Future products cannot be activated by changing a commercial grant alone.
AVAILABLE_DDAS = frozenset({"logistics"})


def enabled_ddas(identity, workspace_id):
    return frozenset(row["dda_id"] for row in identity.get("ddas", [])
                     if row.get("workspace_id") == workspace_id
                     and row.get("status") == "enabled"
                     and row.get("dda_id") in AVAILABLE_DDAS)


def require_dda(ctx, dda_id):
    if dda_id not in ctx.enabled_ddas:
        raise HTTPException(403, "DDA Logística no está habilitado en este workspace.",
                            headers={"X-Dation-Entitlement": "disabled"})


def logistics_api(path):
    # All current business endpoints belong to Logistics. Platform identity,
    # Home and administrator diagnostics remain accessible without a DDA grant.
    return path.startswith("/api/") and not path.startswith(("/api/platform/", "/api/system/"))

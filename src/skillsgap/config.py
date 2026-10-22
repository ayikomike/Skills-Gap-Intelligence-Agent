"""Load configuration. Secrets/contact come from the environment, never the repo."""
import os
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path=None):
    path = Path(path) if path else ROOT / "config" / "sources.yaml"
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    cfg["_root"] = str(ROOT)
    return cfg


def user_agent(cfg):
    """Honest user agent: project name, project URL and a contact address."""
    p = cfg["project"]
    contact = os.environ.get(p["contact_env"], "contact-not-set")
    return f"{p['user_agent_name']} (+{p['project_url']}; {contact})"

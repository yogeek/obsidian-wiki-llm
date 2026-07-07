"""
Canonical tag taxonomy and legacy-tag mapping for the Notion tech-watch
database curation (see docs/superpowers/specs/2026-07-07-notion-tag-curation-design.md).
"""

CANONICAL_TAGS = [
    "Kubernetes", "Ingress-Mesh", "AWS", "Cloud", "IaC", "Terraform",
    "Crossplane", "CICD-GitOps", "Observabilité", "Sécurité", "Réseau",
    "IA-LLM", "Agents-IA", "MCP", "CLI-Terminal", "DevEx", "Productivité",
    "Learning", "SRE-Ops", "FinOps", "Data-DB", "Serverless", "SSH",
    "Divers",
]

# Legacy tag name (exact casing as stored in Notion today) -> list of
# canonical tags it maps to. Every one of the 155 tags currently in the
# `tag` multi_select property must appear here exactly once as a key.
TAG_MAP = {
    # --- Kubernetes ---
    "K8S": ["Kubernetes"],
    "docker": ["Kubernetes"],
    "Karpenter": ["Kubernetes"],
    "Scaling": ["Kubernetes"],
    "multitenancy": ["Kubernetes"],
    "Kind": ["Kubernetes"],
    "OCI": ["Kubernetes"],
    "Operator": ["Kubernetes"],
    "Scheduling": ["Kubernetes"],
    "Stateful": ["Kubernetes"],
    "Job": ["Kubernetes"],
    "fleet": ["Kubernetes"],
    "Sveltos": ["Kubernetes"],
    "Microservices": ["Kubernetes"],
    "registry": ["Kubernetes"],
    "Kyverno": ["Kubernetes"],
    "Policies": ["Kubernetes"],
    "eks": ["Kubernetes", "AWS"],

    # --- Ingress-Mesh ---
    "Cilium": ["Ingress-Mesh"],
    "Istio": ["Ingress-Mesh"],
    "Traefik": ["Ingress-Mesh"],
    "Nginx": ["Ingress-Mesh"],
    "GatewayAPI": ["Ingress-Mesh"],
    "Mesh": ["Ingress-Mesh"],
    "apigw": ["Ingress-Mesh"],

    # --- AWS ---
    "aws": ["AWS"],
    "s3": ["AWS"],
    "storage": ["AWS"],
    "IAM": ["AWS", "Sécurité"],

    # --- Cloud ---
    "cloud": ["Cloud"],
    "Platform": ["Cloud"],
    "IDP": ["Cloud"],
    "Paas": ["Cloud"],

    # --- IaC / Terraform / Crossplane ---
    "IaC": ["IaC"],
    "config": ["IaC"],
    "nix": ["IaC"],
    "terraform": ["Terraform", "IaC"],
    "Crossplane": ["Crossplane", "IaC"],

    # --- CICD-GitOps ---
    "gitops": ["CICD-GitOps"],
    "CICD": ["CICD-GitOps"],
    "Git": ["CICD-GitOps"],
    "Github": ["CICD-GitOps"],
    "Argocd": ["CICD-GitOps"],
    "Automation": ["CICD-GitOps"],
    "Artifact": ["CICD-GitOps"],
    "Build": ["CICD-GitOps"],
    "featureflag": ["CICD-GitOps"],

    # --- Observabilité ---
    "Dashboard": ["Observabilité"],
    "Observability": ["Observabilité"],
    "Monitoring": ["Observabilité"],
    "debug": ["Observabilité"],
    "log": ["Observabilité"],
    "Otel": ["Observabilité"],
    "datadog": ["Observabilité"],
    "Jaeger": ["Observabilité"],

    # --- Sécurité ---
    "security": ["Sécurité"],
    "Auth": ["Sécurité"],
    "hacking": ["Sécurité"],
    "secret": ["Sécurité"],
    "Oauth": ["Sécurité"],
    "ldap": ["Sécurité"],
    "oicd": ["Sécurité"],
    "passkey": ["Sécurité"],
    "cert": ["Sécurité"],
    "vault": ["Sécurité"],
    "RBAC": ["Sécurité", "Kubernetes"],

    # --- Réseau ---
    "Network": ["Réseau"],
    "ebpf": ["Réseau"],
    "grpc": ["Réseau"],
    "http": ["Réseau"],
    "Dns": ["Réseau"],
    "Kernel": ["Réseau"],

    # --- IA-LLM ---
    "IA": ["IA-LLM"],
    "GPT": ["IA-LLM"],
    "LLM": ["IA-LLM"],
    "AI": ["IA-LLM"],
    "Prediction": ["IA-LLM"],
    "Voice": ["IA-LLM"],
    "STT": ["IA-LLM"],
    "Speech": ["IA-LLM"],
    "Claude": ["IA-LLM"],
    "Notebook": ["IA-LLM"],

    # --- Agents-IA ---
    "Agent": ["Agents-IA"],
    "Skills": ["Agents-IA"],
    "Opencode": ["Agents-IA"],

    # --- MCP ---
    "MCP": ["MCP"],

    # --- CLI-Terminal ---
    "CLI": ["CLI-Terminal"],
    "Terminal": ["CLI-Terminal"],
    "tui": ["CLI-Terminal"],
    "Shell": ["CLI-Terminal"],
    "bash": ["CLI-Terminal"],

    # --- DevEx ---
    "dev": ["DevEx"],
    "ide": ["DevEx"],
    "Ux": ["DevEx"],
    "ui": ["DevEx"],
    "Web": ["DevEx"],
    "Testing": ["DevEx"],
    "benchmark": ["DevEx"],
    "Local": ["DevEx"],
    "Api": ["DevEx"],
    "Frontend": ["DevEx"],
    "Framework": ["DevEx"],
    "Browser": ["DevEx"],
    "Html": ["DevEx"],
    "Python": ["DevEx"],
    "Go": ["DevEx"],
    "wysiwyg": ["DevEx"],
    "Package": ["DevEx"],
    "Cleaning": ["DevEx"],
    "Image": ["DevEx"],
    "snippet": ["DevEx"],

    # --- Productivité ---
    "productivity": ["Productivité"],
    "Visualisation": ["Productivité"],
    "Doc": ["Productivité"],
    "search": ["Productivité"],
    "n8n": ["Productivité"],
    "Nocode": ["Productivité"],
    "map": ["Productivité"],
    "Diagram": ["Productivité"],
    "PDF": ["Productivité"],
    "Poll": ["Productivité"],
    "Feedback": ["Productivité"],

    # --- Learning ---
    "learning": ["Learning"],
    "Formation": ["Learning"],
    "Nutshell": ["Learning"],

    # --- SRE-Ops ---
    "ops": ["SRE-Ops"],
    "sre": ["SRE-Ops"],
    "Incident": ["SRE-Ops"],
    "Chaos": ["SRE-Ops"],
    "HA": ["SRE-Ops"],
    "Resilience": ["SRE-Ops"],
    "Cpu": ["SRE-Ops"],

    # --- FinOps ---
    "costing": ["FinOps"],

    # --- Data-DB ---
    "data": ["Data-DB"],
    "db": ["Data-DB"],
    "Queue": ["Data-DB"],
    "json": ["Data-DB"],
    "Sql": ["Data-DB"],

    # --- Serverless ---
    "Serverless": ["Serverless"],
    "lambda": ["Serverless", "AWS"],
    "Knative": ["Serverless", "Kubernetes"],
    "Wasm": ["Serverless"],
    "Webassembly": ["Serverless"],

    # --- SSH ---
    "ssh": ["SSH"],

    # --- Divers ---
    "opensource": ["Divers"],
    "Architecture": ["Divers"],
    "game": ["Divers"],
    "fun": ["Divers"],
    "Mac": ["Divers"],
    "Ios": ["Divers"],
    "Windows": ["Divers"],
    "Pro": ["Divers"],
    "Monolith": ["Divers"],
    "Blog": ["Divers"],
    "Uber": ["Divers"],
}


def canonicalize_tags(old_tags: list[str]) -> tuple[list[str], list[str]]:
    """Map legacy Notion tags to the canonical taxonomy.

    Returns (new_tags, unmapped): new_tags is the order-preserving,
    deduplicated union of canonical tags for all recognized old_tags.
    unmapped lists any old_tags not present in TAG_MAP verbatim, so
    nothing is silently dropped.
    """
    new_tags: list[str] = []
    unmapped: list[str] = []
    for tag in old_tags:
        targets = TAG_MAP.get(tag)
        if targets is None:
            unmapped.append(tag)
            continue
        for target in targets:
            if target not in new_tags:
                new_tags.append(target)
    return new_tags, unmapped


# Suggested tags for the 11 articles that currently have zero tags in
# Notion, derived from each article's title/URL (see plan Task 4). A
# value of None means no honest suggestion could be made from the
# available data — diff.py surfaces these as "needs_manual_review".
UNTAGGED_SUGGESTIONS: dict[str, list[str] | None] = {
    # Note: 3 entries originally in this dict have been removed because the
    # underlying Notion pages no longer exist as of 2026-07-07:
    #   - "369083fc-7c60-81b9-b010-cdb68da0faeb" (Dozzle - simple container
    #     logger): archived as a duplicate of "369083fc-7c60-81b6-..." which
    #     already carries the correct tags.
    #   - "1a9083fc-7c60-819e-b90d-cbe9121b25c3" (securing-the-kubernetes-host
    #     -operating-system, empty title): archived as a duplicate of
    #     "1a9083fc-7c60-81d2-..." which already carries the correct tags.
    #   - "173083fc-7c60-8135-ab9c-dd25ca007d76" ("A story from Lili Wan on
    #     Medium"): deleted directly in Notion by the database owner.
    "2f2083fc-7c60-815a-98b9-ea57b00252fb": ["Agents-IA"],  # Vibe Kanban - Orchestrate AI Coding Agents
    "293083fc-7c60-8181-aa27-fd64bcace747": ["Kubernetes", "Ingress-Mesh"],  # K8SGB - a global kubernetes loadbalancer
    "1a2083fc-7c60-8168-bbc3-eaca6aa26ed8": ["Kubernetes", "CICD-GitOps"],  # Testkube as a Quality Gate with Keptn
    "133083fc-7c60-8158-adce-f49fbc33fd29": ["Kubernetes", "Observabilité"],  # Kexa - requests limits k8s tool and dashboard
    "132083fc-7c60-8140-9c06-df9c63585c3b": ["Productivité"],  # Screenity - screen capture tool
    "bb0480c4-a13f-433c-8f1e-b883bffa6b24": ["Kubernetes"],  # Sleepcycles k8s operator
    "3222ebac-f2cd-4021-b14b-03650b5e9077": ["CICD-GitOps", "Kubernetes"],  # GitOps bridge
    "2390efb6-871f-43ab-bf36-e573c3c17e40": None,  # no title, no URL — empty row, insufficient info
}

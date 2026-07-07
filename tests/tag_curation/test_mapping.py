import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.tag_curation.mapping import CANONICAL_TAGS, TAG_MAP, canonicalize_tags

# The 155 legacy tag names exactly as they appear in the Notion `tag`
# multi_select property today (spec §4 source list).
ALL_155_SOURCE_TAGS = [
    "K8S", "IA", "productivity", "cloud", "CLI", "learning", "aws", "dev",
    "Network", "GPT", "Terminal", "security", "IaC", "costing", "ops", "sre",
    "Dashboard", "LLM", "Observability", "tui", "Ux", "ide", "Visualisation",
    "docker", "debug", "terraform", "ui", "Monitoring", "Agent", "gitops",
    "Scaling", "data", "Doc", "Git", "log", "ssh", "ebpf", "Web", "Auth",
    "db", "MCP", "opensource", "hacking", "Architecture", "s3", "Otel",
    "CICD", "AI", "Local", "config", "registry", "Cilium", "IAM", "Platform",
    "Testing", "IDP", "storage", "benchmark", "Karpenter", "secret",
    "Crossplane", "search", "Github", "n8n", "Api", "Frontend", "Argocd",
    "Nocode", "eks", "Queue", "map", "Automation", "PDF", "Cleaning",
    "Oauth", "Kind", "json", "OCI", "Diagram", "Istio", "grpc", "http",
    "Traefik", "Serverless", "lambda", "Cpu", "Shell", "Paas",
    "multitenancy", "Microservices", "nix", "game", "Browser", "Prediction",
    "ldap", "Voice", "STT", "oicd", "passkey", "Kyverno", "Policies",
    "Incident", "Skills", "Claude", "Opencode", "Framework", "Notebook",
    "Pro", "Nginx", "GatewayAPI", "Poll", "Feedback", "Mac", "Ios",
    "Windows", "Sql", "Image", "fun", "Knative", "datadog", "Speech", "Dns",
    "Operator", "Html", "Scheduling", "Python", "Package", "Kernel",
    "Artifact", "Build", "Chaos", "cert", "Nutshell", "bash", "HA",
    "Resilience", "Monolith", "wysiwyg", "Go", "Mesh", "Blog", "Stateful",
    "Uber", "Job", "Wasm", "Webassembly", "RBAC", "Jaeger", "fleet",
    "Sveltos", "Formation", "featureflag", "vault", "snippet", "apigw",
]


def test_canonical_tags_has_24_entries():
    assert len(CANONICAL_TAGS) == 24
    assert len(set(CANONICAL_TAGS)) == 24  # no duplicates


def test_all_155_source_tags_are_covered():
    assert len(ALL_155_SOURCE_TAGS) == 155
    missing = [t for t in ALL_155_SOURCE_TAGS if t not in TAG_MAP]
    assert missing == [], f"Uncovered legacy tags: {missing}"


def test_every_tag_map_value_is_canonical():
    for source, targets in TAG_MAP.items():
        for target in targets:
            assert target in CANONICAL_TAGS, (
                f"TAG_MAP[{source!r}] contains non-canonical tag {target!r}"
            )


def test_simple_single_mapping():
    new_tags, unmapped = canonicalize_tags(["K8S"])
    assert new_tags == ["Kubernetes"]
    assert unmapped == []


def test_dual_canonical_mapping():
    new_tags, unmapped = canonicalize_tags(["terraform"])
    assert new_tags == ["terraform", "IaC"]
    assert unmapped == []


def test_cross_domain_mapping():
    new_tags, unmapped = canonicalize_tags(["eks"])
    assert new_tags == ["Kubernetes", "aws"]
    assert unmapped == []


def test_dedup_union_across_multiple_old_tags():
    # K8S -> Kubernetes, docker -> Kubernetes: must not duplicate
    new_tags, unmapped = canonicalize_tags(["K8S", "docker"])
    assert new_tags == ["Kubernetes"]
    assert unmapped == []


def test_order_preserving_union():
    # IaC first, then terraform (adds terraform, IaC already present)
    new_tags, unmapped = canonicalize_tags(["IaC", "terraform"])
    assert new_tags == ["IaC", "terraform"]


def test_unmapped_tag_is_reported_not_dropped():
    new_tags, unmapped = canonicalize_tags(["K8S", "TotallyUnknownTag"])
    assert new_tags == ["Kubernetes"]
    assert unmapped == ["TotallyUnknownTag"]


def test_empty_input():
    new_tags, unmapped = canonicalize_tags([])
    assert new_tags == []
    assert unmapped == []


from scripts.tag_curation.mapping import UNTAGGED_SUGGESTIONS


def test_untagged_suggestions_has_8_entries():
    # Originally 11; 3 removed because the underlying Notion pages no
    # longer exist (2 archived as duplicates, 1 deleted by the owner).
    assert len(UNTAGGED_SUGGESTIONS) == 8


def test_untagged_suggestions_values_are_canonical_or_none():
    for page_id, tags in UNTAGGED_SUGGESTIONS.items():
        if tags is None:
            continue
        for tag in tags:
            assert tag in CANONICAL_TAGS, (
                f"UNTAGGED_SUGGESTIONS[{page_id!r}] has non-canonical tag {tag!r}"
            )


def test_untagged_suggestions_has_exactly_one_manual_review_case():
    manual = [pid for pid, tags in UNTAGGED_SUGGESTIONS.items() if tags is None]
    assert len(manual) == 1

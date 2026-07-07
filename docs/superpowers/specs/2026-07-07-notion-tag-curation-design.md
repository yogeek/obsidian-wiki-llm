# Design — Curation des tags de la base Notion de veille

Date : 2026-07-07
Projet : obsidian-wiki-llm
Auteur : Guillaume + Claude Code

## 1. Contexte et problème

La base Notion de veille techno (292 articles, propriété `tag` de type `multi_select`)
est alimentée manuellement via le plugin Chrome « Save to Notion » (PC) et l'export
mobile. Les tags se sont accumulés sans contrôle : **155 tags distincts pour 292
articles**, dont **63 utilisés une seule fois**, avec de nombreux synonymes et
variations de casse (`IA`/`AI`/`GPT`/`LLM`, `K8S`/`kubernetes`, `CICD`/`gitops`…).
Résultat : impossible de filtrer/présenter proprement, et la saisie future reste
polluée par un menu déroulant de 155 options.

Décision produit (validée) : appliquer une **taxonomie plate de 24 tags canoniques**
directement **dans Notion (source de vérité)**, pour que les futures synchronisations
ET l'usage quotidien de « Save to Notion » en bénéficient.

## 2. Objectifs et périmètre

### Inclus
- Définir 24 tags canoniques (vocabulaire fermé).
- Remapper les tags des ~290 articles selon une table 155→24 déterministe.
- Tagger à la main les 11 articles actuellement sans tag (depuis titre/URL).
- Nettoyer la propriété `tag` de Notion : retirer les ~131 options obsolètes pour ne
  garder que les 24 canoniques dans le menu déroulant.
- Re-synchroniser le vault Obsidian pour refléter les tags propres.

### Exclus (lots séparés, hors de ce design)
- Le statut `État` (13 articles sans statut, valeurs à normaliser) — lot distinct.
- Les résumés / descriptions et l'enrichissement LLM (clé Anthropic à renouveler).
- La réorganisation structurelle des pages Notion.
- La phase « second cerveau » au format OKF.

## 3. Taxonomie cible — 24 tags canoniques

| # | Tag canonique | Définition courte |
|---|---|---|
| 1 | Kubernetes | Orchestration de conteneurs, runtime, workloads, cluster mgmt |
| 2 | Ingress-Mesh | Ingress controllers, service mesh, API gateway (couche réseau K8s) |
| 3 | AWS | Services et écosystème Amazon Web Services |
| 4 | Cloud | Cloud générique, platform engineering, PaaS/IDP |
| 5 | IaC | Infrastructure as Code (générique) |
| 6 | Terraform | Spécifique Terraform / OpenTofu |
| 7 | Crossplane | Spécifique Crossplane |
| 8 | CICD-GitOps | Intégration/déploiement continu, GitOps, Git, automatisation de build |
| 9 | Observabilité | Monitoring, logs, traces, dashboards, debug |
| 10 | Sécurité | AuthN/Z, secrets, IAM, hacking, certificats, policies de sécurité |
| 11 | Réseau | Networking, DNS, protocoles (HTTP/gRPC), eBPF |
| 12 | IA-LLM | Intelligence artificielle, LLM, GPT, voix/speech |
| 13 | Agents-IA | Agents autonomes, coding agents, skills, MCP clients |
| 14 | MCP | Model Context Protocol |
| 15 | CLI-Terminal | Outils ligne de commande, TUI, shell |
| 16 | DevEx | Expérience développeur : IDE, tests, frontend, API, langages, outils dev |
| 17 | Productivité | Docs, diagrammes, recherche, no-code, automatisation perso |
| 18 | Learning | Formation, tutoriels, contenus pédagogiques |
| 19 | SRE-Ops | Fiabilité, incidents, résilience, HA, chaos, performance |
| 20 | FinOps | Coûts, optimisation de la dépense cloud |
| 21 | Data-DB | Bases de données, SQL, files/queues, formats de données |
| 22 | Serverless | Fonctions, lambda, Knative, WebAssembly |
| 23 | SSH | Accès et tunnels SSH |
| 24 | Divers | Hors-sujet récurrent, blogs d'ingénierie, OS, fun, singletons non classables |

### Règle d'attribution
Le nouveau jeu de tags d'un article = **union des canoniques** de chacun de ses
anciens tags (dédupliquée). Un article peut porter plusieurs tags (multi_select).
Si l'union dépasse 5 tags, l'article est signalé dans le dry-run pour arbitrage manuel
(éviter le bruit). La recherche full-text native de Notion reste le complément pour la
granularité fine (ex. retrouver « terraboard »).

## 4. Table de mapping complète 155 → 24

Format : `ancien_tag (occurrences) → canonique[s]`

### Kubernetes et voisins
- K8S (113) → Kubernetes
- docker (11) → Kubernetes
- Karpenter (3) → Kubernetes
- Scaling (8) → Kubernetes
- multitenancy (2) → Kubernetes
- Kind (2) → Kubernetes
- OCI (2) → Kubernetes
- Operator (1) → Kubernetes
- Scheduling (1) → Kubernetes
- Stateful (1) → Kubernetes
- Job (1) → Kubernetes
- fleet (1) → Kubernetes
- Sveltos (1) → Kubernetes
- Microservices (2) → Kubernetes
- registry (4) → Kubernetes
- Kyverno (1) → Kubernetes
- Policies (1) → Kubernetes
- eks (3) → Kubernetes + AWS

### Ingress-Mesh
- Cilium (4) → Ingress-Mesh
- Istio (2) → Ingress-Mesh
- Traefik (2) → Ingress-Mesh
- Nginx (1) → Ingress-Mesh
- GatewayAPI (1) → Ingress-Mesh
- Mesh (1) → Ingress-Mesh
- apigw (1) → Ingress-Mesh

### AWS
- aws (45) → AWS
- s3 (5) → AWS
- storage (4) → AWS
- IAM (4) → AWS + Sécurité

### Cloud
- cloud (58) → Cloud
- Platform (4) → Cloud
- IDP (4) → Cloud
- Paas (2) → Cloud

### IaC / Terraform / Crossplane
- IaC (22) → IaC
- config (4) → IaC
- nix (2) → IaC
- terraform (11) → Terraform + IaC
- Crossplane (3) → Crossplane + IaC

### CICD-GitOps
- gitops (9) → CICD-GitOps
- CICD (5) → CICD-GitOps
- Git (7) → CICD-GitOps
- Github (3) → CICD-GitOps
- Argocd (3) → CICD-GitOps
- Automation (2) → CICD-GitOps
- Artifact (1) → CICD-GitOps
- Build (1) → CICD-GitOps
- featureflag (1) → CICD-GitOps

### Observabilité
- Dashboard (18) → Observabilité
- Observability (15) → Observabilité
- Monitoring (10) → Observabilité
- debug (11) → Observabilité
- log (7) → Observabilité
- Otel (5) → Observabilité
- datadog (1) → Observabilité
- Jaeger (1) → Observabilité

### Sécurité
- security (22) → Sécurité
- Auth (6) → Sécurité
- hacking (5) → Sécurité
- secret (3) → Sécurité
- Oauth (2) → Sécurité
- ldap (1) → Sécurité
- oicd (1) → Sécurité
- passkey (1) → Sécurité
- cert (1) → Sécurité
- vault (1) → Sécurité
- RBAC (1) → Sécurité + Kubernetes

### Réseau
- Network (32) → Réseau
- ebpf (7) → Réseau
- grpc (2) → Réseau
- http (2) → Réseau
- Dns (1) → Réseau
- Kernel (1) → Réseau

### IA-LLM
- IA (62) → IA-LLM
- GPT (29) → IA-LLM
- LLM (17) → IA-LLM
- AI (4) → IA-LLM
- Prediction (1) → IA-LLM
- Voice (1) → IA-LLM
- STT (1) → IA-LLM
- Speech (1) → IA-LLM
- Claude (1) → IA-LLM
- Notebook (1) → IA-LLM

### Agents-IA
- Agent (9) → Agents-IA
- Skills (1) → Agents-IA
- Opencode (1) → Agents-IA

### MCP
- MCP (6) → MCP

### CLI-Terminal
- CLI (55) → CLI-Terminal
- Terminal (24) → CLI-Terminal
- tui (14) → CLI-Terminal
- Shell (2) → CLI-Terminal
- bash (1) → CLI-Terminal

### DevEx
- dev (38) → DevEx
- ide (13) → DevEx
- Ux (13) → DevEx
- ui (11) → DevEx
- Web (6) → DevEx
- Testing (4) → DevEx
- benchmark (4) → DevEx
- Local (4) → DevEx
- Api (3) → DevEx
- Frontend (3) → DevEx
- Framework (1) → DevEx
- Browser (1) → DevEx
- Html (1) → DevEx
- Python (1) → DevEx
- Go (1) → DevEx
- wysiwyg (1) → DevEx
- Package (1) → DevEx
- Cleaning (2) → DevEx
- Image (1) → DevEx
- snippet (1) → DevEx

### Productivité
- productivity (60) → Productivité
- Visualisation (12) → Productivité
- Doc (8) → Productivité
- search (3) → Productivité
- n8n (3) → Productivité
- Nocode (3) → Productivité
- map (3) → Productivité
- Diagram (2) → Productivité
- PDF (2) → Productivité
- Poll (1) → Productivité
- Feedback (1) → Productivité

### Learning
- learning (53) → Learning
- Formation (1) → Learning
- Nutshell (1) → Learning

### SRE-Ops
- ops (21) → SRE-Ops
- sre (20) → SRE-Ops
- Incident (1) → SRE-Ops
- Chaos (1) → SRE-Ops
- HA (1) → SRE-Ops
- Resilience (1) → SRE-Ops
- Cpu (2) → SRE-Ops

### FinOps
- costing (21) → FinOps

### Data-DB
- data (8) → Data-DB
- db (6) → Data-DB
- Queue (3) → Data-DB
- json (2) → Data-DB
- Sql (1) → Data-DB

### Serverless
- Serverless (2) → Serverless
- lambda (2) → Serverless + AWS
- Knative (1) → Serverless + Kubernetes
- Wasm (1) → Serverless
- Webassembly (1) → Serverless

### SSH
- ssh (7) → SSH

### Divers
- opensource (5) → Divers
- Architecture (5) → Divers
- game (1) → Divers
- fun (1) → Divers
- Mac (1) → Divers
- Ios (1) → Divers
- Windows (1) → Divers
- Pro (1) → Divers
- Monolith (1) → Divers
- Blog (1) → Divers
- Uber (1) → Divers

Total : 155 tags source couverts (aucun orphelin).

## 5. Traitement des articles sans tag

11 articles n'ont aucun tag côté Notion. Étape dédiée dans le dry-run : pour chacun,
proposer 1 à 3 tags canoniques déduits du **titre + URL**. Ces propositions sont
présentées dans l'aperçu et validées avant écriture, comme le reste.

## 6. Flux de write-back sécurisé

Aucune écriture Notion n'a lieu avant validation explicite de l'aperçu.

1. **Backup** — Export JSON horodaté de l'état actuel de chaque page :
   `{page_id, titre, tags_actuels}` → `backups/notion-tags-YYYYMMDD-HHMMSS.json`.
   Permet un rollback intégral.
2. **Génération de l'aperçu (dry-run)** — Pour chaque article, calculer le nouveau jeu
   de tags via la table §4 (+ §5 pour les non-taggés). Produire un diff lisible
   `previews/tag-diff-YYYYMMDD-HHMMSS.md` : `titre | tags_actuels → tags_nouveaux`,
   avec section dédiée aux cas à arbitrer (union > 5 tags, non-taggés).
3. **Revue humaine** — Guillaume relit l'aperçu. Ajustements possibles sur la table ou
   des cas individuels. Rien n'est écrit tant que l'aperçu n'est pas approuvé.
4. **Application** — Pour chaque page : `PATCH /v1/pages/{id}` mettant à jour la
   propriété `tag` (multi_select) avec les valeurs canoniques. Rate-limit ~3 req/s,
   idempotent (rejouable), reprise sur erreur, journal des écritures.
5. **Nettoyage du menu** — `PATCH /v1/databases/{id}` sur la propriété `tag` pour ne
   conserver que les 24 options canoniques (retrait des options obsolètes).
   À vérifier : comportement de l'API Notion sur la suppression d'options de
   multi_select (voir §8, risque à confirmer).
6. **Re-sync du vault** — `POST /vaults/tech-watch/sync/notion` pour refléter les tags
   propres dans le second cerveau Obsidian.

## 7. Rollback

En cas de problème, rejouer le backup §6.1 : pour chaque `page_id`, réécrire
`tags_actuels`. Script symétrique de l'application.

## 8. Détails techniques et risques

- **Propriété concernée** : `tag` (type `multi_select`). Ne pas confondre avec `État`
  (select) ni `Nom` (title).
- **Auth** : token dans `.env` (`NOTION_API_KEY`, `ntn_…`), header
  `Notion-Version: 2022-06-28`. Connexion validée (lecture + écriture activées sur
  l'intégration « obsidian-llm-wiki »).
- **Risque 1 — suppression d'options multi_select** : l'API Notion peut refuser ou
  ignorer la suppression d'options encore référencées. Mitigation : n'exécuter §6.5
  qu'APRÈS §6.4 (plus aucune page ne référence les options obsolètes). Si l'API ne
  permet pas la suppression programmatique, documenter un nettoyage manuel dans l'UI.
- **Risque 2 — écrasement concurrent** : ne pas lancer la sync automatique (scheduler
  6h) pendant l'application. Arrêter/mettre en pause le backend le temps du write.
- **Risque 3 — casse des liens du vault** : les pages de tag-hub du vault seront
  régénérées à la re-sync ; les anciennes (155) seront remplacées par 24. Acceptable.

## 9. Vérification (definition of done)

- Après application, requête Notion : le nombre de valeurs distinctes dans `tag` ≤ 24.
- 0 article sans tag (les 11 traités).
- Backup présent et rollback testé sur 1 page témoin.
- Vault re-synchronisé : `technology_watch/` reflète 24 tag-hubs (et non plus 155).

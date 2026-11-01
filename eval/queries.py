
QUERIES = [
        "Generate a compose file for Gitea with PostgreSQL",
        "Does Immich have any recent CVEs?",
        "How do I set up NextCloud?",
        "What dependencies does VaultWarden need?",
        "What environment variables do I need for WireGuard?",
        "What are the resource requirements for Jellyfin vs Plex?",
        "I am looking for an open source media player that can play most videos or audios without requiring extra codecs.",
        "What are the main differences between Joplin and Obsidian?",
        "How can I configure SSO/OAuth for Authentik with my other self-hosted apps?",
        "How does the Sonarr/Radarr with Prowlarr and Jellyfin work? Where does someone source the media content?",
        "My NextCloud container keeps restarting, what could be the common causes for this?",
        "Are there any known vulnerabilities in the latest version of NextCloud?",
        "What security hardening steps should I take after deploying VaultWarden?",
        "I have the following message on my admin dashboard for VaultWarden, what does it mean and what steps should I take? message: “You are using a plain text ADMIN_TOKEN which is insecure. Please generate a secure Argon2 PHC string by using vaultwarden hash or argon2.”",
        "What are the best self-hosted alternatives for Google Photos?",
        "What are the differences between LinuxServer.io images and the official docker images?",
        "How should I back up the data on my NextCloud instance ? What back up strategy is best and should I run a cron job for it?",
        "What is LetsEncrypt used for?",
        "Could You walk me through how to set up VaultWarden? I need the complete walkthrough and docker-compose files. This includes setting up certificates for TLS. I already have a domain and configured the DNS.",
        "Set up Paperless-ngx with Redis and PostgreSQL behind a reverse proxy.",
]

# Same intent as QUERIES, reworded, index-aligned. Used by
# benchmark_semantic_cache.py --paraphrase to test whether the semantic cache
# hits on a rephrasing, not just on the identical string.
PARAPHRASED_QUERIES = [
        "Write me a docker-compose setup for Gitea backed by Postgres",
        "Have any CVEs been reported for Immich lately?",
        "What are the steps to install Nextcloud?",
        "Which dependencies are required to run Vaultwarden?",
        "Which env vars does WireGuard need to be configured?",
        "How do Jellyfin and Plex compare in hardware requirements?",
        "Is there an open-source media player that handles almost any video or audio format without installing extra codecs?",
        "How do Obsidian and Joplin differ?",
        "How do I set up Authentik as an SSO/OAuth provider for my other self-hosted services?",
        "How do Sonarr, Radarr, Prowlarr and Jellyfin fit together, and where does the media actually come from?",
        "Why might my Nextcloud container be stuck in a restart loop?",
        "Does the newest Nextcloud release have any known security vulnerabilities?",
        "Once Vaultwarden is deployed, how should I harden it?",
        "My Vaultwarden admin page warns: “You are using a plain text ADMIN_TOKEN which is insecure. Please generate a secure Argon2 PHC string by using vaultwarden hash or argon2.” What does this mean and how do I fix it?",
        "Which self-hosted apps are the best replacements for Google Photos?",
        "How do LinuxServer.io container images differ from the official Docker images?",
        "What's the best way to back up my Nextcloud data, and should I schedule it with cron?",
        "What does Let's Encrypt do?",
        "Give me a full walkthrough for deploying Vaultwarden, including docker-compose files and TLS certificates. My domain and DNS are already set up.",
        "How do I deploy Paperless-ngx with Redis and Postgres behind a reverse proxy?",
]

# In-domain questions that are NOT rewordings of anything in QUERIES. A
# semantic-cache hit on one of these is a false hit: the user would get the
# answer to a different question. Some share an app name with a QUERIES entry
# (Nextcloud, Vaultwarden, Jellyfin, Immich) but ask something else, which is
# the realistic way a cache serves the wrong answer.
UNRELATED_QUERIES = [
        "Generate a compose file for Nextcloud with MariaDB",
        "How do I enable hardware transcoding in Jellyfin with an Intel GPU?",
        "How do I import my Google Takeout photos into Immich?",
        "How do I add a second user to Vaultwarden and share a collection?",
        "How do I set up Pi-hole as the DNS server for my home network?",
        "What is the difference between Traefik and Nginx Proxy Manager?",
        "How do I configure Uptime Kuma to send alerts to Discord?",
        "How do I mount an NFS share inside a Docker container?",
        "What is the best way to update all my Docker containers automatically?",
        "How do I set up Home Assistant with Zigbee devices?",
        "How do I expose a self-hosted service to the internet without opening ports, using Cloudflare Tunnel?",
        "How much RAM does a Minecraft server need for ten players?",
        "How do I configure Grafana to read metrics from Prometheus?",
        "Generate a compose file for Gitea with SQLite",
        "Are there any known vulnerabilities in Jellyfin?",
        "How do I rotate Postgres passwords used by a docker-compose stack?",
        "What does a reverse proxy do?",
        "How do I restore a Nextcloud backup onto a new server?",
        "How do I set up Tailscale on my home server?",
        "What are the best self-hosted alternatives for Google Drive?",
]

# Extra Docker Compose generation queries. Prompt chaining is built only for
# compose generation, so strategies are also compared on this subset.
COMPOSE_QUERIES = [
        "Generate a docker-compose file for Immich with its machine-learning container, Redis and PostgreSQL.",
        "Write a compose file for Jellyfin with hardware transcoding on an Intel iGPU.",
        "Give me a docker-compose.yml for Nextcloud with MariaDB and Redis behind Traefik with Let's Encrypt.",
        "Create a compose stack for Authentik with its worker, PostgreSQL and Redis.",
        "Docker compose for Uptime Kuma, exposed only on localhost.",
        "Write a compose file for Home Assistant with a Mosquitto MQTT broker.",
        "Generate a compose file for Vaultwarden behind Caddy with automatic HTTPS.",
        "Compose file for a Prometheus, Grafana and node-exporter monitoring stack.",
        "Create a docker-compose for Gitea with a Gitea Actions runner.",
        "Give me a compose file for Pi-hole with Unbound as the upstream DNS resolver.",
]

# Every query the strategy eval runs, in order. The first 20 are QUERIES, so
# query_index values in older result files still line up.
ALL_QUERIES = QUERIES + COMPOSE_QUERIES
# Indexes into ALL_QUERIES of the compose-generation queries.
COMPOSE_INDEXES = [0, 18, 19] + list(range(len(QUERIES), len(ALL_QUERIES)))

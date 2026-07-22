# Completely Free Deployment

This deployment keeps the React frontend on Vercel Hobby and runs FastAPI,
PostgreSQL with pgvector, and Caddy on one Oracle Cloud Always Free ARM VM.

## Production Topology

```text
Browser
  -> Vercel Hobby: React static frontend
  -> DuckDNS hostname over HTTPS
  -> Caddy on Oracle Cloud
  -> FastAPI container
  -> PostgreSQL and pgvector container
```

Only ports `80` and `443` are public. PostgreSQL and FastAPI remain inside the
Docker network.

## 1. Create the Oracle VM

Create the VM in the Oracle account's home region.

- Image: Ubuntu 24.04 ARM64
- Shape: `VM.Standard.A1.Flex`
- OCPUs: `2`
- Memory: `12 GB`
- Boot volume: `100 GB`

Add ingress rules:

- TCP `22` from your own IP address
- TCP `80` from `0.0.0.0/0`
- TCP `443` from `0.0.0.0/0`
- UDP `443` from `0.0.0.0/0`

Do not expose ports `5432` or `8000`.

## 2. Install Docker

Connect to the VM:

```bash
ssh -i /path/to/private-key ubuntu@ORACLE_PUBLIC_IP
```

Install Docker and Git:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git
sudo usermod -aG docker "$USER"
exit
```

Reconnect so the Docker group change takes effect.

## 3. Clone and Configure the Project

```bash
git clone YOUR_GITHUB_REPOSITORY_URL WhichMovieItIs
cd WhichMovieItIs
cp deploy/oracle/oracle.env.example deploy/oracle/.env
nano deploy/oracle/.env
```

Replace every placeholder in `.env`. Use a long alphanumeric database password
so it can be safely placed in `DATABASE_URL` without URL encoding.

## 4. Configure DuckDNS

Create a free DuckDNS subdomain and point it at the Oracle VM public IP. Set the
same hostname in `BACKEND_HOSTNAME`:

```text
BACKEND_HOSTNAME=your-api-name.duckdns.org
```

Keep ports `80` and `443` open. Caddy obtains and renews the HTTPS certificate
automatically.

## 5. Start the Production Stack

Run from the repository root:

```bash
docker compose \
  --file deploy/oracle/docker-compose.yml \
  --env-file deploy/oracle/.env \
  up --detach --build
```

Inspect startup state and logs:

```bash
docker compose \
  --file deploy/oracle/docker-compose.yml \
  --env-file deploy/oracle/.env \
  ps

docker compose \
  --file deploy/oracle/docker-compose.yml \
  --env-file deploy/oracle/.env \
  logs --follow backend
```

The first backend startup downloads the embedding model into the persistent
`model_cache` volume, so it takes longer than later restarts.

## 6. Move the Local Database

Create a compressed dump on the local Windows computer:

```powershell
docker exec whichmovie-postgres pg_dump `
  -U postgres `
  -d whichmovie `
  -Fc `
  -f /tmp/whichmovie.dump

docker cp whichmovie-postgres:/tmp/whichmovie.dump .\whichmovie.dump
```

Copy it to Oracle:

```powershell
scp -i C:\path\to\private-key `
  .\whichmovie.dump `
  ubuntu@ORACLE_PUBLIC_IP:/home/ubuntu/whichmovie.dump
```

Restore it on Oracle:

```bash
cd ~/WhichMovieItIs
bash deploy/oracle/restore_database.sh /home/ubuntu/whichmovie.dump
```

## 7. Deploy the Frontend to Vercel

Import the GitHub repository into Vercel and configure:

- Root directory: `frontend`
- Framework: Vite
- Environment variable:
  - `VITE_API_BASE_URL=https://your-api-name.duckdns.org`

After Vercel gives the final frontend URL, update the Oracle `.env`:

```text
FRONTEND_ORIGINS=https://your-project.vercel.app
```

Restart the backend:

```bash
docker compose \
  --file deploy/oracle/docker-compose.yml \
  --env-file deploy/oracle/.env \
  up --detach
```

## 8. Verify Production

```bash
curl https://your-api-name.duckdns.org/health
curl https://your-api-name.duckdns.org/health/db
curl "https://your-api-name.duckdns.org/search?q=ship%20hits%20iceberg&limit=5"
```

Verify the browser application:

- Catalog loads
- Rough-plot search returns results
- Movie detail opens
- Posters load
- A missing exact title triggers the TMDB fallback

## 9. Configure GitHub Deployment

The workflow at `.github/workflows/deploy-oracle.yml` is manual by design. Add
these GitHub environment secrets under the `production` environment:

- `ORACLE_HOST`
- `ORACLE_USER`
- `ORACLE_SSH_KEY`
- `ORACLE_APP_DIR`

Run **Deploy backend to Oracle Cloud** from the GitHub Actions page after a
tested change reaches `main`.

## 10. Back Up PostgreSQL

Create a backup manually:

```bash
bash deploy/oracle/backup_database.sh
```

When `OCI_BUCKET_NAME` is configured and the OCI CLI is authenticated, the
script also uploads the compressed dump to Oracle Object Storage. Schedule the
script with cron only after one manual backup and restore have both succeeded.

## Free-Tier Constraints

- Oracle can temporarily report no available ARM capacity.
- Oracle may reclaim idle Always Free compute instances.
- Vercel Hobby is restricted to personal, non-commercial projects.
- DuckDNS provides a free subdomain, not a paid-domain availability guarantee.
- The deployment remains free only while every Oracle resource stays marked
  Always Free eligible and Vercel usage stays inside Hobby limits.

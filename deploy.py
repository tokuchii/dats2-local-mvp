"""One-command production deploy: builds containers, starts services, initializes DB."""
import subprocess
import sys
import time


def run(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    print(f"\n> {cmd}")
    result = subprocess.run(cmd, shell=True)
    if check and result.returncode != 0:
        print(f"FAILED: {cmd}")
        sys.exit(1)
    return result


def main():
    print("=" * 60)
    print("  DATS 2.0 — Production Deploy")
    print("=" * 60)

    # Build
    run("docker compose build", check=True)

    # Start DB first
    run("docker compose up -d db", check=True)
    print("Waiting for PostgreSQL to be ready...")
    time.sleep(5)

    # Start app
    run("docker compose up -d app", check=True)
    print("Waiting for app to start...")
    time.sleep(5)

    # Verify health
    result = run("docker compose exec app python -c \"import urllib.request; r=urllib.request.urlopen('http://localhost:8000/health'); print(r.read().decode())\"", check=False)
    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("  DEPLOY COMPLETE")
        print("  App: http://localhost:8000")
        print("  DB:  localhost:5433")
        print("=" * 60)
    else:
        print("\nApp started but health check failed. Check logs:")
        print("  docker compose logs app")

    # Show logs
    print("\nTailing logs (Ctrl+C to stop)...")
    run("docker compose logs -f app", check=False)


if __name__ == "__main__":
    main()

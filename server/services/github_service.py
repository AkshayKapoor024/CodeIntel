import os
import subprocess
import shutil
import time
import httpx
from server.logger.logger import logging

class GitHubService:
    def __init__(self, token: str = None):
        self.token = token or os.getenv("GITHUB_TOKEN")

    def clone_repository(self, repo_url: str, branch: str, dest_path: str) -> str:
        """
        Clones a GitHub repository to a destination path and returns the latest commit hash.
        """
        logging.info(f"Cloning repository {repo_url} (branch: {branch}) to {dest_path}")
        if os.path.exists(dest_path):
            try:
                shutil.rmtree(dest_path, ignore_errors=True)
            except Exception as e:
                logging.warning(f"Could not clean up existing directory {dest_path}: {e}")

        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        # Build clone URL with token if available for private repos
        clone_url = repo_url
        if self.token and "github.com" in repo_url:
            clone_url = repo_url.replace("https://github.com/", f"https://x-access-token:{self.token}@github.com/")

        cmd = ["git", "clone", "--branch", branch, "--depth", "1", clone_url, dest_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            # Try default branch if specified branch fails
            logging.warning(f"Failed to clone branch {branch}. Trying default branch clone.")
            cmd = ["git", "clone", "--depth", "1", clone_url, dest_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Failed to clone repository: {result.stderr}")

        # Get commit hash
        commit_hash = self.get_commit_hash(dest_path)
        logging.info(f"Repository cloned. Commit hash: {commit_hash}")
        return commit_hash

    def get_commit_hash(self, repo_path: str) -> str:
        """Runs git rev-parse HEAD to get the commit hash."""
        cmd = ["git", "-C", repo_path, "rev-parse", "HEAD"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        return "unknown"

    def fetch_file_content_sync(self, repo_url: str, commit_hash: str, file_path: str) -> str:
        """
        Synchronously fetches the content of a file directly from GitHub using commit hash or raw URL.
        Supports public and private repos if GITHUB_TOKEN is configured.
        """
        parts = repo_url.replace("https://github.com/", "").strip("/").split("/")
        if len(parts) < 2:
            raise Exception("Invalid GitHub URL")
        owner = parts[0]
        repo = parts[1].split(".git")[0]

        ref = commit_hash if commit_hash and commit_hash != "unknown" else "HEAD"
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{file_path}"
        headers = {}
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        with httpx.Client(follow_redirects=True, timeout=15.0) as client:
            response = client.get(raw_url, headers=headers)
            if response.status_code == 200:
                return response.text
            
            # API fallback if raw URL returns 404
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={ref}"
            headers["Accept"] = "application/vnd.github.v3.raw"
            api_resp = client.get(api_url, headers=headers)
            if api_resp.status_code == 200:
                return api_resp.text
                
            raise Exception(f"Failed to fetch file {file_path} from GitHub (Status {response.status_code})")

    async def fetch_file_content(self, repo_url: str, commit_hash: str, file_path: str) -> str:
        """Async version of fetch_file_content."""
        return self.fetch_file_content_sync(repo_url, commit_hash, file_path)

import os
import git
from github import Github
from api.models import GitSyncLog, GitHubToken, User
from datetime import datetime

def sync_and_push(user_id):
    try:
        user = User.objects.get(id=user_id)
        github_token = GitHubToken.objects.get(user=user)
        local_repo_path = github_token.clone_path
        branch_name = github_token.branch_name
        repo_full_name = github_token.repository
        access_token = github_token.access_token

        if not local_repo_path or not os.path.exists(local_repo_path):
            raise Exception("Local repo path does not exist.")
        if not branch_name:
            raise Exception("No branch name assigned to user.")

        repo = git.Repo(local_repo_path)
        origin = repo.remotes.origin

        # 1. Checkout or create user branch
        if branch_name not in repo.heads:
            repo.git.checkout('main')
            repo.git.checkout('-b', branch_name)
        else:
            repo.git.checkout(branch_name)

        # 2. Add/commit local changes
        repo.git.add('--all')
        if repo.is_dirty():
            repo.git.commit('-m', f'Auto-commit by {user.email} at {datetime.now().isoformat()}')

        # 3. Pull latest main and rebase
        origin.fetch()
        try:
            repo.git.rebase('origin/main')
        except Exception as e:
            repo.git.rebase('--abort')
            GitSyncLog.objects.create(
                user=user,
                action='rebase',
                status='conflict',
                message=str(e),
            )
            return {'status': 'conflict', 'error': str(e)}

        # 4. Push user branch
        try:
            origin.push(branch_name)
        except Exception as e:
            GitSyncLog.objects.create(
                user=user,
                action='push',
                status='push_error',
                message=str(e),
            )
            return {'status': 'push_error', 'error': str(e)}

        # 5. Create/update PR via GitHub API
        g = Github(access_token)
        gh_repo = g.get_repo(repo_full_name)
        user_login = gh_repo.owner.login
        prs = gh_repo.get_pulls(state='open', head=f"{user_login}:{branch_name}")
        if prs.totalCount == 0:
            pr = gh_repo.create_pull(
                title=f"Auto PR from {user.email}",
                body="Automated PR for test case changes",
                head=branch_name,
                base="main"
            )
        else:
            pr = prs[0]

        # 6. Optionally auto-merge if no conflicts
        if pr.mergeable:
            pr.merge()

        # 7. Log success
        GitSyncLog.objects.create(
            user=user,
            action='sync_and_push',
            status='success',
            message='Sync, push, and PR successful',
            pr_url=pr.html_url
        )
        return {'status': 'success', 'pr_url': pr.html_url}

    except Exception as e:
        GitSyncLog.objects.create(
            user_id=user_id,
            action='sync_and_push',
            status='error',
            message=str(e),
        )
        return {'status': 'error', 'error': str(e)} 
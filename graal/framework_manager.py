"""
Framework Manager for self-update capabilities
Handles framework version management, updates, and testing
"""
import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import httpx
from pydantic import BaseModel, Field
from .migration_manager import MigrationManager

logger = logging.getLogger(__name__)


class FrameworkVersion(BaseModel):
    """Framework version information"""
    tag: str = Field(..., description="Git tag (e.g., 'v1.2.0')")
    version: str = Field(..., description="Semantic version (e.g., '1.2.0')")
    release_date: Optional[str] = Field(None, description="Release date")
    changelog: str = Field(default="", description="Version changelog")
    is_prerelease: bool = Field(default=False, description="Is this a pre-release?")


class UpdateResult(BaseModel):
    """Result of a framework update operation"""
    success: bool = Field(..., description="Was the update successful?")
    from_version: str = Field(..., description="Previous version")
    to_version: str = Field(..., description="New version")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    test_results: Optional[Dict[str, Any]] = Field(None, description="Test execution results")
    rollback_available: bool = Field(default=False, description="Can rollback to previous version?")
    error_message: Optional[str] = Field(None, description="Error message if update failed")
    
    # Migration-specific fields
    migration_applied: Optional[bool] = Field(None, description="Was code migration applied?")
    migration_changes: Optional[List[Dict[str, Any]]] = Field(None, description="List of migration changes applied")
    breaking_changes: Optional[List[str]] = Field(None, description="List of breaking changes in this update")
    migration_message: Optional[str] = Field(None, description="Migration status message")


class FrameworkManager:
    """
    Manages framework version updates and testing
    
    Capabilities:
    - Check available versions from GitHub
    - Update framework to specific version
    - Run tests after update
    - Rollback on failure
    - Clone agent for safe testing
    """
    
    def __init__(self, agent_config, repo_url: str = "https://api.github.com/repos/Holy-Bird-Animation-Studio/hg-agent-fwk"):
        self.agent_config = agent_config
        self.repo_url = repo_url
        self.github_api_url = repo_url
        self.github_repo_url = "https://github.com/Holy-Bird-Animation-Studio/hg-agent-fwk.git"
        self.agent_root = Path(os.getcwd())
        self.framework_lock_file = self.agent_root / "framework.lock"
        self.backup_dir = self.agent_root / ".framework_backups"
        
        # Migration manager for code updates
        self.migration_manager = MigrationManager(self.agent_root)
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(exist_ok=True)
    
    def get_current_version(self) -> str:
        """Get current framework version from framework.lock"""
        try:
            if self.framework_lock_file.exists():
                version = self.framework_lock_file.read_text().strip()
                return version.lstrip('v')  # Remove 'v' prefix if present
            return "1.0.0"  # Default fallback
        except Exception as e:
            logger.error(f"Error reading framework.lock: {e}")
            return "unknown"
    
    async def get_available_versions(self) -> List[FrameworkVersion]:
        """Get available framework versions from GitHub releases/tags"""
        try:
            async with httpx.AsyncClient() as client:
                # Get tags from GitHub API
                response = await client.get(f"{self.github_api_url}/tags", timeout=10.0)
                response.raise_for_status()
                
                tags_data = response.json()
                versions = []
                
                for tag in tags_data:
                    tag_name = tag["name"]
                    version_str = tag_name.lstrip('v')
                    
                    # Try to get release info for more details
                    release_info = await self._get_release_info(client, tag_name)
                    
                    versions.append(FrameworkVersion(
                        tag=tag_name,
                        version=version_str,
                        release_date=release_info.get("published_at"),
                        changelog=release_info.get("body", ""),
                        is_prerelease=release_info.get("prerelease", False)
                    ))
                
                # Sort by semantic version (newest first)
                versions.sort(key=lambda v: v.version, reverse=True)
                return versions
                
        except Exception as e:
            logger.error(f"Error fetching available versions: {e}")
            return []
    
    async def _get_release_info(self, client: httpx.AsyncClient, tag_name: str) -> Dict[str, Any]:
        """Get release information for a specific tag"""
        try:
            response = await client.get(f"{self.github_api_url}/releases/tags/{tag_name}", timeout=10.0)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"No release info for tag {tag_name}: {e}")
        return {}
    
    async def update_framework(self, target_version: str, run_tests: bool = True) -> UpdateResult:
        """
        Update framework to target version
        
        Args:
            target_version: Target version (e.g., 'v1.2.0' or '1.2.0')
            run_tests: Whether to run tests after update
            
        Returns:
            UpdateResult with success status and details
        """
        current_version = self.get_current_version()
        target_tag = target_version if target_version.startswith('v') else f'v{target_version}'
        target_clean = target_version.lstrip('v')
        
        logger.info(f"🔄 Starting framework update: {current_version} → {target_clean}")
        
        # Check if migration is needed
        migration_info = self.migration_manager.get_migration_info(current_version, target_clean)
        if migration_info["migration_available"] and migration_info["has_code_changes"]:
            logger.info(f"🔧 Migration required with {len(migration_info['migration_steps'])} code changes")
            logger.info(f"Breaking changes: {migration_info['breaking_changes']}")
        
        # Create backup before update
        backup_path = await self._create_backup(current_version)
        
        try:
            # Update requirements.txt to point to new version
            await self._update_requirements_file(target_tag)
            
            # Reinstall framework with new version
            await self._reinstall_framework()
            
            # Apply code migrations if needed
            migration_result = await self.migration_manager.apply_migration(current_version, target_clean)
            
            # Update framework.lock
            self.framework_lock_file.write_text(target_tag + "\n")
            
            test_results = None
            if run_tests:
                logger.info("🧪 Running tests after framework update...")
                test_results = await self._run_tests()
                
                if not test_results.get("success", False):
                    logger.error("❌ Tests failed after update, rolling back...")
                    await self._rollback_from_backup(backup_path)
                    return UpdateResult(
                        success=False,
                        from_version=current_version,
                        to_version=target_clean,
                        test_results=test_results,
                        rollback_available=True,
                        error_message="Tests failed after update, automatically rolled back"
                    )
            
            logger.info(f"✅ Framework updated successfully: {current_version} → {target_clean}")
            
            # Include migration results in response
            result = UpdateResult(
                success=True,
                from_version=current_version,
                to_version=target_clean,
                test_results=test_results,
                rollback_available=True
            )
            
            # Add migration info to result
            if migration_result:
                result_dict = result.dict()
                result_dict.update({
                    "migration_applied": migration_result.get("migration_required", False),
                    "migration_changes": migration_result.get("changes_applied", []),
                    "breaking_changes": migration_result.get("breaking_changes", []),
                    "migration_message": migration_result.get("message", "")
                })
                
                # Convert back to UpdateResult with additional fields
                return UpdateResult(**{k: v for k, v in result_dict.items() if k in UpdateResult.__fields__})
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Framework update failed: {e}")
            
            # Attempt rollback
            try:
                await self._rollback_from_backup(backup_path)
                rollback_available = True
            except Exception as rollback_error:
                logger.error(f"❌ Rollback also failed: {rollback_error}")
                rollback_available = False
            
            return UpdateResult(
                success=False,
                from_version=current_version,
                to_version=target_clean,
                rollback_available=rollback_available,
                error_message=str(e)
            )
    
    async def _create_backup(self, version: str) -> Path:
        """Create backup of current framework configuration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{version}_{timestamp}"
        backup_path.mkdir(exist_ok=True)
        
        # Backup key files
        files_to_backup = ["requirements.txt", "framework.lock"]
        for filename in files_to_backup:
            src = self.agent_root / filename
            if src.exists():
                shutil.copy2(src, backup_path / filename)
        
        logger.info(f"📦 Created backup at {backup_path}")
        return backup_path
    
    async def _update_requirements_file(self, target_tag: str):
        """Update requirements.txt to point to new framework version"""
        requirements_path = self.agent_root / "requirements.txt"
        
        if not requirements_path.exists():
            raise FileNotFoundError("requirements.txt not found")
        
        content = requirements_path.read_text()
        lines = content.split('\n')
        
        # Update the framework line
        updated_lines = []
        framework_updated = False
        
        for line in lines:
            if 'hg-agent-fwk.git' in line:
                # Replace with new version
                new_line = f"git+https://github.com/Holy-Bird-Animation-Studio/hg-agent-fwk.git@{target_tag}"
                updated_lines.append(new_line)
                framework_updated = True
                logger.info(f"📝 Updated framework line: {new_line}")
            else:
                updated_lines.append(line)
        
        if not framework_updated:
            raise ValueError("Framework line not found in requirements.txt")
        
        requirements_path.write_text('\n'.join(updated_lines))
    
    async def _reinstall_framework(self):
        """Reinstall framework from updated requirements.txt"""
        logger.info("📦 Reinstalling framework...")
        
        try:
            # Run pip install in subprocess
            process = await asyncio.create_subprocess_exec(
                "pip", "install", "--force-reinstall", "-r", "requirements.txt",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.agent_root
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown pip error"
                raise RuntimeError(f"pip install failed: {error_msg}")
            
            logger.info("✅ Framework reinstalled successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to reinstall framework: {e}")
            raise
    
    async def _run_tests(self) -> Dict[str, Any]:
        """Run tests and return results"""
        try:
            # Look for test command or files
            test_commands = [
                ["python", "-m", "pytest", "tests/", "-v"],
                ["python", "-m", "pytest", ".", "-v"],
                ["python", "test_agent.py"],
            ]
            
            for cmd in test_commands:
                if await self._command_exists(cmd[0]):
                    logger.info(f"🧪 Running tests: {' '.join(cmd)}")
                    
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=self.agent_root
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    return {
                        "success": process.returncode == 0,
                        "command": ' '.join(cmd),
                        "exit_code": process.returncode,
                        "stdout": stdout.decode(),
                        "stderr": stderr.decode(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
            
            # No test command found
            return {
                "success": True,  # Assume OK if no tests
                "message": "No test command found, skipping tests",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _command_exists(self, command: str) -> bool:
        """Check if a command exists"""
        try:
            process = await asyncio.create_subprocess_exec(
                "which", command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0
        except:
            return False
    
    async def _rollback_from_backup(self, backup_path: Path):
        """Rollback framework from backup"""
        logger.info(f"🔄 Rolling back from backup: {backup_path}")
        
        # Restore files from backup
        for backup_file in backup_path.iterdir():
            if backup_file.is_file():
                dest = self.agent_root / backup_file.name
                shutil.copy2(backup_file, dest)
                logger.info(f"📋 Restored {backup_file.name}")
        
        # Reinstall framework from restored requirements.txt
        await self._reinstall_framework()
        logger.info("✅ Rollback completed")
    
    async def create_test_clone(self, clone_name: Optional[str] = None) -> Path:
        """
        Create a test clone of the current agent for safe testing
        
        Returns:
            Path to the cloned agent directory
        """
        if not clone_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clone_name = f"{self.agent_config.slug}_test_{timestamp}"
        
        clone_path = self.agent_root.parent / clone_name
        
        # Copy entire agent directory
        shutil.copytree(self.agent_root, clone_path, ignore=shutil.ignore_patterns(
            '__pycache__', '*.pyc', '.pytest_cache', '.framework_backups', '*.log'
        ))
        
        logger.info(f"🔬 Created test clone: {clone_path}")
        return clone_path
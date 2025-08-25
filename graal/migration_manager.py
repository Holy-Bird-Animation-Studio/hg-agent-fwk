"""
Migration Manager for GRAAL Agent Framework
Handles automatic code migrations when upgrading framework versions
"""
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MigrationStep:
    """Single migration step"""
    name: str
    description: str
    file_pattern: str  # Glob pattern for files to modify
    search_pattern: str  # Regex pattern to find
    replace_pattern: str  # Replacement pattern
    required: bool = True  # If False, migration failure won't block update


@dataclass
class FrameworkMigration:
    """Complete migration between framework versions"""
    from_version: str
    to_version: str
    breaking_changes: List[str]
    migration_steps: List[MigrationStep]
    changelog: str = ""
    
    def is_compatible(self, current_version: str, target_version: str) -> bool:
        """Check if this migration applies to the version transition"""
        return (self.from_version == current_version and 
                self.to_version == target_version)


class MigrationManager:
    """
    Manages automatic code migrations for agent framework updates
    
    Capabilities:
    - Detect breaking changes between versions
    - Apply code transformations to agent files
    - Generate migration reports
    - Rollback failed migrations
    """
    
    def __init__(self, agent_root: Path):
        self.agent_root = Path(agent_root)
        self.migrations = self._load_migrations()
        self.backup_dir = self.agent_root / ".migration_backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def _load_migrations(self) -> List[FrameworkMigration]:
        """Load all available migrations"""
        return [
            # Migration v1.0.0 → v1.1.0
            FrameworkMigration(
                from_version="1.0.0",
                to_version="1.1.0", 
                breaking_changes=[
                    "Renamed BaseAgent.process() to BaseAgent.process_message()",
                    "Added required user_id parameter to process_message()",
                ],
                migration_steps=[
                    MigrationStep(
                        name="update_process_method",
                        description="Rename process() to process_message()",
                        file_pattern="app/main.py",
                        search_pattern=r"async def process\(",
                        replace_pattern="async def process_message("
                    ),
                    MigrationStep(
                        name="add_user_id_param",
                        description="Add user_id parameter to process_message()",
                        file_pattern="app/main.py", 
                        search_pattern=r"async def process_message\(\s*self,\s*message: str,\s*context: Dict\[str, Any\]\s*\)",
                        replace_pattern="async def process_message(self, message: str, context: Dict[str, Any], user_id: Optional[str] = None, conversation_id: Optional[str] = None)"
                    )
                ]
            ),
            
            # Migration v1.1.0 → v1.2.0
            FrameworkMigration(
                from_version="1.1.0",
                to_version="1.2.0",
                breaking_changes=[
                    "Framework self-update capabilities added",
                    "New endpoints /fwk/* available automatically",
                ],
                migration_steps=[
                    # No breaking changes for v1.2.0, just new features
                ],
                changelog="Added self-update system with /fwk/* endpoints. No code changes required for existing agents."
            ),
            
            # Migration v1.2.0 → v1.3.0 (future example)
            FrameworkMigration(
                from_version="1.2.0", 
                to_version="1.3.0",
                breaking_changes=[
                    "AgentConfig.port is now AgentConfig.server_port",
                    "New required field AgentConfig.agent_type",
                ],
                migration_steps=[
                    MigrationStep(
                        name="rename_port_config",
                        description="Rename port to server_port in AgentConfig",
                        file_pattern="app/main.py",
                        search_pattern=r"port=(\d+)",
                        replace_pattern="server_port=\\1"
                    ),
                    MigrationStep(
                        name="add_agent_type",
                        description="Add required agent_type field",
                        file_pattern="app/main.py",
                        search_pattern=r"(AgentConfig\([^)]+)\)",
                        replace_pattern="\\1,\n        agent_type=\"conversational\"\n    )"
                    )
                ]
            )
        ]
    
    def find_migration(self, current_version: str, target_version: str) -> Optional[FrameworkMigration]:
        """Find migration for version transition"""
        for migration in self.migrations:
            if migration.is_compatible(current_version, target_version):
                return migration
        return None
    
    def has_breaking_changes(self, current_version: str, target_version: str) -> bool:
        """Check if migration has breaking changes requiring code updates"""
        migration = self.find_migration(current_version, target_version)
        return migration is not None and len(migration.migration_steps) > 0
    
    async def apply_migration(self, current_version: str, target_version: str) -> Dict[str, Any]:
        """
        Apply migration from current to target version
        
        Returns:
            Dict with migration results and details
        """
        migration = self.find_migration(current_version, target_version)
        
        if migration is None:
            return {
                "success": True,
                "migration_required": False,
                "message": f"No migration needed for {current_version} → {target_version}",
                "changes_applied": []
            }
        
        if len(migration.migration_steps) == 0:
            return {
                "success": True, 
                "migration_required": False,
                "message": f"Version {target_version} has new features but no code changes required",
                "changelog": migration.changelog,
                "breaking_changes": migration.breaking_changes
            }
        
        logger.info(f"🔄 Applying migration {current_version} → {target_version}")
        logger.info(f"Breaking changes: {migration.breaking_changes}")
        
        # Create backup before migration
        backup_path = await self._create_migration_backup(current_version, target_version)
        
        applied_changes = []
        failed_steps = []
        
        try:
            for step in migration.migration_steps:
                logger.info(f"  📝 Applying: {step.description}")
                
                success, details = await self._apply_migration_step(step)
                
                if success:
                    applied_changes.append({
                        "step": step.name,
                        "description": step.description,
                        "details": details
                    })
                    logger.info(f"    ✅ {step.description}")
                else:
                    failed_steps.append({
                        "step": step.name,
                        "description": step.description,
                        "error": details
                    })
                    logger.error(f"    ❌ {step.description}: {details}")
                    
                    if step.required:
                        # Rollback on required step failure
                        await self._rollback_migration(backup_path)
                        return {
                            "success": False,
                            "migration_required": True,
                            "error": f"Required migration step failed: {step.description}",
                            "failed_step": step.name,
                            "rollback_performed": True
                        }
            
            # Migration completed
            return {
                "success": True,
                "migration_required": True,
                "message": f"Migration {current_version} → {target_version} completed successfully",
                "breaking_changes": migration.breaking_changes,
                "changes_applied": applied_changes,
                "failed_steps": failed_steps,  # Non-required steps that failed
                "backup_path": str(backup_path)
            }
            
        except Exception as e:
            logger.error(f"❌ Migration failed with exception: {e}")
            await self._rollback_migration(backup_path)
            return {
                "success": False,
                "migration_required": True,
                "error": f"Migration failed: {str(e)}",
                "rollback_performed": True
            }
    
    async def _apply_migration_step(self, step: MigrationStep) -> Tuple[bool, str]:
        """Apply single migration step"""
        try:
            # Find files matching pattern
            files_to_modify = list(self.agent_root.glob(step.file_pattern))
            
            if not files_to_modify:
                return False, f"No files found matching pattern: {step.file_pattern}"
            
            modifications = []
            
            for file_path in files_to_modify:
                if not file_path.is_file():
                    continue
                    
                content = file_path.read_text()
                
                # Apply regex transformation
                new_content = re.sub(
                    step.search_pattern,
                    step.replace_pattern,
                    content,
                    flags=re.MULTILINE
                )
                
                if new_content != content:
                    file_path.write_text(new_content)
                    modifications.append(str(file_path.relative_to(self.agent_root)))
            
            if modifications:
                return True, f"Modified files: {', '.join(modifications)}"
            else:
                return True, "No changes needed (patterns already up to date)"
                
        except Exception as e:
            return False, f"Error applying step: {str(e)}"
    
    async def _create_migration_backup(self, current_version: str, target_version: str) -> Path:
        """Create backup before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"migration_{current_version}_to_{target_version}_{timestamp}"
        backup_path.mkdir(exist_ok=True)
        
        # Backup key agent files
        files_to_backup = [
            "app/main.py",
            "requirements.txt", 
            "framework.lock",
            "CLAUDE.md"
        ]
        
        for file_name in files_to_backup:
            src_file = self.agent_root / file_name
            if src_file.exists():
                dst_file = backup_path / file_name
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                dst_file.write_text(src_file.read_text())
        
        logger.info(f"📦 Created migration backup: {backup_path}")
        return backup_path
    
    async def _rollback_migration(self, backup_path: Path):
        """Rollback migration from backup"""
        logger.info(f"🔄 Rolling back migration from {backup_path}")
        
        try:
            for backup_file in backup_path.rglob("*"):
                if backup_file.is_file():
                    relative_path = backup_file.relative_to(backup_path)
                    target_file = self.agent_root / relative_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    target_file.write_text(backup_file.read_text())
            
            logger.info("✅ Migration rollback completed")
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            raise
    
    def get_migration_info(self, current_version: str, target_version: str) -> Dict[str, Any]:
        """Get information about migration without applying it"""
        migration = self.find_migration(current_version, target_version)
        
        if migration is None:
            return {
                "migration_available": False,
                "message": f"No migration defined for {current_version} → {target_version}"
            }
        
        return {
            "migration_available": True,
            "from_version": migration.from_version,
            "to_version": migration.to_version,
            "breaking_changes": migration.breaking_changes,
            "migration_steps": [
                {
                    "name": step.name,
                    "description": step.description,
                    "file_pattern": step.file_pattern,
                    "required": step.required
                }
                for step in migration.migration_steps
            ],
            "changelog": migration.changelog,
            "has_code_changes": len(migration.migration_steps) > 0
        }
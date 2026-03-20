"""
Checkpoint Manager
==================

Handles saving and loading processing state for crash recovery.
Enables resuming long-running batch processing operations.

Author: APXMIND Development Team
Created: 2025-11-01
Version: 2.0.0
"""

import json
import pickle
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib
import logging

from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class CheckpointManager:
    """
    Manages processing checkpoints for crash recovery.
    
    Features:
    - Saves processing state periodically
    - Supports both JSON and pickle formats
    - Validates checkpoint integrity with checksums
    - Automatic cleanup of old checkpoints
    - Atomic writes to prevent corruption
    
    Usage:
        manager = CheckpointManager(Path("checkpoints"))
        
        # Save state
        state = {'processed_files': ['file1.pdf'], 'current_index': 1}
        manager.save("dataset_processing", state)
        
        # Load state
        restored = manager.load("dataset_processing")
        if restored:
            print(f"Resuming from {restored['current_index']}")
    """
    
    def __init__(
        self,
        checkpoint_dir: Path,
        format: str = "json",
        max_checkpoints: int = 5,
        enable_compression: bool = False
    ):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory to store checkpoints
            format: Checkpoint format ('json' or 'pickle')
            max_checkpoints: Maximum number of checkpoints to keep
            enable_compression: Whether to compress checkpoints
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.format = format
        self.max_checkpoints = max_checkpoints
        self.enable_compression = enable_compression
        
        # Create checkpoint directory
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"Initialized checkpoint manager",
            extra={
                'checkpoint_dir': str(self.checkpoint_dir),
                'format': format,
                'max_checkpoints': max_checkpoints
            }
        )
    
    def save(
        self,
        name: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save processing state to checkpoint.
        
        Args:
            name: Checkpoint name (e.g., "dataset_processing")
            state: State dictionary to save
            metadata: Optional metadata (timestamp added automatically)
            
        Returns:
            True if saved successfully
        """
        try:
            # Prepare checkpoint data
            checkpoint = {
                'name': name,
                'timestamp': datetime.now().isoformat(),
                'state': state,
                'metadata': metadata or {}
            }
            
            # Generate checkpoint filename
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp_str}.{self.format}"
            checkpoint_path = self.checkpoint_dir / filename
            
            # Save based on format
            if self.format == "json":
                self._save_json(checkpoint_path, checkpoint)
            elif self.format == "pickle":
                self._save_pickle(checkpoint_path, checkpoint)
            else:
                raise ValueError(f"Unsupported format: {self.format}")
            
            # Calculate and save checksum
            checksum = self._calculate_checksum(checkpoint_path)
            checksum_path = checkpoint_path.with_suffix(f"{checkpoint_path.suffix}.sha256")
            checksum_path.write_text(checksum)
            
            logger.info(
                f"Saved checkpoint: {name}",
                extra={
                    'checkpoint_path': str(checkpoint_path),
                    'state_keys': list(state.keys()),
                    'checksum': checksum[:16]
                }
            )
            
            # Cleanup old checkpoints
            self._cleanup_old_checkpoints(name)
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to save checkpoint: {name}",
                extra={'error': str(e)},
                exc_info=True
            )
            return False
    
    def load(
        self,
        name: str,
        version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Load processing state from checkpoint.
        
        Args:
            name: Checkpoint name
            version: Specific version timestamp (loads latest if None)
            
        Returns:
            Restored state dictionary or None if not found
        """
        try:
            # Find checkpoint file
            checkpoint_path = self._find_checkpoint(name, version)
            if not checkpoint_path:
                logger.warning(f"No checkpoint found for: {name}")
                return None
            
            # Verify checksum
            if not self._verify_checksum(checkpoint_path):
                logger.error(
                    f"Checkpoint checksum mismatch: {checkpoint_path.name}",
                    extra={'checkpoint_path': str(checkpoint_path)}
                )
                return None
            
            # Load based on format
            if self.format == "json":
                checkpoint = self._load_json(checkpoint_path)
            elif self.format == "pickle":
                checkpoint = self._load_pickle(checkpoint_path)
            else:
                raise ValueError(f"Unsupported format: {self.format}")
            
            logger.info(
                f"Loaded checkpoint: {name}",
                extra={
                    'checkpoint_path': str(checkpoint_path),
                    'timestamp': checkpoint.get('timestamp'),
                    'state_keys': list(checkpoint.get('state', {}).keys())
                }
            )
            
            return checkpoint.get('state')
            
        except Exception as e:
            logger.error(
                f"Failed to load checkpoint: {name}",
                extra={'error': str(e)},
                exc_info=True
            )
            return None
    
    def list_checkpoints(self, name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available checkpoints.
        
        Args:
            name: Filter by checkpoint name (lists all if None)
            
        Returns:
            List of checkpoint info dictionaries
        """
        checkpoints = []
        
        # Find all checkpoint files
        pattern = f"{name}_*.{self.format}" if name else f"*.{self.format}"
        for path in self.checkpoint_dir.glob(pattern):
            # Skip checksum files
            if path.suffix == ".sha256":
                continue
            
            checkpoints.append({
                'name': path.stem.rsplit('_', 1)[0],
                'path': str(path),
                'timestamp': path.stem.rsplit('_', 1)[1],
                'size': path.stat().st_size,
                'modified': datetime.fromtimestamp(path.stat().st_mtime).isoformat()
            })
        
        # Sort by timestamp (newest first)
        checkpoints.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return checkpoints
    
    def delete(self, name: str, version: Optional[str] = None) -> bool:
        """
        Delete checkpoint(s).
        
        Args:
            name: Checkpoint name
            version: Specific version (deletes all if None)
            
        Returns:
            True if deleted successfully
        """
        try:
            if version:
                # Delete specific version
                filename = f"{name}_{version}.{self.format}"
                checkpoint_path = self.checkpoint_dir / filename
                if checkpoint_path.exists():
                    checkpoint_path.unlink()
                    checksum_path = checkpoint_path.with_suffix(f"{checkpoint_path.suffix}.sha256")
                    if checksum_path.exists():
                        checksum_path.unlink()
                    logger.info(f"Deleted checkpoint: {filename}")
            else:
                # Delete all versions
                pattern = f"{name}_*.{self.format}"
                for path in self.checkpoint_dir.glob(pattern):
                    path.unlink()
                    checksum_path = path.with_suffix(f"{path.suffix}.sha256")
                    if checksum_path.exists():
                        checksum_path.unlink()
                logger.info(f"Deleted all checkpoints for: {name}")
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to delete checkpoint: {name}",
                extra={'error': str(e)},
                exc_info=True
            )
            return False
    
    def _save_json(self, path: Path, data: Dict[str, Any]):
        """Save checkpoint as JSON."""
        # Atomic write (write to temp file, then rename)
        temp_path = path.with_suffix(".tmp")
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_path.replace(path)
    
    def _save_pickle(self, path: Path, data: Dict[str, Any]):
        """Save checkpoint as pickle."""
        temp_path = path.with_suffix(".tmp")
        with open(temp_path, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        temp_path.replace(path)
    
    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load checkpoint from JSON."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_pickle(self, path: Path) -> Dict[str, Any]:
        """Load checkpoint from pickle."""
        with open(path, 'rb') as f:
            return pickle.load(f)
    
    def _calculate_checksum(self, path: Path) -> str:
        """Calculate SHA-256 checksum of file."""
        sha256 = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _verify_checksum(self, path: Path) -> bool:
        """Verify checkpoint file integrity."""
        checksum_path = path.with_suffix(f"{path.suffix}.sha256")
        if not checksum_path.exists():
            logger.warning(f"No checksum file found for: {path.name}")
            return True  # Allow if checksum file is missing
        
        expected_checksum = checksum_path.read_text().strip()
        actual_checksum = self._calculate_checksum(path)
        
        return expected_checksum == actual_checksum
    
    def _find_checkpoint(
        self,
        name: str,
        version: Optional[str] = None
    ) -> Optional[Path]:
        """Find checkpoint file by name and version."""
        if version:
            # Find specific version
            filename = f"{name}_{version}.{self.format}"
            checkpoint_path = self.checkpoint_dir / filename
            return checkpoint_path if checkpoint_path.exists() else None
        else:
            # Find latest version
            pattern = f"{name}_*.{self.format}"
            checkpoints = sorted(
                self.checkpoint_dir.glob(pattern),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            return checkpoints[0] if checkpoints else None
    
    def _cleanup_old_checkpoints(self, name: str):
        """Remove old checkpoints beyond max_checkpoints limit."""
        if self.max_checkpoints <= 0:
            return
        
        # Find all checkpoints for this name
        pattern = f"{name}_*.{self.format}"
        checkpoints = sorted(
            self.checkpoint_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        # Delete old ones
        for old_checkpoint in checkpoints[self.max_checkpoints:]:
            old_checkpoint.unlink()
            checksum_path = old_checkpoint.with_suffix(f"{old_checkpoint.suffix}.sha256")
            if checksum_path.exists():
                checksum_path.unlink()
            logger.debug(f"Cleaned up old checkpoint: {old_checkpoint.name}")


# Export
__all__ = ['CheckpointManager']

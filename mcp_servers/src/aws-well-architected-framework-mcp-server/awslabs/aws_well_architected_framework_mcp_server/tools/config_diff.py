#!/usr/bin/env python3
"""
Configuration Diff Tool

Compares two versions of configuration files and shows differences.

Requirements: 9.1, 9.2, 9.4
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class ChangeType(Enum):
    """Types of configuration changes"""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class ConfigChange:
    """Represents a configuration change"""
    change_type: ChangeType
    path: str
    old_value: Any
    new_value: Any
    file_name: str


class ConfigDiff:
    """Compares configuration files"""
    
    def __init__(self):
        self.changes: List[ConfigChange] = []
    
    def compare_directories(self, old_dir: Path, new_dir: Path) -> List[ConfigChange]:
        """Compare two configuration directories"""
        print(f"Comparing configurations:")
        print(f"  Old: {old_dir}")
        print(f"  New: {new_dir}")
        print("=" * 60)
        
        # Compare capabilities
        self._compare_subdirectory(old_dir / "capabilities", new_dir / "capabilities")
        
        # Compare patterns
        self._compare_subdirectory(old_dir / "patterns", new_dir / "patterns")
        
        # Compare scoring
        self._compare_subdirectory(old_dir / "scoring", new_dir / "scoring")
        
        return self.changes
    
    def _compare_subdirectory(self, old_subdir: Path, new_subdir: Path):
        """Compare files in a subdirectory"""
        if not old_subdir.exists() or not new_subdir.exists():
            return
        
        # Get all JSON files
        old_files = set(f.name for f in old_subdir.glob("*.json"))
        new_files = set(f.name for f in new_subdir.glob("*.json"))
        
        # Files added
        for filename in new_files - old_files:
            self.changes.append(ConfigChange(
                change_type=ChangeType.ADDED,
                path=filename,
                old_value=None,
                new_value="<entire file>",
                file_name=filename
            ))
        
        # Files removed
        for filename in old_files - new_files:
            self.changes.append(ConfigChange(
                change_type=ChangeType.REMOVED,
                path=filename,
                old_value="<entire file>",
                new_value=None,
                file_name=filename
            ))
        
        # Files in both - compare contents
        for filename in old_files & new_files:
            old_file = old_subdir / filename
            new_file = new_subdir / filename
            
            try:
                with open(old_file, 'r') as f:
                    old_config = json.load(f)
                with open(new_file, 'r') as f:
                    new_config = json.load(f)
                
                self._compare_configs(old_config, new_config, filename, "")
                
            except Exception as e:
                print(f"Error comparing {filename}: {e}")
    
    def _compare_configs(self, old_config: Any, new_config: Any, 
                        file_name: str, path: str):
        """Recursively compare configuration values"""
        if isinstance(old_config, dict) and isinstance(new_config, dict):
            # Compare dictionaries
            old_keys = set(old_config.keys())
            new_keys = set(new_config.keys())
            
            # Keys added
            for key in new_keys - old_keys:
                self.changes.append(ConfigChange(
                    change_type=ChangeType.ADDED,
                    path=f"{path}.{key}" if path else key,
                    old_value=None,
                    new_value=new_config[key],
                    file_name=file_name
                ))
            
            # Keys removed
            for key in old_keys - new_keys:
                self.changes.append(ConfigChange(
                    change_type=ChangeType.REMOVED,
                    path=f"{path}.{key}" if path else key,
                    old_value=old_config[key],
                    new_value=None,
                    file_name=file_name
                ))
            
            # Keys in both - compare values
            for key in old_keys & new_keys:
                new_path = f"{path}.{key}" if path else key
                self._compare_configs(old_config[key], new_config[key], 
                                    file_name, new_path)
        
        elif isinstance(old_config, list) and isinstance(new_config, list):
            # Compare lists
            if old_config != new_config:
                self.changes.append(ConfigChange(
                    change_type=ChangeType.MODIFIED,
                    path=path,
                    old_value=old_config,
                    new_value=new_config,
                    file_name=file_name
                ))
        
        else:
            # Compare primitive values
            if old_config != new_config:
                self.changes.append(ConfigChange(
                    change_type=ChangeType.MODIFIED,
                    path=path,
                    old_value=old_config,
                    new_value=new_config,
                    file_name=file_name
                ))
    
    def print_changes(self, show_unchanged: bool = False):
        """Print configuration changes"""
        if not self.changes:
            print("\n✅ No changes detected")
            return
        
        # Group by change type
        added = [c for c in self.changes if c.change_type == ChangeType.ADDED]
        removed = [c for c in self.changes if c.change_type == ChangeType.REMOVED]
        modified = [c for c in self.changes if c.change_type == ChangeType.MODIFIED]
        
        print(f"\n📊 Change Summary:")
        print(f"  Added: {len(added)}")
        print(f"  Removed: {len(removed)}")
        print(f"  Modified: {len(modified)}")
        
        # Print added
        if added:
            print(f"\n➕ Added ({len(added)}):")
            for change in added:
                print(f"  {change.file_name}::{change.path}")
                if isinstance(change.new_value, (dict, list)):
                    print(f"    Value: {json.dumps(change.new_value, indent=2)[:100]}...")
                else:
                    print(f"    Value: {change.new_value}")
        
        # Print removed
        if removed:
            print(f"\n➖ Removed ({len(removed)}):")
            for change in removed:
                print(f"  {change.file_name}::{change.path}")
                if isinstance(change.old_value, (dict, list)):
                    print(f"    Was: {json.dumps(change.old_value, indent=2)[:100]}...")
                else:
                    print(f"    Was: {change.old_value}")
        
        # Print modified
        if modified:
            print(f"\n🔄 Modified ({len(modified)}):")
            for change in modified:
                print(f"  {change.file_name}::{change.path}")
                print(f"    Old: {self._format_value(change.old_value)}")
                print(f"    New: {self._format_value(change.new_value)}")
    
    def _format_value(self, value: Any) -> str:
        """Format value for display"""
        if isinstance(value, (dict, list)):
            formatted = json.dumps(value, indent=2)
            if len(formatted) > 100:
                return formatted[:100] + "..."
            return formatted
        return str(value)
    
    def export_diff(self, output_file: Path):
        """Export diff to JSON file"""
        diff_data = {
            "summary": {
                "total_changes": len(self.changes),
                "added": len([c for c in self.changes if c.change_type == ChangeType.ADDED]),
                "removed": len([c for c in self.changes if c.change_type == ChangeType.REMOVED]),
                "modified": len([c for c in self.changes if c.change_type == ChangeType.MODIFIED])
            },
            "changes": [
                {
                    "type": change.change_type.value,
                    "file": change.file_name,
                    "path": change.path,
                    "old_value": change.old_value,
                    "new_value": change.new_value
                }
                for change in self.changes
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(diff_data, f, indent=2)
        
        print(f"\n💾 Diff exported to: {output_file}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Compare WAFR Enterprise Scoring configuration versions"
    )
    parser.add_argument(
        "old_config",
        type=Path,
        help="Old configuration directory"
    )
    parser.add_argument(
        "new_config",
        type=Path,
        help="New configuration directory"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Export diff to JSON file"
    )
    parser.add_argument(
        "--show-unchanged",
        action="store_true",
        help="Show unchanged values"
    )
    
    args = parser.parse_args()
    
    if not args.old_config.exists():
        print(f"Error: Old configuration directory not found: {args.old_config}")
        sys.exit(1)
    
    if not args.new_config.exists():
        print(f"Error: New configuration directory not found: {args.new_config}")
        sys.exit(1)
    
    diff = ConfigDiff()
    changes = diff.compare_directories(args.old_config, args.new_config)
    
    diff.print_changes(show_unchanged=args.show_unchanged)
    
    if args.output:
        diff.export_diff(args.output)
    
    # Exit with code 1 if there are changes (useful for CI/CD)
    sys.exit(1 if changes else 0)


if __name__ == "__main__":
    main()
